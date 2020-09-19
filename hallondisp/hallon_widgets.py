# -*- coding: utf-8 -*-
import time
from multiprocessing import Process
from tkinter import Frame, StringVar, Label, Button, Text, END, WORD, CENTER
from loguru import logger
from hallondisp.hallon_workers import PowerWorker, CumulativePowerWorker, TemperatureWorker, DoorWorker, LunchWorker
from hallondisp.utils import sound_player


class HallonWidget(Frame):
    def __init__(self, parent, workers):
        Frame.__init__(self, parent)
        self.workers = workers

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
                                 font=("DejaVu Sans", config['fontsize'], "bold"))
        self.clock_label.pack()
        self.update()

    def update(self):
        x = time.strftime('%H:%M:%S')
        if x != self.clockValue.get():
            self.clockValue.set(x)
        self.after(100, self.update)


class TimerWidget(HallonWidget):
    def __init__(self, parent, config, workers):
        HallonWidget.__init__(self, parent, workers)
        self.start_time = None
        self.config(bg=config['background'])
        # noinspection PyTypeChecker
        self.alarm_process: Process = None
        self.mode = "reset"
        self.name = config['title']
        self.run_name = config['title']
        self.text = StringVar()
        self.minutes = int(config['duration'] / 60)
        self.seconds = int(config['duration'] % 60)
        self.button = Button(self,
                             textvariable=self.text,
                             bg=config['background'],
                             fg=config['foreground'],
                             activebackground=config['background'],
                             activeforeground=config['foreground'],
                             font=("DejaVu Sans", config['fontsize'], "bold"),
                             command=lambda: self.toggle(),
                             pady=30,
                             highlightthickness=0, bd=0)
        self.button.pack()
        self.reset()

    def reset(self):
        self.mode = "reset"
        # self.config(bg="#333")
        self.button.config(bg="#333", activebackground='#333')
        self.text.set(f"{self.name} ({self.minutes:02}:{self.seconds:02})")
        if self.alarm_process is not None and self.alarm_process.is_alive():
            self.alarm_process.kill()

    def start(self):
        self.mode = "running"
        self.start_time = time.time()
        self.tick()
        self.button.config(bg="#FFD700", activebackground='#FFD700')

    def toggle(self):
        logger.info("toggle")
        if self.mode == "reset":
            self.start()
        elif self.mode == "running":
            self.reset()

        logger.info(self.mode)

    def alarm(self):
        if self.mode == "running" and (self.alarm_process is None or not self.alarm_process.is_alive()):
            logger.info("Starting alarm sound")
            self.alarm_process = Process(target=sound_player.alarm)
            self.alarm_process.start()
            self.button.config(bg="#f33", activebackground='#f33')

    def tick(self):
        if self.mode == "reset":
            return
        # get the current local time from the PC
        timeleft = self.start_time + 60 * self.minutes + self.seconds - time.time()

        if timeleft <= 0:
            self.alarm()

        minutes = int(timeleft / 60)
        sec = int(timeleft - minutes * 60)
        self.text.set(f"{self.run_name} ({abs(minutes):02}:{abs(sec):02})")

        # calls itself every 200 milliseconds
        # to update the time display as needed
        # could use >200 ms, but display gets jerky
        self.after(200, self.tick)


class TemperatureWidget(HallonWidget):
    def __init__(self, parent, config, workers):
        HallonWidget.__init__(self, parent, workers)
        self.config(bg=config['background'])
        self.sensor_id = config['sensor_id']
        self.temperatureValue = StringVar()
        self.min_tempValue = StringVar()
        self.max_tempValue = StringVar()
        self.temperatureValue.set("---")
        self.min_tempValue.set("---")
        self.max_tempValue.set("---")

        Label(self,
              text=config['title'],
              bg=config['background'],
              fg=config['foreground'],
              font=("DejaVu Sans", config['titlefontsize'], "bold")).pack()

        self.temperature_label = Label(self,
                                       textvariable=self.temperatureValue,
                                       bg=config['background'],
                                       fg=config['foreground'],
                                       font=("DejaVu Sans", config['fontsize'], "bold"))
        self.temperature_label.pack()

        worker: TemperatureWorker = self.get_worker('temperature-worker')
        worker.whenTemperatureReported.subscribe(lambda x: self.handle_update(x))
        worker.whenMinMaxModified.subscribe(lambda x: self.handle_min_max_update(x))

    def handle_update(self, update):
        logger.info(update)
        if update['sensor_id'] == self.sensor_id:
            self.temperatureValue.set("{:.1f}°C".format(update['temp']))

    def handle_min_max_update(self, min_max):
        self.min_tempValue.set("{:.1f}°C".format(min_max[0]))
        self.max_tempValue.set("{:.1f}°C".format(min_max[1]))


