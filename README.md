# PFA_MaskGenerator
Tool that generates the chamber masking file for PFA Efficiency analyzer
# Working version... still to be fully tested and optimized
------

## Requirements
1. A PEM certificate (the one you use for CRAB submission) is needed to access DQM files stored at this (link)[https://cmsweb.cern.ch/dqm/offline/data/browse/ROOT/OnlineData/original/00034xxxx]. Currently in the code it is hardcoded my PEM certificate path....adjust according to yours
1. A working copy of [Simone's tool](https://github.com/simonepv/P5GEMOfflineMonitor) under the env var *$DCS_TOOL*
    * You might need to set some env var to make Simone's tool work
1. The ouput files of Simone's tool are expected to be found under *$DCS_TOOL/OutputFiles*

## Intended WorkFlow
* Based on Run Number, download DQM.root
* From DQM.root, retrieve Start Run UTC time and Stop Run UTC Time
* Based Start/Stop time retrieve DCS.root using Simone's tool [here](https://github.com/simonepv/P5GEMOfflineMonitor)
* Based on the Expected I eq and the DCS.root produce a JSON file containing list of chambers to be masked with LS info

## Input/Output
This utility takes as **input**
* RunNumberList
* Expected Ieq List
For each run in the RunNumberList this utility produces as **output**
* ChamberOFF_Run_<RunNumber>.json  (a JSON formatted file containing LS to mask for each chamber)
* HV_Status_Run_<RunNumber>.root)  (a ROOT file containing plots)

#### NOTE:
    DCS.root and DQM.root have all timestamps in UTC time

### Typical Output
* JSON File --> ([./ChamberOFF_Run_344681.json](./ChamberOFF_Run_344681.json))
* ROOT File --> ([./HV_Status_Run_344681.root](./HV_Status_Run_344681.root))


## How are bad Lumisection identified
For a given Run in P5, PFA needs to know which SuperChambers were operated at the expected
Ieq, HV trips (if any).
Three manipulations have to be made DCS.root to find out which SuperChambers had Ieq != Ieq expected:
    
1. Unify (extend) all 7 HV channels of a given SuperChambers on the widest possible time range
1. Fill the gaps: since the DCS stores HV data only in case of a change, there are time gaps which are not good for analysis.
       The manipulation consists in checking the previous HV value of a channel and extrapolating it in the "future" assuming it didn't change
1. Once unified and gap filled, sum up HV of all 7 channels to get HV of the SuperChambers and then convert it to Ieq (which is the standard for CMS GEM HV)   
   Then the time window for Ieq != Ieq expected is derived and finally converted in LumiSection based on Run start time (UTC Format) and #LS (taken from DQM online)