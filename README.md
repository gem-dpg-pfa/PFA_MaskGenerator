# PFA_MaskGenerator
Tool that generates the chamber masking file for PFA Efficiency analyzer
------

## Requirements
1. A PEM certificate (the one you use for CRAB submission) is needed to access DQM files stored at this [link](https://cmsweb.cern.ch/dqm/offline/data/browse/ROOT/OnlineData/original/00034xxxx).
   How to obtain the certificate: [twiki](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookStartingGrid#ObtainingCert).
   Make sure you place the p12 certificate file in the `.globus` directory of your `lxplus` home area.

2. A working copy of [P5GEMOfflineMonitor tool](https://github.com/gem-dpg-pfa/P5GEMOfflineMonitor) under the env var *$DCS_TOOL*
   The ouput files of P5GEMOfflineMonitor tool are expected to be found under *$DCS_TOOL/OutputFiles*

## Installation
1. Install the [P5GEMOfflineMonitor tool](https://github.com/gem-dpg-pfa/P5GEMOfflineMonitor)
```bash
cd your_working_directory
git clone git@github.com:gem-dpg-pfa/P5GEMOfflineMonitor.git
cd P5GEMOfflineMonitor
source setup_DCS.sh
```
   Sensitive database information must be added to the script `setup_DCS.sh` (please contact @fsimone91 or @fraivone)

2. Install the [PFA_MaskGenerator tool](https://github.com/gem-dpg-pfa/PFA_MaskGenerator)
```bash
cd your_working_directory
git clone git@github.com:gem-dpg-pfa/PFA_MaskGenerator.git
cd PFA_MaskGenerator
python PFA_MaskGenerator.py -h
```

## Intended WorkFlow
* Based on Run Number, download DQM.root
* From DQM.root, retrieve Start Run UTC time and Stop Run UTC Time
* Based Start/Stop time retrieve DCS.root
* Based on the Expected I eq and the DCS.root produce a JSON file containing list of chambers to be masked with LS info

## Input/Output
This utility takes as **input**
* RunNumberList
* Expected Ieq List (if not specified, Ieq will be inferred from DCS data)

For each run in the RunNumberList this utility produces as **output**
* ChamberOFF_Run_<RunNumber>.json  (a JSON formatted file containing LS to mask for each chamber)
* HV_Status_Run_<RunNumber>.root)  (a ROOT file containing plots)

#### NOTE:
    DCS.root and DQM.root have all timestamps in UTC time

### Typical Output
* JSON File --> ([./ChamberOFF_Run_344681.json](./ChamberOFF_Run_344681.json))
* ROOT File --> ([./HV_Status_Run_344681.root](./HV_Status_Run_344681.root))

