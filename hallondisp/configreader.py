# -*- coding: utf-8 -*-
import json
import requests

APP_CONFIG = None


def _read_online_config(app_config):
    configuration_url = app_config['configuration_url']
    response = requests.get(configuration_url)
    assert response.status_code == 200, "Could not read config..."
    return response.json()


def _read_local_config(app_config):
    configuration_file = app_config['configuration_file']
    with open(configuration_file, 'r') as f:
        return json.load(f)


def read_json_config(filename="hallondisp.json"):
    global APP_CONFIG
    assert APP_CONFIG is None, "Config should only be read once!"
    with open(filename) as json_data_file:
        app_config = json.load(json_data_file)

    if app_config['configuration-style'] == "online":
        app_config.update(_read_online_config(app_config))
        APP_CONFIG = app_config

    elif app_config['configuration-style'] == "local":
        app_config.update(_read_local_config(app_config))
        APP_CONFIG = app_config

    assert APP_CONFIG is not None, "Config style not supported"
    return APP_CONFIG
