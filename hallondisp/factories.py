# -*- coding: utf-8 -*-
from hallondisp.hallon_widgets import *
from hallondisp.hallon_workers import *


class WorkerFactory:
    built_in_workers = {
        'power-worker': PowerWorker,
        'cumulative-power-worker': CumulativePowerWorker,
        'temperature-worker': TemperatureWorker,
        'door-worker': DoorWorker,
        'lunch-worker': LunchWorker,
        "water-worker": WaterWorker,
        'cumulative-water-worker': CumulativeWaterWorker,
        'relay-worker': RelayWorker
    }

    def __init__(self, worker_configs):
        self.worker_configs = worker_configs
        self.instances = {}

    def build_worker(self, worker_name) -> HallonWorker:
        logger.info("Building worker: " + worker_name)
        config = self.worker_configs[worker_name]
        assert not config['is-abstract'], "Abstract workers cannot be constructed"

        if "extends" in config:
            base_config = self.worker_configs[config['extends']]
            base_config['config'].update(config['config'])
            config = base_config
        if worker_name in self.instances.keys():
            logger.info(f"{worker_name} has already been constructed. Reusing existing worker")
            return self.instances[worker_name]

        worker = None
        if config['source']['type'] == "built-in":
            logger.info(f"{worker_name} is a built-in worker.")
            if "require-workers" in config:
                for worker_requirement in config["require-workers"]:
                    logger.info(f"{worker_name} require {worker_requirement}")
                    self.build_worker(worker_requirement)

            worker = self.__build_built_in(config['source']['name'], config['config'])
            self.instances[worker_name] = worker

        assert worker is not None, f"worker {worker_name} not created..."
        return worker

    def __build_built_in(self, worker_name, config) -> HallonWorker:
        logger.info(f"Constructing and initializing {worker_name}")
        w_type = WorkerFactory.built_in_workers[worker_name]
        w = w_type(config=config, workers=self.instances)
        w.init_worker()
        return w


class WidgetFactory:
    built_in_widgets = {
        'current_time': CurrentTimeWidget,
        'nominal_power': CurrentPower,
        'cumulative_power': CumulativePower,
        'temperature': TemperatureWidget,
        "timer": TimerWidget,
        "door": DoorWidget,
        "lunch": Lunch,
        "current_water": CurrentWater,
        'cumulative_water': CumulativeWater,
        'relay_buttons': RelayWidget

    }

    def __init__(self, widget_configs, worker_factory: WorkerFactory):
        self.widget_configs = widget_configs
        self.worker_factory = worker_factory

    def build_widget(self, widget_config, parent) -> HallonWidget:
        assert widget_config['name'] in self.widget_configs, f"{widget_config['name']} is not a known widget"
        config = self.widget_configs[widget_config['name']]
        if 'config' in widget_config:
            config['config'].update(widget_config['config'])

        if config['source'] == "built-in":
            return self.__build_built_in(parent, config)

    def __build_built_in(self, parent, config) -> HallonWidget:
        workers = {}
        for requiered_worker in config['require_workers']:
            worker = self.worker_factory.build_worker(requiered_worker["worker-name"])
            worker.init_worker()
            alias = requiered_worker['worker-alias'] if 'worker-alias' in requiered_worker else requiered_worker['worker-name']
            workers[alias] = worker

        w_type = WidgetFactory.built_in_widgets[config['type']]
        w = w_type(parent=parent, config=config['config'], workers=workers)
        return w
