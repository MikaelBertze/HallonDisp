# -*- coding: utf-8 -*-
import time
from threading import Timer
from tkinter import Frame, StringVar, Label
from datetime import datetime, timedelta
from loguru import logger
from hallondisp import mqtt_utils
import numpy as np

from hallondisp.hallon_workers import PowerWorker, CumulativePowerWorker, TemperatureWorker


class HallonWidget(Frame):
    def __init__(self, parent, workers):
        Frame.__init__(self, parent)
        self.workers = workers

    @property
    def tk_frame(self) -> Frame:
        return self.__tkFrame

    def get_worker(self, name):
        return self.workers[name]


class CurrentTimeWidget(HallonWidget):
    def __init__(self, parent, config, workers):
        HallonWidget.__init__(self, parent, workers)
        self.clockValue = StringVar()
        self.clockValue.set("12:00:00")
        self.clock_label = Label(self,
                                 textvariable=self.clockValue,
                                 bg=config['background'],
                                 fg=config['foreground'],
                                 font=("Courier", config['fontsize'], "bold"))
        self.clock_label.pack()
        self.update()

    def update(self):
        x = time.strftime('%H:%M:%S')
        if x != self.clockValue.get():
            self.clockValue.set(x)
        self.after(100, self.update)



    @staticmethod
    def hallon_size():
        return 1, 4

class TemperatureWidget(HallonWidget):
    def __init__(self, parent, config, workers):
        HallonWidget.__init__(self, parent, workers)
        self.config(bg=config['background'])
        self.temperatureValue = StringVar()
        self.temperatureValue.set("---")

        Label(self,
              text=config['title'],
              bg=config['background'],
              fg=config['foreground'],
              font=("Courier", config['titlefontsize'], "bold")).pack()

        self.temperature_label = Label(self,
                                 textvariable=self.temperatureValue,
                                 bg=config['background'],
                                 fg=config['foreground'],
                                 font=("Courier", config['fontsize'], "bold"))
        self.temperature_label.pack()

        worker: TemperatureWorker = self.get_worker('temperature-worker')
        worker.whenTemperatureReported.subscribe(lambda x: self.handle_update(x))

    def handle_update(self, update):
        self.temperatureValue.set("{:.1f}°C".format(update))


class CurrentPower(HallonWidget):
    def __init__(self, parent, config, workers):
        HallonWidget.__init__(self, parent, workers)
        self.powerValue = StringVar()
        self.powerValue.set("---")
        self.power_label = Label(self,
                                 textvariable=self.powerValue,
                                 bg=config['background'],
                                 fg=config['foreground'],
                                 font=("Courier", config['fontsize'], "bold"))
        self.power_label.pack()

        worker: PowerWorker = self.get_worker('power-worker')
        worker.whenPowerReported.subscribe(lambda x: self.handle_update(x))

    def handle_update(self, update):
        self.powerValue.set("{:.0f}W".format(update))


    @staticmethod
    def hallon_size():
        return 1, 4


class CumulativePower(HallonWidget):
    def __init__(self, parent, config, workers):
        HallonWidget.__init__(self, parent, workers)
        logger.info("CumulativePower widget starting")

        self.config(bg=config['background'])
        self.powerValue = StringVar()
        self.powerValue.set("---")

        Label(self,
              text=config['title'],
              bg=config['background'],
              fg=config['foreground'],
              font=("Courier", config['titlefontsize'], "bold")).pack()

        self.power_label = Label(self,
                                 textvariable=self.powerValue,
                                 bg=config['background'],
                                 fg=config['foreground'],
                                 font=("Courier", config['fontsize'], "bold"))
        self.power_label.pack()
        worker: CumulativePowerWorker = self.get_worker('cumulative-power-worker')
        worker.whenUsageReported.subscribe(lambda x: self.handle_update(x))

    def handle_update(self, update):
        self.powerValue.set("{:.2f}kWh".format(update))

    @staticmethod
    def hallon_size():
        return 1, 4