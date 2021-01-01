#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json


def readconfig():
    with open("config.json") as json_data_file:
        return json.load(json_data_file)
