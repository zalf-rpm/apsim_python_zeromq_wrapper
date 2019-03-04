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
import os
import sys
#print sys.path
import zmq
import uuid
import shutil
#print "pyzmq version: ", zmq.pyzmq_version(), " zmq version: ", zmq.zmq_version()

#import soil_io

PATHS = {
    "berg": {
        #"path-to-climate-dir": "N:/climate/",
        "path_to_temp_storage": "R:/"
    }
}

def extract_output_filenames(xml):
    "extract from the APSIM xml file the output filenames"

    output_filenames = []

    sim = xml.folder.simulation["name"]
    area = xml.folder.simulation.area["name"]
    if area == "paddock":
        area = ""
    else:
        area = " " + area
    for tag in xml.find_all("outputfile"):
        tag_name = "" if "name" not in tag.attrs else " " + tag["name"]
        output_filenames.append(sim + area + tag_name + ".out")

    return output_filenames


def process_message(msg, out_socket, temp_path):

    if msg == "stop":
        return True

    try: 
        # create a temporary folder for the apsim data
        uid = uuid.uuid4()
        print(str(uid))
        temp_path = temp_path + str(uid) + "/"
        os.makedirs(temp_path, exist_ok=True)

        # read APSIM xml file content
        apsim_xml = msg["apsim_xml"]
        xml = BeautifulSoup(apsim_xml, "lxml-xml")
        
        # create/reference the met file and add the path to the APSIM XML file
        path_to_met_file = msg["met_path"]
        if not path_to_met_file and msg["met_content"]:
            path_to_met_file = temp_path + "___apsim_met.met"
            with open(path_to_met_file, "w") as _:
                _.write(msg["met_content"])
        xml.folder.simulation.metfile.filename.string = path_to_met_file

        # create temporary APSIM input file
        path_to_temp_input_file = temp_path + "___apsim_input.apsim"
        with open(path_to_temp_input_file, "w") as _:
            _.write(str(xml))
        
        # should we produce a .sum file (will be produces anyway, but just with one line)
        include_sum_file = msg.get("include_sum", False)

        # call APSIM
        cmd_call = ["apsim", path_to_temp_input_file]
        if not include_sum_file:
            cmd_call.append("MaxOutputLines=1")
        subprocess.call(cmd_call)

        # the result message template
        msg_template = {
            "id": msg.get("id", None),
            "outputs": {},
        }

        # if requested include sum file
        if include_sum_file:
            sum_filename = xml.folder.simulation["name"] + ".sum"
            with open(temp_path + sum_filename) as _:
                msg_template["outputs"][sum_filename] = _.read()

        # read all results from the output files
        for output_filename in extract_output_filenames(xml):
            with open(temp_path + output_filename, "r") as _:
                msg_template["outputs"][output_filename] = _.read()
                
        # send result
        out_socket.send_json(msg_template)

        # remove the temp file and the output file
        shutil.rmtree(temp_path, ignore_errors=True)

    except Exception as e:
        sys.stderr.write(str(e))
        out_socket.send_json({"error": str(e)})

    return False

def run():

    config = {
        "user": "berg",
        "in_port": "5551",
        "out_port": "5552", 
        "temp_folder": None
    }
    if len(sys.argv) > 1 and __name__ == "__main__":
        for arg in sys.argv[1:]:
            k,v = arg.split("=")
            if k in config:
                config[k] = v

    paths = PATHS[config["user"]]
    if config["temp_folder"]:
        paths["path_to_temp_storage"] = config["temp_folder"]

    print("config:", config)

    context = zmq.Context.instance()
    in_socket = context.socket(zmq.PULL)
    in_socket.bind("tcp://*:" + config["in_port"])
    out_socket = context.socket(zmq.PUSH)
    out_socket.bind("tcp://*:" + config["out_port"])

    leave = False

    while not leave:
        try:
            msg = in_socket.recv_json()
            leave = process_message(msg, out_socket, paths["path_to_temp_storage"])
        except Exception as e:
            sys.stdout.write(str(e))
            continue

    print("exiting run()")

if __name__ == "__main__":
    run()