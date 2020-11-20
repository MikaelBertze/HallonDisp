import asyncio
from time import time, sleep
import mariadb
from hallondisp.hallon_workers import PowerWorker
from hallondisp.factories import WorkerFactory
import hallondisp.configreader as config_reader
#workers

def add_to_db(conn, sensor_id, value1, value2):
    ts = time()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO measurements (TimeStamp_ms,SensorId,Value1,Value2) VALUES (?, ?, ?, ?)",
        (int(ts*1000), sensor_id, float(value1), 0.0))
    conn.commit()

    print ("done")
    print(ts)


if __name__ == "__main__":

    try:
        conn = mariadb.connect(
            user="hallondisp",
            password="hallondisp",
            host="localhost",
            port=3306,
            database="hallondisp"
        )
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        exit(1)


    #read config
    config = config_reader.read_json_config('./hallondisp.json')
    worker_factory = WorkerFactory(config['workers'])

    worker: PowerWorker = worker_factory.build_worker("power-worker")
    worker.whenPowerReported.subscribe(lambda x: add_to_db(conn, 'power', x['power'], None))

    #worker.init_worker()


    while True:
        sleep(1)
    # loop = asyncio.get_event_loop()
    # try:
    #     loop.run_forever()
    # finally:
    #     worker.kill()
    #     loop.close()
    #
