# -*- coding: utf-8 -*-
import datetime
import time
from multiprocessing import Process
from tkinter import Frame, StringVar, Label, Button, Text, END, WORD, CENTER, LEFT
from loguru import logger
from hallondisp.hallon_workers import PowerWorker, CumulativePowerWorker, TemperatureWorker, DoorWorker, LunchWorker, \
    WaterWorker, CumulativeWaterWorker, RelayWorker
from hallondisp.utils import sound_player
import requests


class HallonWidget(Frame):
    def __init__(self, parent, workers):
        Frame.__init__(self, parent)
        self.workers = workers
        self.sticky = False


    def get_worker(self, name):
        for w in self.workers.keys():
            logger.warning(w)
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
        self.mode = "reset"
        self.name = config['title']
        self.run_name = config['title']
        self.tone = config['tone']
        self.tone_running = False
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
        if self.tone_running:
            url = "http://alarmthingy.local/stop"
            logger.info(url)
            requests.get("http://alarmthingy.local/stop")
            self.tone_running = False
        self.sticky = False

    def start(self):
        self.mode = "running"
        self.start_time = time.time()
        self.tick()
        self.button.config(bg="#FFD700", activebackground='#FFD700')
        self.sticky = True

    def toggle(self):
        logger.info("toggle")
        if self.mode == "reset":
            self.start()
        elif self.mode == "running":
            self.reset()

        logger.info(self.mode)

    def alarm(self):
        if self.mode == "running" and not self.tone_running:
            logger.info("Starting alarm sound")
            self.button.config(bg="#f33", activebackground='#f33')
            url = f"http://alarmthingy.local/{self.tone}"
            logger.info(url)
            requests.get(f"http://alarmthingy.local/{self.tone}")
            self.tone_running = True

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

        if config['title']:
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
        if update['sensor_id'] == self.sensor_id:
            self.temperatureValue.set("{:.1f}°C".format(update['temp']))

    def handle_min_max_update(self, min_max):
        self.min_tempValue.set("{:.1f}°C".format(min_max[0]))
        self.max_tempValue.set("{:.1f}°C".format(min_max[1]))


class DoorsWidget(HallonWidget):
    def __init__(self, parent, config, workers):
        HallonWidget.__init__(self, parent, workers)
        self.config(bg=config['background'])
        logger.warning(config.keys())
        for door_config in config['doors']:
            dc = {
                'title': door_config['title'],
                'door-id': door_config['door-id'],
                'true_foreground': config['true_foreground'],
                'fontsize': config['fontsize'],
                'true_background': config['true_background'],
                'false_foreground': config['false_foreground'],
                'false_background': config['false_background'],
                'true_foreground': config['true_foreground']
            }
            logger.info(f"Setting up door widget for {door_config['title']}")
            w = DoorWidget(self, dc, workers)
            w.pack(side=LEFT, padx=5);



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


class CurrentWater(HallonWidget):
    def __init__(self, parent, config, workers):
        HallonWidget.__init__(self, parent, workers)
        self.waterValue = StringVar()
        self.waterValue.set("---")
        self.water_label = Label(self,
                                 textvariable=self.waterValue,
                                 bg=config['background'],
                                 fg=config['foreground'],
                                 font=("DejaVu Sans", config['fontsize'], "bold"))
        self.water_label.pack()

        worker: WaterWorker = self.get_worker('water-worker')
        worker.whenWaterReported.subscribe(lambda x: self.handle_update(x['l_per_minute']))

    def handle_update(self, update):
        if (update > 10):
            self.waterValue.set("{:.2f} l/m".format(update))
        else:
            self.waterValue.set("{:.3f} l/m".format(update))


class CumulativeWater(HallonWidget):
    def __init__(self, parent, config, workers):
        HallonWidget.__init__(self, parent, workers)
        logger.info("CumulativeWater widget starting")

        self.config(bg=config['background'])
        self.waterValue = StringVar()
        self.waterValue.set("---")

        Label(self,
              text=config['title'],
              bg=config['background'],
              fg=config['foreground'],
              font=("DejaVu Sans", config['titlefontsize'], "bold")).pack()

        self.water_label = Label(self,
                                 textvariable=self.waterValue,
                                 bg=config['background'],
                                 fg=config['foreground'],
                                 font=("DejaVu Sans", config['fontsize'], "bold"))
        self.water_label.pack()
        worker: CumulativeWaterWorker = self.get_worker('cumulative-water-worker')
        worker.whenUsageReported.subscribe(lambda x: self.handle_update(x))

    def handle_update(self, update):
        self.waterValue.set("{:.2f} l".format(update))


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
        worker.whenPowerReported.subscribe(lambda x: self.handle_update(x['power']))

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
        if 'today' in update:
            lunch = update['today']
            lunch = lunch.replace(',', '\n')
            self.textbox.delete(1.0, END)
            self.textbox.insert(END, lunch, 'tag-center')


