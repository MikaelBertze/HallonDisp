# -*- coding: utf-8 -*-
import os
from loguru import logger
from tkinter import Tk, Button, Frame, PhotoImage
from rx.subject import Subject
from hallondisp.factories import WidgetFactory, WorkerFactory, HallonWorker, Warnings


class HallonPage(Frame):
    def __init__(self, parent, page_config, widget_factory: WidgetFactory):
        Frame.__init__(self, parent)
        self.when_page_displayed = Subject()
        self.config(bg="#333")
        for widget_config in page_config['widgets']:
            logger.info(f"Building widget: {widget_config['name']}")
            widget = widget_factory.build_widget(widget_config, self)
            widget.pack()


class MainApp(Tk):
    def __init__(self, config):
        Tk.__init__(self)
        self.worker_factory = WorkerFactory(config['workers'])
        self.widget_factory = WidgetFactory(config['widgets'], self.worker_factory)
        self.pages = []
        self.current_page = -1
        self.left_img = PhotoImage(
            file=os.path.join(os.path.dirname(__file__), 'images/left_white.png'))
        self.right_img = PhotoImage(
            file=os.path.join(os.path.dirname(__file__), 'images/right_white.png'))

        self.active_frame = -1
        self.config(bg="#333")

        self.warnings = {}

        l_button = Button(self, bg="#333", fg="#333", activebackground='#333', image=self.left_img, highlightthickness=0, bd=0,
               width=110,
               command=lambda: self.next_frame(False)).pack(side="left", fill="y")

        Button(self, bg="#333", fg="#333", activebackground='#333', image=self.right_img,  highlightthickness=0, bd=0,
               width=110,
               command=lambda: self.next_frame(True)).pack(side="right", fill="y")

        self.warning_thingy = Button(l_button, text="Varningar", bg="#ff0", fg="#f00", activebackground='#f00',
                                     highlightthickness=0, bd=0,
                                     height=5,
                                     width=10,
                                     command=lambda: self.show_warnings())
        self.container = Frame(self)
        self.container.pack(side="top", fill="both", expand=True, ipadx=50)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        for page_config in config['pages']:
            self.load_page(page_config)
        logger.info("All pages loaded")

        w : HallonWorker
        for w in self.worker_factory.instances.values():
            if w.has_watchdog:
                w.whenWatchDogReport.subscribe(lambda x: self.handle_watchdog_report(x))
        self.next_frame(True)

    def handle_watchdog_report(self, report):
        if not report['state']:
            logger.warning("WATCH DOG REPORT:")
            logger.warning(report)
            self.warnings[report['hash']] = report['message']

        self.show_warning_thingy()

    def show_warning_thingy(self):
        if len(self.warnings.values()) > 0:
            logger.info("Show warning thingy")
            self.warning_thingy.place(x=10, y=10)
        else:
            self.warning_thingy.place_forget()

    def show_warnings(self):
        if not self.current_page == -1:
            self.current_page = -1
            page = Warnings(self.container, self.warnings, self.clear_warnings)
            page.grid(row=0, column=0, sticky="nsew", )
            page.tkraise()

    def clear_warnings(self):
        logger.info("Cleared warnings")
        self.warnings = {}

    def load_page(self, page_config):
        logger.info(f"Loading page {page_config['name']}")
        page = HallonPage(self.container, page_config, self.widget_factory)
        page.grid(row=0, column=0, sticky="nsew")
        self.pages.append(page)

    def next_frame(self, forward):
        self.current_page += 1 if forward else -1
        self.current_page %= len(self.pages)

        logger.info("Frame switch: " + str(self.current_page))

        page = self.pages[self.current_page]
        page.tkraise()
