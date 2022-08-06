#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import socket
import sys
import time
import pathlib
import importlib
import logging
import fluent.sender

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, "lib"))

from config import load_config
import logger


SENSOR_MODULE_LIST = ["scd4x", "max31856", "sht35"]


def load_sensor():
    sensor_list = []
    for name in SENSOR_MODULE_LIST:
        logging.info("Load {name}".format(name=name))
        mod = importlib.import_module("sensor." + name)
        sensor_list.append(getattr(mod, name.upper())())

    return sensor_list


def sense(sensor_list):
    value_map = {}
    for sensor in sensor_list:
        logging.info(
            "Measurements are being taken using {name}".format(name=sensor.NAME)
        )
        val = sensor.get_value_map()
        logging.info(val)
        value_map.update(val)

    logging.info("Mearged measurements: {result}".format(result=str(value_map)))

    return value_map


######################################################################
logger.init("Enviorment Sensor")

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

hostname = os.environ.get("NODE_HOSTNAME") or socket.gethostname()

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
        logging.error(fluent_logger.last_error)

    logging.info(
        "sleep {sleep_time} sec...".format(sleep_time=config["sense"]["interval"])
    )
    time.sleep(config["sense"]["interval"])