class Warnings(HallonWidget):
    def __init__(self, parent, warnings, clear_warnings):
        HallonWidget.__init__(self, parent, {})
        self.config(bg="#333")
        Button(self, text="Rensa", font=("DejaVu Sans", 25, "bold"), command=clear_warnings).pack()
        for w in warnings.values():
            Label(self,
                  text=w,
                  bg="#333",
                  fg="#f00",
                  font=("DejaVu Sans", 15, "bold")).pack()


class RelayWidget(HallonWidget):
    def __init__(self, parent, config, workers):
        HallonWidget.__init__(self, parent, workers)

        self.mode = 0
        self.state = False

        self.start_time = None
        self.config(bg=config['background'])
        # noinspection PyTypeChecker
        self.teslatext = StringVar()
        self.teslatext.set("TESLA")
        self.teslabutton = Button(self,
                             textvariable=self.teslatext,
                             bg=config['background'],
                             fg=config['foreground'],
                             activebackground=config['background'],
                             activeforeground=config['foreground'],
                             font=("DejaVu Sans", config['fontsize'], "bold"),
                             command=lambda: self.toggle_tesla(),
                             pady=30,
                             highlightthickness=0, bd=0)
        self.teslabutton.pack(pady=30)

        self.heatertext = StringVar()
        self.heatertext.set("MOTORVÄRMARE")
        self.heaterbutton = Button(self,
                             textvariable=self.heatertext,
                             bg=config['background'],
                             fg=config['foreground'],
                             activebackground=config['background'],
                             activeforeground=config['foreground'],
                             font=("DejaVu Sans", config['fontsize'], "bold"),
                             command=lambda: self.toggle_heater(),
                             pady=30,
                             highlightthickness=0, bd=0)
        self.heaterbutton.pack(pady=30)

        self.paused = False
        self.pause_minute = 0

        worker: RelayWorker = self.get_worker('relay-worker')
        worker.whenRelayReported.subscribe(lambda x: self.handle_update(x))

        hour_power: CumulativePowerWorker = self.get_worker('cumulative-power-worker-hour')
        hour_power.whenUsageReported.subscribe(lambda x: self.power_report(x))

    def power_report(self, x):
        now = datetime.datetime.now()
        m = now.minute
        l = 3.5
        limit = l / 60 * m

        logger.info(f"Limit: {limit} | Current: {x}")
        if not self.paused and m < 15:
            return

        if x > limit:
            if not self.paused:
                self.pause(m)

        else:
            if x < limit * 1.1 and (m < self.pause_minute or m > self.pause_minute + 15):
                self.unpause()

    def unpause(self):
        if self.mode > 0:
            self.paused = False
            self.pause_minute = 0
            requests.get("http://relaythingy.local/start")

    def pause(self, m):
        bg = "#33f"
        self.paused = True
        self.pause_minute = m
        requests.get("http://relaythingy.local/stop")


    def handle_update(self, state):
        self.state = state
        logger.info(state)
        bg = "#f33" if state else "#3f3"
        pausebg = "#00f"

        if self.paused:
            logger.info(f"Pause mode {self.pause_minute}")
            self.teslabutton.config(bg=pausebg, activebackground=pausebg)
            self.heaterbutton.config(bg=pausebg, activebackground=pausebg)
            return

        if self.mode == 0:
            self.teslabutton.config(bg=bg, activebackground=bg)
            self.heaterbutton.config(bg=bg, activebackground=bg)
        if self.mode == 1:
            self.teslabutton.config(bg=bg, activebackground=bg)
            pass
        if self.mode == 2:
            self.heaterbutton.config(bg=bg, activebackground=bg)

    def toggle_tesla(self):
        bg = "#3ff"
        logger.info("tesla toggle")
        self.heaterbutton["state"] = "disabled"
        if self.state or self.paused:
            self.mode = 0
            self.paused = False
            self.pause_minute = 0
            logger.info("tesla off")
            requests.get("http://relaythingy.local/stop")
            self.heaterbutton["state"] = "normal"
        else:
            self.mode = 1
            requests.get("http://relaythingy.local/start")
            self.heaterbutton["state"] = "disabled"
            self.heaterbutton.config(bg=bg, activebackground=bg)

    def toggle_heater(self):
        bg = "#3ff"
        logger.info("heater toggle")
        if self.state:
            self.mode = 0
            requests.get("http://relaythingy.local/stop")
            self.teslabutton["state"] = "normal"
        else:
            self.mode = 2
            requests.get("http://relaythingy.local/start")
            self.teslabutton["state"] = "disabled"
            self.teslabutton.config(bg=bg, activebackground=bg)







