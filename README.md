# PFA_MaskGenerator
Tool that generates the chamber masking file for PFA Efficiency analyzer
------

## Requirements
1. A PEM certificate (the one you use for CRAB submission) is needed to access DQM files stored at this [link](https://cmsweb.cern.ch/dqm/offline/data/browse/ROOT/OnlineData/original/00034xxxx).
   How to obtain the certificate: [twiki](https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookStartingGrid#ObtainingCert).
   Make sure you place the p12 certificate file in the `.globus` directory of your `lxplus` home area.

2. A working copy of [P5GEMOfflineMonitor tool](https://github.com/gem-dpg-pfa/P5GEMOfflineMonitor) under the env var *$DCS_TOOL*
   The ouput files of P5GEMOfflineMonitor tool are expected to be found under *$DCS_TOOL/OutputFiles*
   
3. Python libraries:
```bash
pip2 install  numpy==1.9.0 --user
pip2 install  scipy==1.1.0 --user
```

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

## How to execute
```bash
cd your_working_directory/P5GEMOfflineMonitor
source setup_DCS.sh
cd ../PFA_MaskGenerator
python PFA_MaskGenerator.py -r 344681,344680  --ieq_expected_list 700,700
```
If argument `--ieq_expected_list` is not provided, expected HV setting (equivalent divider current) is inferred from the DCS data as the value set to the majority of the 72 chambers.

## Intended WorkFlow
- [x] Based on Run Number, download DQM.root
- [x] From DQM.root, retrieve Start Run UTC time and Stop Run UTC Time
- [ ] From DQM.root, retrieve list of chambers/VFATs undergoing DAQ errors during data taking (assigned to @caruta)
- [x] Based Start/Stop time retrieve DCS.root
- [x] From DCS.root extract Ieq vs time for all the chambers
- [x] Based on expected Ieq compared with effective Ieq from DCS, store timestamps corresponding to chamber off/tripping/set to low HV
- [x] Convert time to lumisection and store in a JSON file for further analysis

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

