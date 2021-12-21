import os
import io
import re
import sys
import json
import time
import random
import configparser
import traceback
import pandas as pd
import numpy as np
from django.http import HttpResponse
from django.http import JsonResponse
from django.http import HttpResponseBadRequest
import xml.etree.ElementTree as ET
from sklearn.cluster import KMeans

sys.setrecursionlimit(1000000)

cf = configparser.ConfigParser()
cf.read('board/config/board.cfg')

# get Elasticsearch ins
profile = os.environ.get('env', 'develop')
if profile == 'product':
    server_address = '10.166.152.49'
    xml_path = "/home/lteuser/App/data_visualization_back/13037.xml"
    desc_path = "/home/lteuser/App/data_visualization_back/6419_B42_R2B_Final_Version.xlsx"
else:
    server_address = 'localhost'
    xml_path = "D:\\projects\\test\\13037.xml"
    desc_path = "D:\\projects\\test\\6419_B42_R2B_Final_Version.xlsx"

# init xml data
tree = ET.parse(xml_path)
desc = pd.read_excel(desc_path)
root = tree.getroot()
packages = {}

for Package in root.iter('Package'):
    package = {}
    for child in Package.find('Outline').find('Polygon'):
        if child.tag == 'PolyStepSegment':
            if 'PolyStepSegment' not in package.keys():
                package['PolyStepSegment'] = []
            package['PolyStepSegment'].append(child.attrib)
        else:
            package[child.tag] = child.attrib

    _X = list(map(float, (re.findall('\"x\": \"(.*?)\"', json.dumps(package)))))
    _Y = list(map(float, (re.findall('\"y\": \"(.*?)\"', json.dumps(package)))))
    package['width'] = max(_X) - min(_X)
    package['height'] = max(_Y) - min(_Y)
    packages[Package.attrib['name']] = package

components = {}

for Component in root.iter('Component'):
    component = {'packageRef': Component.attrib['packageRef'], 'layerRef': Component.attrib['layerRef']}
    for child in Component:
        component[child.tag] = child.attrib
    width = packages[Component.attrib['packageRef']]['width']
    height = packages[Component.attrib['packageRef']]['height']
    component['packageValue'] = {'width': width, 'height': height}
    component['startLocation'] = {'x': float(component['Location']['x']) - width / 2,
                                  'y': float(component['Location']['y']) - height / 2}
    component['pins'] = []
    components[Component.attrib['refDes']] = component

components_desc = {}
for des, pos in desc[['Func des', 'Pos / Place']].values:
    components_desc[pos.split('/')[0].strip()] = des

logical_nets = {}

for LogicalNet in root.iter('LogicalNet'):
    logical_net = []
    for child in LogicalNet:
        logical_net.append(child.attrib)
    logical_nets[LogicalNet.get('name')] = logical_net

for key in logical_nets.keys():
    for pin in logical_nets[key]:
        if pin['componentRef'] not in components.keys():
            continue
        components[pin['componentRef']]['pins'].append({'pin': pin['pin'], 'net': key})

unfiltered_components = {}
filtered_components = {}

for key in components.keys():
    if len(components[key]['pins']) <= 2:
        filtered_components[key] = components[key]
    else:
        unfiltered_components[key] = components[key]