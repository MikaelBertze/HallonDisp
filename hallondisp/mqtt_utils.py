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


class MqttListener(threading.Thread):

    def __init__(self, broker, topic):
        threading.Thread.__init__(self)
        self.daemon = True
        self.OnMessage = Subject()
        self._server = broker['host']
        self._user = broker['user']
        self._pass = broker['pass']
        self._topic = topic

    def run(self):
        while True:
            try:
                logger.info("Starting MQTT updater thread")
                client = mqtt.Client(userdata=self)
                client.username_pw_set(self._user, self._pass)
                client.on_connect = self.on_connect
                client.on_message = self.on_message
                client.connect(self._server, 1883, 60)
                client.loop_forever()
            except Exception as e:
                logger.exception(e)
                sleep(10)


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
