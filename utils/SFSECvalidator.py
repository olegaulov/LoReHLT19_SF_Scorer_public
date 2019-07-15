#!/usr/bin/env python

import os, sys, glob
import simplejson as json
import jsonschema
import subprocess

#os.environ['UNCOMPRESS_DIR'] = '/Users/ona1/Desktop/uncompressdir/'
#os.environ['FSDB'] = '1'
edlvalidator = "./validate_system_lorehlt2019_edl.pl"
schemafile = "../schemas/LoReHLT19-schema_V1.json"

allFiles = glob.glob(os.environ['UNCOMPRESS_DIR'] + "/*")
if len(allFiles) < 2:
    print(allFiles)
    sys.exit('Error: Expected two files in the submission archive. Received '+ str(len(allFiles)))

tabFiles = glob.glob(os.environ['UNCOMPRESS_DIR'] + "/*.tab")
if len(tabFiles) != 1:
    sys.exit('Error: Expected one .tab EDL file in the submission archive. Received '+ str(len(tabFiles)))

jsonFiles = glob.glob(os.environ['UNCOMPRESS_DIR'] + "/*.json")
if len(jsonFiles) != 1:
    sys.exit('Error: Expected one .json file in the submission archive. Received '+ str(len(jsonFiles)))

p = subprocess.run([edlvalidator + " " + tabFiles[0]], shell=True, capture_output=True)
#print(p.stdout.decode())
if p.returncode:
    sys.exit('Error validating EDL file:\n'+ p.stdout.decode())


p = subprocess.run(['./validate_system_lorehlt2019_edl.pl ' + tabFiles[0]], shell=True, capture_output=True)
#print(p.stdout.decode())
if p.returncode:
    sys.exit('Error validating EDL file:\n'+ p.stdout.decode())

try:
    with open(schemafile, 'r') as f:
        schema_data = f.read()
        schema = json.loads(schema_data)
except:
    sys.exit('CAN NOT OPEN JSON SCHEMA FILE: '+ schemafile)

try:
    with open(jsonFiles[0]) as f:
        d = json.load(f)
except:
    sys.exit('CAN NOT OPEN JSON SUBMISSION FILE: '+ jsonFiles[0])

try:
    jsonschema.validate(d, schema)
except Exception as e:
    print(e)
    sys.exit('ERROR: System submission json failed validation:\n' + str(e) + '\n')

