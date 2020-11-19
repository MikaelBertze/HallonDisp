# -*- coding: utf-8 -*-
import threading
from time import sleep

from loguru import logger
import paho.mqtt.client as mqtt
from rx.subject import Subject

from hallondisp import configreader


def get_broker(name):
    mqtt_brokers = configreader.APP_CONFIG['mqtt_definitions']
    assert name in [x['name'] for x in mqtt_brokers], f"broker {name} is not configured"
    broker = next(b for b in mqtt_brokers if b['name'] == name)
    return broker


class MqttListener:

    def __init__(self, broker, topic):
        self.OnMessage = Subject()
        self._server = broker['host']
        self._user = broker['user']
        self._pass = broker['pass']
        self._topic = topic
        logger.info("Starting MQTT updater thread")
        self.client = mqtt.Client(userdata=self)
        self.client.username_pw_set(self._user, self._pass)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def start(self):
        self.client.connect(self._server, 1883, 60)
        self.client.loop_start()
 
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
