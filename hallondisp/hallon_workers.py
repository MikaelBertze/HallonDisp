# -*- coding: utf-8 -*-
import json
from datetime import datetime
from threading import Timer
import numpy as np
from loguru import logger
from rx.subject import Subject
import requests
from bs4 import BeautifulSoup
from hallondisp import mqtt_utils
from hallondisp.mqtt_utils import MqttListener


class HallonWorker:
    def __init__(self, config, workers, timeout_s=-1):
        self.config = config
        self.workers = workers
        self.has_watchdog = False
        self.whenWatchDogReport = Subject()
        self.timeout_s = timeout_s
        self.initialized = False
        self.msg_count = 0
        self.watchdog = None

    def timeout(self):
        if self.msg_count == 0:
            self.whenWatchDogReport.on_next({'state': False, 'message': self.watchdog_message(), 'hash': hash(self)})
        else:
            self.whenWatchDogReport.on_next({'state': True, 'message': "", 'hash': hash(self)})
        self.msg_count = 0
        if self.watchdog is not None:
            self.watchdog.cancel()
        self.watchdog = Timer(self.timeout_s, self.timeout)
        self.watchdog.daemon = True
        self.watchdog.start()

    def watchdog_message(self):
        if self.timeout_s > 0:
            raise NotImplementedError("You should implement this...")

    def init_worker(self):
        logger.info("initializing worker")
        if not self.initialized:
            self._init_worker()
            self.initialized = True
            if self.timeout_s > 0:
                self.timeout()

    def _init_worker(self):
        raise NotImplementedError("You should implement this...")


class DoorWorker(HallonWorker):
    def __init__(self, config, workers):
        HallonWorker.__init__(self, config, workers, 120)
        self.whenDoorReported = Subject()
        broker = mqtt_utils.get_broker(config['mqtt']['broker'])
        self.mqtt_updater = MqttListener(broker, config['mqtt']['topics'])
        self.mqtt_updater.OnMessage.subscribe(self.handle_update)

    def _init_worker(self):
        self.mqtt_updater.start()

    def watchdog_message(self):
        return "Door not reported:" + self.mqtt_updater._topics[0]

    def handle_update(self, msg):
        try:
            self.msg_count += 1
            data = json.loads(msg[1])
            for x in data:
                self.whenDoorReported.on_next(x)

        except Exception as ex:
            logger.error("Exception in mqtt thread: " + str(ex))


class PowerWorker(HallonWorker):
    def __init__(self, config, workers):
        HallonWorker.__init__(self, config, workers, 120)
        self.whenPowerReported = Subject()
        self.whenNoPowerReported = Subject()
        broker = mqtt_utils.get_broker(config['mqtt']['broker'])
        self.mqtt_updater = MqttListener(broker, [config['mqtt']['topic']])

        self.mqtt_updater.OnMessage.subscribe(self.handle_update)

    def watchdog_message(self):
        return "Power not reported:" + self.mqtt_updater._topics[0]

    def _init_worker(self):
        self.mqtt_updater.start()

    def handle_update(self, msg):
        try:
            self.msg_count += 1
            # expected structure: tickPeriod:123|counter:5
            data = json.loads(msg[1])
            if "power_tick_period" in data:
                tick_period = data['power_tick_period']
            else:
                logger.info(f"Could not read power message {msg}")
                return
            tp = int(tick_period)
            wh_per_hit = 1 / float(1000) * 1000
            power = wh_per_hit * 3600 / float(tp / 1000)
            data['power'] = power
            self.whenPowerReported.on_next(data)
        except Exception as ex:
            logger.error("Exception in mqtt thread: " + str(ex))