class DoorWidget(HallonWidget):
    def __init__(self, parent, config, workers):
        HallonWidget.__init__(self, parent, workers)
        self.door_id = config['door-id']
        self.config = config
        # self.doorValue = StringVar()
        # self.doorValue.set("---")
        self.door_label = Label(self,
                                text=config['title'],
                                bg='yellow',
                                fg=config['true_foreground'],
                                font=("DejaVu Sans", config['fontsize'], "bold"))
        self.door_label.pack()

        worker: DoorWorker = self.get_worker('door-worker')
        worker.whenDoorReported.subscribe(lambda x: self.handle_update(x))

    def handle_update(self, update):
        if update['id'] == self.door_id:
            if update['door']:
                self.door_label.config(fg=self.config['true_foreground'], bg=self.config['true_background'],
                                       activebackground=self.config['true_background'])
            else:
                self.door_label.config(fg=self.config['false_foreground'], bg=self.config['false_background'],
                                       activebackground=self.config['false_background'])


class CurrentPower(HallonWidget):
    def __init__(self, parent, config, workers):
        HallonWidget.__init__(self, parent, workers)
        self.powerValue = StringVar()
        self.powerValue.set("---")
        self.power_label = Label(self,
                                 textvariable=self.powerValue,
                                 bg=config['background'],
                                 fg=config['foreground'],
                                 font=("DejaVu Sans", config['fontsize'], "bold"))
        self.power_label.pack()

        worker: PowerWorker = self.get_worker('power-worker')
        worker.whenPowerReported.subscribe(lambda x: self.handle_update(x))

    def handle_update(self, update):
        self.powerValue.set("{:.0f}W".format(update))


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
              font=("DejaVu Sans", config['titlefontsize'], "bold")).pack()

        self.power_label = Label(self,
                                 textvariable=self.powerValue,
                                 bg=config['background'],
                                 fg=config['foreground'],
                                 font=("DejaVu Sans", config['fontsize'], "bold"))
        self.power_label.pack()
        worker: CumulativePowerWorker = self.get_worker('cumulative-power-worker')
        worker.whenUsageReported.subscribe(lambda x: self.handle_update(x))

    def handle_update(self, update):
        self.powerValue.set("{:.2f}kWh".format(update))


class Lunch(HallonWidget):
    def __init__(self, parent, config, workers):
        HallonWidget.__init__(self, parent, workers)
        logger.info("Lunch widget starting")
        self.config(bg=config['background'])
        self.lunchValue = StringVar()
        self.lunchValue.set("---")

        Label(self,
              text="Dagens lunch",
              bg=config['background'],
              fg=config['foreground'],
              font=("DejaVu Sans", config['titlefontsize'], "bold")).pack()

        self.textbox = Text(self,
                            height=6,
                            width=50,
                            bg=config['background'],
                            fg=config['foreground'],
                            font=("DejaVu Sans", config['fontsize'], "bold"),
                            wrap=WORD,
                            highlightthickness=0,
                            borderwidth=0,
                            pady=30)

        self.textbox.tag_configure('tag-center', justify=CENTER)
        self.textbox.pack()

        worker: LunchWorker = self.get_worker('lunch-worker')
        worker.whenNewLunchReported.subscribe(lambda x: self.handle_update(x))
        self.handle_update(worker.lunch)

    def handle_update(self, update):
        logger.info(update)
        if 'today' in update:
            lunch = update['today']
            lunch = lunch.replace(',', '\n')
            self.textbox.delete(1.0, END)
            self.textbox.insert(END, lunch, 'tag-center')
