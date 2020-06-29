# -*- coding: utf-8 -*-
from typing import Dict
import os
from loguru import logger
from hallondisp import configreader
from hallondisp import ui



def __verify_app_config(config:Dict):
    # should contain app geometry
    assert "geometry" in config.keys(), "\"geometry\" missing in config file"
    assert "fullscreen" in config.keys(), "\"fullscreen\" missing in config file"

def start_app():
    logger.add("hallondisp.log", retention="5 days")
    logger.info("Starting up!")
    config = configreader.read_json_config("hallondisp.json")
    app_config = config['app']
    __verify_app_config(app_config)
    logger.info("Config file app section looks good!")
    logger.info(f"Geometry: {app_config['geometry']}")
    logger.info(f"Fullscreen: {'Yes' if app_config['fullscreen'] else 'No'}")

    app = ui.MainApp(config)

    if app_config['fullscreen']:
        app.attributes("-fullscreen", True)
    #else:
    #    app.attributes('-type', 'splash')
    app.geometry(app_config['geometry'])


    app.mainloop()

#def __build_widget(config):



