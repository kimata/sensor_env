#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import socket
import sys
import time
import pathlib
import importlib
import logging
import traceback
import fluent.sender

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, "lib"))

from config import load_config
import logger

RASP_I2C_BUS_ARM = 0x1  # Raspberry Pi のデフォルトの I2C バス番号
RASP_I2C_BUS_VC = 0x0  # dtparam=i2c_vc=on で有効化される I2C のバス番号

SENSOR_MODULE_LIST = [
    {"name": "scd4x", "bus": RASP_I2C_BUS_ARM},
    {"name": "max31856", "bus": RASP_I2C_BUS_ARM},
    {"name": "sht35", "bus": RASP_I2C_BUS_ARM},
    {"name": "apds9250", "bus": RASP_I2C_BUS_ARM},
    {"name": "veml6075", "bus": RASP_I2C_BUS_VC},
]


def load_sensor():
    sensor_list = []
    for sensor in SENSOR_MODULE_LIST:
        logging.info("Load {name}".format(name=sensor["name"]))
        mod = importlib.import_module("sensor." + sensor["name"])
        sensor_list.append(getattr(mod, sensor["name"].upper())(bus=sensor["bus"]))

    return sensor_list


def sense(sensor_list):
    value_map = {}
    for sensor in sensor_list:
        try:
            logging.info(
                "Measurements are being taken using {name}".format(name=sensor.NAME)
            )
            val = sensor.get_value_map()
            logging.info(val)
            value_map.update(val)
        except:
            logging.error(traceback.format_exc())

    logging.info("Mearged measurements: {result}".format(result=str(value_map)))

    return value_map


######################################################################
logger.init("sensor.enviorment")

logging.info("Load config...")
config = load_config()

logging.info("Load sensors...")
sensor_list = load_sensor()
logging.info("Check sensor existences...")
sensor_list = list(filter(lambda sensor: sensor.ping(), sensor_list))

logging.info(
    "Active sensor list: {sensor_list}".format(
        sensor_list=", ".join(map(lambda sensor: sensor.NAME, sensor_list))
    )
)

hostname = os.environ.get("NODE_HOSTNAME", socket.gethostname())

logging.info("Hostanm: {hostname}".format(hostname=hostname))

sender = fluent.sender.FluentSender("sensor", host=config["fluent"]["host"])
while True:
    logging.info("Start.")

    value_map = sense(sensor_list)
    value_map.update({"hostname": hostname})

    if sender.emit("rasp", value_map):
        logging.info("Finish.")
        pathlib.Path(config["liveness"]["file"]).touch()
    else:
        logging.error(sender.last_error)

    logging.info(
        "sleep {sleep_time} sec...".format(sleep_time=config["sense"]["interval"])
    )
    time.sleep(config["sense"]["interval"])
