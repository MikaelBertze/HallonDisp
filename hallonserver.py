import asyncio
from time import time, sleep
import mariadb
from hallondisp.hallon_workers import PowerWorker, WaterWorker
from hallondisp.factories import WorkerFactory
import hallondisp.configreader as config_reader


def add_to_db(conn, sensor_id, value1, value2=0.0):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO measurements (TimeStamp,SensorId,Value1,Value2) VALUES (CURRENT_TIMESTAMP(3), ?, ?, ?)",
        (sensor_id, value1, value2))
    conn.commit()


def handle_water_report(x):
    if float(x['consumption']) > .001:
        add_to_db(conn, 'water', float(x['consumption']), float(x['t_diff']) / 1000.0)


if __name__ == "__main__":

    try:
        conn = mariadb.connect(
            user="hallondisp",
            password="hallondisp",
            host="127.0.0.1",
            port=3306,
            database="hallondisp"
        )
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        exit(1)

    config = config_reader.read_json_config('./hallondisp.json')
    worker_factory = WorkerFactory(config['workers'])

    power_worker: PowerWorker = worker_factory.build_worker("power-worker")
    power_worker.whenPowerReported.subscribe(lambda x: add_to_db(conn, 'power', float(x['power']), None))

    water_worker: WaterWorker = worker_factory.build_worker("water-worker")
    water_worker.whenWaterReported.subscribe(handle_water_report)

    while True:
        sleep(1)
