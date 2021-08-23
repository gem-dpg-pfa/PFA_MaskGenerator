# PFA_MaskGenerator
Tool that generates the chamber masking file for PFA Efficiency analyzer
# Still Under Construction
------

## Intended WorkFlow
* Based on Run Number, download DQM.root
* From DQM.root, retrieve Start Run UTC time and Stop Run UTC Time
* Based Start/Stop time retrieve DCS.root using Simone's tool [here](https://github.com/simonepv/P5GEMOfflineMonitor)
* Based on the Expected I eq and the DCS.root produce a JSON file containing list of chambers to be masked with LS info
### Description
Provides a tool able to generate masking files for PFA Efficiency analyzer
For a given Run in P5, PFA needs to know which SuperChambers were operated at the expected
Ieq, HV trips (if any).
It has been chosen to analyze the DCS_dump file. Three manipulations have to be made 
to find out which SuperChambers had Ieq != Ieq expected:
    
1. Unify (extend) all 7 HV channels of a given SuperChambers on the widest possible time range
1. Fill the gaps: since the DCS stores HV data only in case of a change, there are time gaps which are not good for analysis.
       The manipulation consists in checking the previous HV value of a channel and extrapolating it in the "future" assuming it didn't change
1. Once unified and gap filled, sum up HV of all 7 channels to get HV of the SuperChambers and then convert it to Ieq (which is the standard for CMS GEM HV)   
   Then the time window for Ieq != Ieq expected is derived and finally converted in LumiSection based on Run start time (UTC Format) and #LS (taken from DQM online)

This utility takes as input 
* RunNumber
* Expected I eq
   
This utility produces as output 
* ChamberOFF_Run_<RunNumber>.json  (a JSON formatted file containing LS to mask for each chamber)

#### NOTE:
    DCS.root and DQM.root have all timestamps in UTC time

### Typical Output
* JSON File --> ([./ChamberOFF_Example.txt](./ChamberOFF_Run_343266.json))
* ROOT File --> ([./HV_Status_Run_343266.root](./HV_Status_Run_343266.root))