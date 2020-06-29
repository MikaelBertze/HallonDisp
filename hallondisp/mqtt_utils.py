# -*- coding: utf-8 -*-
import threading

from loguru import logger
import paho.mqtt.client as mqtt
from rx.subject import Subject


class MqttListener(threading.Thread):

    def __init__(self, server, topic):
        threading.Thread.__init__(self)
        self.daemon = True
        self.OnMessage = Subject()
        self._server = server
        self._topic = topic

    def run(self):
        logger.info("Starting MQTT updater thread")
        client = mqtt.Client(userdata=self)
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect(self._server, 1883, 60)
        client.loop_forever()

    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected to {userdata._topic} with result code {str(rc)}")
        logger.info(userdata._topic)
        client.subscribe(userdata._topic)

    def on_message(self, client, userdata, msg):
        try:
            received = msg.payload.decode('ascii')
            self.OnMessage.on_next(received)
        except:
            pass