class CumulativePowerWorker(HallonWorker):
    def __init__(self, config, workers):
        HallonWorker.__init__(self, config, workers)

        assert "power-worker" in workers, "This worker require power-worker"
        self.reset_mode = config['reset-mode']
        self.measurements = []
        self.whenUsageReported = Subject()
        self.start_time = None
        assert 'power-worker' in workers, "Could not find power-worker in workers"
        power_worker: PowerWorker = workers['power-worker']
        power_worker.whenPowerReported.subscribe(self.power_reported)

    def _init_worker(self):
        self.reset_cumulative_usage()
        logger.info("Cumulative power worker initialized")

    def power_reported(self, value):
        now = datetime.now()
        delta = now-self.start_time
        self.measurements.append((delta.total_seconds(), value['power']))
        values = [x[1] / 1000 for x in self.measurements]
        times = [x[0] / 60 / 60 for x in self.measurements]
        current_usage = np.trapz(values, times)
        self.whenUsageReported.on_next(current_usage)

    def reset_cumulative_usage(self):
        logger.info("Cumulative worker reset")
        self.measurements = []
        self.start_time = datetime.now()
        seconds_to_next_reset = None

        if self.reset_mode == "minute":
            seconds_to_next_reset = 60 - self.start_time.second
        if self.reset_mode == "hour":
            seconds_to_next_reset = 3600 - self.start_time.minute * 60 - self.start_time.second
        elif self.reset_mode == "day":
            seconds_to_next_reset = 86400 - self.start_time.hour * 3600 - self.start_time.minute * 60 - self.start_time.second

        assert seconds_to_next_reset is not None, f"Unsupported reset-mode: {self.reset_mode}"

        logger.info(f"Reset of cumulative usage in {seconds_to_next_reset}s.")
        timer = Timer(seconds_to_next_reset, self.reset_cumulative_usage)
        timer.daemon = True
        timer.start()


class WaterWorker(HallonWorker):
    def __init__(self, config, workers):
        HallonWorker.__init__(self, config, workers, 120)
        self.whenWaterReported = Subject()
        self.whenNoWaterReported = Subject()
        broker = mqtt_utils.get_broker(config['mqtt']['broker'])
        self.mqtt_updater = MqttListener(broker, [config['mqtt']['topic']])
        self.mqtt_updater.OnMessage.subscribe(self.handle_update)

    def watchdog_message(self):
        return "Water not reported:" + self.mqtt_updater._topics[0]

    def _init_worker(self):
        self.mqtt_updater.start()

    def handle_update(self, msg):
        try:
            self.msg_count += 1
            # expected structure: tickPeriod:123|counter:5
            data = json.loads(msg[1])
            if "consumption" in data and "t_diff" in data:
                consumption = data['consumption']
                t_diff = data['t_diff']
            else:
                logger.info(f"Could not read water message {msg}")
                return
            if t_diff < 10:
                logger.info(f"Strange water report. t_diff: {t_diff}")
            l_per_minute = consumption / (t_diff/1000.0) * 60
            data['l_per_minute'] = l_per_minute
            self.whenWaterReported.on_next(data)

        except Exception as ex:
            logger.error("Exception in mqtt thread: " + str(ex))


class CumulativeWaterWorker(HallonWorker):
    def __init__(self, config, workers):
        HallonWorker.__init__(self, config, workers)
        assert "water-worker" in workers, "This worker require water-worker"
        self.reset_mode = config['reset-mode']
        self.total = 0
        self.whenUsageReported = Subject()
        self.start_time = None
        water_worker: WaterWorker = workers['water-worker']
        water_worker.whenWaterReported.subscribe(self.water_reported)

    def _init_worker(self):
        self.reset_cumulative_usage()
        logger.info("Cumulative water worker initialized")

    def water_reported(self, value):
        l_diff = float(value['consumption'])
        if l_diff > 0.000001:
            self.total += l_diff
            self.whenUsageReported.on_next(self.total)

    def reset_cumulative_usage(self):
        logger.info("Cumulative worker reset")
        self.total = 0
        self.whenUsageReported.on_next(0)
        self.start_time = datetime.now()
        seconds_to_next_reset = None

        if self.reset_mode == "minute":
            seconds_to_next_reset = 60 - self.start_time.second
        if self.reset_mode == "hour":
            seconds_to_next_reset = 3600 - self.start_time.minute * 60 - self.start_time.second
        elif self.reset_mode == "day":
            seconds_to_next_reset = 86400 - self.start_time.hour * 3600 - self.start_time.minute * 60 - self.start_time.second

        assert seconds_to_next_reset is not None, f"Unsupported reset-mode: {self.reset_mode}"

        logger.info(f"Reset of cumulative water usage in {seconds_to_next_reset}s.")
        timer = Timer(seconds_to_next_reset, self.reset_cumulative_usage)
        timer.daemon = True
        timer.start()


