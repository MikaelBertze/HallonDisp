import json
import time
import math
import numpy as np
import pause
from threading import Thread

from loguru import logger
import paho.mqtt.client as mqtt


class SimulatorClient:
    def __init__(self, broker, topic, name):
        self.name = name
        self.topic = topic
        self.broker = broker
        self.client = mqtt.Client()
        self.client.username_pw_set("hallondisp", "disphallon")
        self.is_paused = True

    def toggle_pause(self):
        logger.info(f"Pause toggle for {self.name}")
        self.is_paused = not self.is_paused

    def run(self):
        self._connect()
        th = Thread(target=self._run)
        th.start()

    def _connect(self):
        logger.info(f"Connecting simulator {self.name}")
        logger.info(f"Broker: {self.broker}")
        self.client.on_connect = self.on_connect
        self.client.connect(self.broker, 1883, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected to {self.topic} with result code {str(rc)}")

    def send_message(self, message):
        self.client.publish(self.topic, message)


class TempSimulator(SimulatorClient):
    def __init__(self, broker, min_s, max_s, repeat_time_s, seconds_between_messages):
        SimulatorClient.__init__(self, broker, "/simulators/temperature", "TempSensor")
        self.seconds_between_messages = seconds_between_messages
        self.repeat_time_s = repeat_time_s
        self.sincurve = [math.sin(x) * (max_s - min_s) + min_s for x in np.linspace(0, math.pi, num=self.repeat_time_s)]

    def _run(self):
        while True:
            temp = self.sincurve[int(time.time()) % self.repeat_time_s]
            pause.until(time.time() + self.seconds_between_messages)
            if not self.is_paused:
                tempdata = { "id": "temp1", "temp": f"{temp}"}
                message = json.dumps(tempdata)
                logger.info(message)
                self.send_message(message)


class DoorSimulator(SimulatorClient):
    def __init__(self, broker, door_id):
        SimulatorClient.__init__(self, broker, "/simulators/door", "DoorSensor")
        self.door_id = door_id
        self.door_state = False

    def toggle_door(self):
        self.door_state = not self.door_state

    def _run(self):
        while True:
            if not self.is_paused:
                doordata = {"id": self.door_id, "door": self.door_state}
                message = json.dumps(doordata)
                logger.info(message)
                self.send_message(message)
            pause.until(time.time() + 10)


class PowerSensorSimulator(SimulatorClient):
    def __init__(self, broker, min_s, max_s, repeat_time_s):
        SimulatorClient.__init__(self, broker, "/simulators/power", "PowerSensor")
        self.repeat_time_ms = repeat_time_s * 1000
        self.sincurve = [math.sin(x) * (max_s - min_s) + min_s for x in np.linspace(0, math.pi, num=self.repeat_time_ms)]
        self.last_tick = PowerSensorSimulator._getTick()

    def _run(self):
        while True:
            pausetime = self.sincurve[PowerSensorSimulator._getTick() % self.repeat_time_ms]
            pause.until(time.time() + pausetime)
            self.blink_detected()

    def blink_detected(self):
        time_now = PowerSensorSimulator._getTick()
        period = time_now - self.last_tick
        self.last_tick = time_now
        if not self.is_paused:
            tickdata = {"id": "power1", "power_tick_period": period}
            message = json.dumps(tickdata)
            logger.info(message)
            self.send_message(message)

    @staticmethod
    def _getTick():
        return int(round(time.time() * 1000))



