# -*- coding: utf-8 -*-
import os
from loguru import logger
from tkinter import Tk, Button, Frame, PhotoImage, X
from rx.subject import Subject
from hallondisp.factories import WidgetFactory, WorkerFactory, HallonWorker, Warnings


class HallonPage(Frame):
    def __init__(self, parent, page_config, widget_factory: WidgetFactory):
        Frame.__init__(self, parent)
        self.when_page_displayed = Subject()
        self.config(bg="#333")
        self.widgets = []
        col = {}


        for widget_config in page_config['widgets']:
            logger.info(f"Building widget: {widget_config['name']}")
            if 'cell' not in widget_config:
                cell = 0
            else:
                cell = widget_config['cell']

            if cell not in col:
                col[cell] = Frame(self, bg="#333")

            widget = widget_factory.build_widget(widget_config, col[cell])
            self.widgets.append(widget)
            widget.pack()
        if len(col) == 1:
            col[0].pack(side="top", fill="x")
        else:
            col[0].pack(side="left", fill="y")
            col[1].pack(side="right", fill="y")

    def is_sticky(self):
        return any([x.sticky for x in self.widgets])


class MainApp(Tk):
    def __init__(self, config):
        Tk.__init__(self)

        self.page_timeout = config['page-handler']['page-timeout']
        self.page_timer = None
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
        self.show_warning_thingy()

    def load_page(self, page_config):
        logger.info(f"Loading page {page_config['name']}")
        page = HallonPage(self.container, page_config, self.widget_factory)
        page.grid(row=0, column=0, sticky="nsew")
        self.pages.append(page)

    def next_frame(self, forward):
        pagenum = self.current_page + (1 if forward else -1)
        pagenum %= len(self.pages)

        logger.info("Frame switch: " + str(pagenum))
        self.set_frame(pagenum)

    def set_frame(self, num, page_timeout=False):
        if self.page_timer is not None:
            self.after_cancel(self.page_timer)

        sticky = page_timeout and self.pages[self.current_page].is_sticky()
        if sticky:
            logger.info("Ignoring timeout. Current page is sticky")
        else:
            logger.info(f"Setting frame to page: {num}")
            assert num < len(self.pages), f"page {num} does not exist"
            self.current_page = num
            page = self.pages[self.current_page]
            page.tkraise()
        if sticky or num != 0:
            logger.info(f"Going back in {self.page_timeout} s")
            self.page_timer = self.after(self.page_timeout * 1000, self.set_frame, 0, True)