class TemperatureWorker(HallonWorker):
    def __init__(self, config, workers):
        HallonWorker.__init__(self, config, workers, 120)
        self.whenTemperatureReported = Subject()
        self.whenMinMaxModified = Subject()
        self.whenNoTemperatureReported = Subject()
        broker = mqtt_utils.get_broker(config['mqtt']['broker'])
        self.mqtt_updater = MqttListener(broker, config['mqtt']['topics'])
        self.mqtt_updater.OnMessage.subscribe(self.handle_update)
        self.day = -1
        self.todayMinValue = 0
        self.todayMaxValue = 0

    def _init_worker(self):
        self.mqtt_updater.start()

    def watchdog_message(self):
        return "Temp not reported:" + self.mqtt_updater._topics[0]

    def handle_update(self, msg):
        try:
            topic, msg = msg
            self.msg_count += 1
            data = json.loads(msg)
            sensor_id = data['id']
            temp = data["temp"]
            self.whenTemperatureReported.on_next({'sensor_id': sensor_id, 'temp': temp})
        except Exception as ex:
            logger.error("Exception in mqtt thread: " + str(ex))


class LunchWorker(HallonWorker):
    def __init__(self, config, workers):
        HallonWorker.__init__(self, config, workers)
        self.whenNewLunchReported = Subject()
        self.lunch = ""

    def _init_worker(self):
        self.update()

    def update(self):
        try:
            # Find url for 'matsedel'
            url = 'http://skola.karlstad.se/hultsbergsskolan4a/matsedel/'
            page = requests.get(url)
            soup = BeautifulSoup(page.content, 'html.parser')
            x = soup.find('object')
            matsedel_url = x['data']
            logger.info(f"Fetching lunch from {matsedel_url}")

            page = requests.get(matsedel_url)
            soup = BeautifulSoup(page.content, 'html.parser')

            today = datetime.now()
            lunch = self.get_lunch_for_date(today, soup)
            logger.info(f"Lunch: {lunch}")
            self.lunch = {'today': lunch}
            self.whenNewLunchReported.on_next(self.lunch)
        except Exception:
            logger.warning("Could not fetch todays lunch")
        finally:
            timer = Timer(60 * 15, self.update)
            timer.daemon = True
            timer.start()

    def get_lunch_for_date(self, date, soup):
        months = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec']
        day_s = f"{date.strftime('%d')} {months[date.month - 1]}"
        try:
            x = soup.find('div', string=day_s)
            y = x.parent.parent.find('div', class_="app-daymenu-name")
            lunch = y.text
        except Exception:
            return "Nada"
        return lunch


class RelayWorker(HallonWorker):
    def __init__(self, config, workers):
        HallonWorker.__init__(self, config, workers, 120)
        self.whenRelayReported = Subject()
        broker = mqtt_utils.get_broker(config['mqtt']['broker'])
        self.mqtt_updater = MqttListener(broker, [config['mqtt']['topic']])
        self.mqtt_updater.OnMessage.subscribe(self.handle_update)

    def watchdog_message(self):
        return "Power not reported:" + self.mqtt_updater._topics[0]

    def _init_worker(self):
        self.mqtt_updater.start()

    def handle_update(self, msg):
        try:
            self.msg_count += 1
            data = json.loads(msg[1])
            if "state" in data:
                state = True if data['state'] == "ON" else False
                logger.info(f"STATE: {state}")
                self.whenRelayReported.on_next(state)
            else:
                logger.info(f"Could not read power message {msg}")
                return

        except Exception as ex:
            logger.error("Exception in mqtt thread: " + str(ex))

