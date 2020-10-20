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
    def __init__(self, config, workers):
        self.config = config
        self.workers = workers
        self.initialized = False

    def init_worker(self):
        logger.info("initializing worker")
        if not self.initialized:
            self._init_worker()
            self.initialized = True

    def _init_worker(self):
        raise NotImplementedError("You should implement this...")


class DoorWorker(HallonWorker):
    def __init__(self, config, workers):
        HallonWorker.__init__(self, config, workers)
        self.whenDoorReported = Subject()
        broker = mqtt_utils.get_broker(config['mqtt']['broker'])
        self.mqtt_updater = MqttListener(broker, config['mqtt']['topic'])
        self.mqtt_updater.OnMessage.subscribe(self.handle_update)

    def _init_worker(self):
        self.mqtt_updater.start()

    def handle_update(self, msg):
        try:
            data = json.loads(msg)
            logger.info(data)
            self.whenDoorReported.on_next(data)

        except Exception as ex:
            logger.error("Exception in mqtt thread: " + str(ex))


class PowerWorker(HallonWorker):
    def __init__(self, config, workers):
        HallonWorker.__init__(self, config, workers)
        self.whenPowerReported = Subject()
        self.whenNoPowerReported = Subject()
        broker = mqtt_utils.get_broker(config['mqtt']['broker'])
        self.mqtt_updater = MqttListener(broker, config['mqtt']['topic'])

        self.mqtt_updater.OnMessage.subscribe(self.handle_update)
        self.watchdog = Timer(10.0, self.timeout)
        self.lost_count = 0

    def _init_worker(self):
        self.mqtt_updater.start()

    def restart_watchdog(self):
        self.watchdog.cancel()
        self.watchdog = Timer(15.0, self.timeout)
        self.watchdog.start()

    def timeout(self):
        self.lost_count += 1
        self.whenNoPowerReported.on_next(self.lost_count)
        self.restart_watchdog()

    def handle_update(self, msg):
        try:
            self.restart_watchdog()
            # expected structure: tickPeriod:123|counter:5
            data = json.loads(msg)
            if "power_tick_period" in data:
                tick_period = data['power_tick_period']
            else:
                logger.info(f"Could not read power message {msg}")
                return
            tp = int(tick_period)
            wh_per_hit = 1 / float(1000) * 1000
            power = wh_per_hit * 3600 / float(tp / 1000)
            logger.info("Reporting power")
            self.whenPowerReported.on_next(power)

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
        self.measurements.append((delta.total_seconds(), value))
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


class TemperatureWorker(HallonWorker):
    def __init__(self, config, workers):
        HallonWorker.__init__(self, config, workers)
        self.whenTemperatureReported = Subject()
        self.whenMinMaxModified = Subject()
        self.whenNoTemperatureReported = Subject()
        broker = mqtt_utils.get_broker(config['mqtt']['broker'])
        self.mqtt_updater = MqttListener(broker, config['mqtt']['topic'])
        self.mqtt_updater.OnMessage.subscribe(self.handle_update)
        self.watchdog = Timer(120.0, self.timeout)
        self.lost_count = 0
        self.day = -1
        self.todayMinValue = 0
        self.todayMaxValue = 0

    def restart_watchdog(self):
        self.watchdog.cancel()
        self.watchdog = Timer(15.0, self.timeout)
        self.watchdog.start()

    def timeout(self):
        self.lost_count += 1
        self.whenNoTemperatureReported.on_next(self.lost_count)
        self.restart_watchdog()

    def _init_worker(self):
        self.mqtt_updater.start()

    def handle_update(self, msg):
        logger.info(msg)
        data = json.loads(msg)
        #key, value = (x.strip() for x in msg.split(':'))
        sensor_id = data['id']
        temp = float(data["temp"])
        #day = datetime.day
        #if self.day != day:
        #    self.day = day
        #    self.todayMinValue = 100
        #    self.todayMaxValue = -100
        #if temp < self.todayMinValue:
        #    self.todayMinValue = temp
        #    self.whenMinMaxModified.on_next((self.todayMinValue, self.todayMaxValue))
        #if temp > self.todayMaxValue:
        #    self.todayMaxValue = temp
        #    self.whenMinMaxModified.on_next((self.todayMinValue, self.todayMaxValue))
        self.whenTemperatureReported.on_next({ 'sensor_id': sensor_id, 'temp': temp})


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
            URL = 'http://skola.karlstad.se/hultsbergsskolan4a/matsedel/'
            page = requests.get(URL)
            soup = BeautifulSoup(page.content, 'html.parser')
            x = soup.find('object')
            matsedel_url = x['data']

            page = requests.get(matsedel_url)
            soup = BeautifulSoup(page.content, 'html.parser')

            today = datetime.now()
            lunch = self.get_lunch_for_date(today, soup)
            logger.info(f"Lunch: {lunch}")
            self.lunch = {'today': lunch}
            self.whenNewLunchReported.on_next(self.lunch)
        except:
            logger.warning("Could not fetch todays lunch")
        finally:
            timer = Timer(60 * 15, self.update)
            timer.daemon = True
            timer.start()

    def get_lunch_for_date(self, date, soup):
        months = ['jan', 'feb', 'mar', 'apr', 'maj', 'juni', 'juli', 'aug', 'sep', 'okt', 'nov', 'dec']
        day_s = f"{date.strftime('%d')} {months[date.month - 1]}"
        try:
            x = soup.find('div', string=day_s)
            y = x.parent.parent.find('div', class_="app-daymenu-name")
            lunch = y.text
        except:
            return "Nada"
        return lunch


class WeatherWorker(HallonWorker):
    def __init__(self, config, workers):
        HallonWorker.__init__(self, config, workers)
        self.whenNewWeatherReported = Subject()
        self.weather = {}

    def _init_worker(self):
        self.update()

    def update(self):
        try:
            self.weather = {}
            pass
        except:
            logger.warning("Could not fetch weather")
        finally:
            timer = Timer(60 * 15, self.update)
            timer.daemon = True
            timer.start()

