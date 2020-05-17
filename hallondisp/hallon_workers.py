# -*- coding: utf-8 -*-
import re
from datetime import datetime
from threading import Timer
import numpy as np
from loguru import logger
from rx.subject import Subject

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


class PowerWorker(HallonWorker):
    def __init__(self, config, workers):
        HallonWorker.__init__(self, config, workers)
        self.whenPowerReported = Subject()
        self.whenNoPowerReported = Subject()
        self.mqtt_updater = MqttListener(config['mqtt']['broker'], config['mqtt']['topic'])
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
            matches = re.match(r'tickPeriod:(\d+)', msg)
            if matches.groups():
                tick_period = matches.group(1)
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
        self.whenNoTemperatureReported = Subject()
        self.mqtt_updater = MqttListener(config['mqtt']['broker'], config['mqtt']['topic'])
        self.mqtt_updater.OnMessage.subscribe(self.handle_update)
        self.watchdog = Timer(120.0, self.timeout)
        self.lost_count = 0

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
        key, value = (x.strip() for x in msg.split(':'))
        if key == 'temp':
            self.whenTemperatureReported.on_next(float(value))