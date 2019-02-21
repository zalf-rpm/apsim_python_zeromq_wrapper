#!/usr/bin/python
# -*- coding: UTF-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/. */

# Authors:
# Michael Berg-Mohnicke <michael.berg@zalf.de>
#
# Maintainers:
# Currently maintained by the authors.
#
# This file has been created at the 
# Research Platform Models (RPM) at ZALF.
# Copyright (C: Leibniz Centre for Agricultural Landscape Research (ZALF)

#import types
#import time
#import os
#import math
#import json
#import csv
#import copy
#from StringIO import StringIO
#from datetime import date, datetime, timedelta
#from collections import defaultdict, OrderedDict

from bs4 import BeautifulSoup
import subprocess
import sys
import json
#print sys.path
import zmq
#print "pyzmq version: ", zmq.pyzmq_version(), " zmq version: ", zmq.zmq_version()

#import soil_io

PATHS = {
    "berg": {
        "path-to-climate-dir": "N:/climate/",
    }
}

def run():

    config = {
        "user": "berg",
        "port": "5551",
        "apsim_path": "in/canola.apsim",
        "met_path": "Goettingen.met",
        "remote_met_path": None
    }
    if len(sys.argv) > 1 and __name__ == "__main__":
        for arg in sys.argv[1:]:
            k,v = arg.split("=")
            if k in config:
                config[k] = v

    #paths = PATHS[config["user"]]

    print("config:", config)

    context = zmq.Context.instance()
    socket = context.socket(zmq.PUSH)
    socket.connect("tcp://localhost:" + config["port"])

    msg_template = {
        "id": 1,
        "apsim_xml": None,
        "met_content": None,
        "met_path": config["remote_met_path"],
        "include_sum": True
    }

    with open(config["apsim_path"], "r") as _:
        msg_template["apsim_xml"] = _.read()
    
    if not msg_template["met_path"] and config["met_path"]:
        with open(config["met_path"]) as _:
            msg_template["met_content"] = _.read()
    
    socket.send_json(msg_template)

    print("exiting run()")

if __name__ == "__main__":
    run()