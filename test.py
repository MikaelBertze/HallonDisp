
from hallondisp import mqtt_utils as mqtt
from hallondisp.factories import WorkerFactory
from hallondisp.hallon_workers import PowerWorker, CumulativePowerWorker
from hallondisp import configreader as cr


def mqtt_updater():
    updater = mqtt.MqttUpdater("192.168.1.150", "/megatron/electricityticker/tickperiod")
    updater.OnMessage.subscribe(lambda x: print(x))
    updater.start()
    updater.join()

def power_worker():
    config = {}
    config['mqtt'] = {}
    config['mqtt']['broker'] = "192.168.1.150"
    config['mqtt']['topic'] = "/megatron/electricityticker/tickperiod"

    worker = PowerWorker(config)
    worker.whenPowerReported.subscribe(lambda x: print(f"power: {x}"))
    worker.whenHourUsageReported.subscribe(lambda x: print(f"hour usage: {x}"))
    worker.whenDayUsageReported.subscribe(lambda x: print(f"daily usage: {x}"))

    worker.init_worker()

def worker_factory():
    config = cr.read_json_config('hallondisp.json')
    factory = WorkerFactory(config['workers'])

    worker1: CumulativePowerWorker = factory.build_worker('cumulative-power-worker-minute')
    worker1.whenUsageReported.subscribe(lambda x: print(f"minute usage: {x}"))
    worker1.init_worker()

    worker2: CumulativePowerWorker = factory.build_worker('cumulative-power-worker-hour')
    worker2.whenUsageReported.subscribe(lambda x: print(f"hour usage: {x}"))
    worker2.init_worker()

    worker3: CumulativePowerWorker = factory.build_worker('cumulative-power-worker-day')
    worker3.whenUsageReported.subscribe(lambda x: print(f"day usage: {x}"))
    worker3.init_worker()

worker_factory()

input("Press Enter to exit...")