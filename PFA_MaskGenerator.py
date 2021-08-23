#!/usr/bin/env python
"""Provides a tool able to generate masking files for PFA Efficiency analyzer
   For a given Run in P5, PFA needs to know which SuperChambers were operated at the expected
   Ieq, HV trips (if any).
   It has been chosen to analyze the DCS_dump file. Three manipulations have to be made 
   to find out which SuperChambers had Ieq != Ieq expected:
    1. Unify (extend) all 7 HV channels of a given SuperChambers on the widest possible time range
    2. Fill the gaps: since the DCS stores HV data only in case of a change, there are time gaps which are not good for analysis.
       The manipulation consists in checking the previous HV value of a channel and extrapolating it in the "future" assuming it didn't change
    3. Once unified and gap filled, sum up HV of all 7 channels to get HV of the SuperChambers and then convert it to Ieq (which is the standard for CMS GEM HV)   
   Then the time window for Ieq != Ieq expected is derived and finally converted in LumiSection based on Run start time (UTC Format) and #LS (taken from DQM online)

   This utility takes as input 
   - RunNumber
   - Expected I eq
   This utility produces as output 
   - ChamberOFF_Run_<RunNumber>.json 
        (a JSON formatted file containing LS to mask for each chamber)

   NOTE:
    DCS.root and DQM.root have all timestamps in UTC time
"""
import ROOT
import datetime
import time
import json
import argparse
from argparse import RawTextHelpFormatter



__author__ = "Francesco Ivone"
__copyright__ = "Copyright 2021, CMS GEM"
__credits__ = ["Simone Calzaferri, Monika Mittal"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Francesco Ivone"
__email__ = "francesco.ivone@cern.ch"
__status__ = "DevelopAlpha"
__comment__ = "Developed on (another) rainy day"



def ReChLa2chamberName(re,ch,la):
    endcap = "M" if re == -1 else "P"
    size = "S" if ch%2 == 1 else "L"
    chID = 'GE11-'+endcap+'-%02d' % ch +"L"+str(la)+"-"+size 
    return chID

def UTCtime_2_LS(UTC_timestamp,RunStart_TimeStamp):
    global SECONDS_PER_LUMISECTION
    
    LS = float(UTC_timestamp-RunStart_TimeStamp)/SECONDS_PER_LUMISECTION
    return LS

## Save the ROOT obj in the TFile according to the path specified in directory.
def writeToTFile(file,obj,directory=None):
    if directory != None:
        if bool(file.GetDirectory(directory)):
            Tdir = file.GetDirectory(directory)
        else:
            file.mkdir(directory)
            Tdir = file.GetDirectory(directory)
        Tdir.cd()
    else:
        file.cd()
    
    obj.Write()


parser = argparse.ArgumentParser(
        description='''Scripts that generates chamber mask file for PFA Efficiency analyzer for a given run.\nIf for a given LS a chamber has Ieq != Ieq_Expected it will be listed in the OutputFile --> ChamberOFF_Run_<RunNumber>.json.\nThe scripts interrogates DCS and DQM to fetch the run conditions''',
        epilog="""Typical exectuion\n\t python PFA_MaskGenerator.py  --run 343266  --ieq_expected 690""",
        formatter_class=RawTextHelpFormatter
)

parser.add_argument('-r','--run', type=int,help="Run Number ",required=True)
parser.add_argument('-iexp','--ieq_expected', type=int,help="Expected ieq for the run",required=True)
args = parser.parse_args()

ROOT.gROOT.SetBatch(True)

## Inputs
DCS_dump_file = "./P5_GEM_HV_monitor_UTC_start_2021-07-30_00-00-01_end_2021-07-31_23-59-59.root"
RunStartTime_UTC = "2021-07-30_19-28-00"

N_LumiSections = 890
SECONDS_PER_LUMISECTION = 24
desiredIeq = args.ieq_expected
granularity = 20 # max delta t between 2 points --> has to be less than SECONDS_PER_LUMISECTION
RunNumber = args.run
## End Inputs

RunStart_TimeStamp = time.mktime(time.strptime(RunStartTime_UTC, '%Y-%m-%d_%H-%M-%S'))
RunStop_TimeStamp = RunStart_TimeStamp + N_LumiSections*SECONDS_PER_LUMISECTION
print "\n### Run",RunNumber,"conditions ###"
print "\nRun Starts on ", datetime.datetime.fromtimestamp(RunStart_TimeStamp).strftime('%Y-%m-%d %H:%M:%S')
print "Run Stops on ", datetime.datetime.fromtimestamp(RunStop_TimeStamp).strftime('%Y-%m-%d %H:%M:%S')
print "\n"


try:
    inFile = ROOT.TFile.Open(DCS_dump_file ,"READ")
except:
    print ("ERROR:\n\tCan't open the input\n\t"+DCS_dump_file+"\n\twith ROOT\nEXITING...\n")
    sys.exit(0)

MaskDict = {}
ieq_graph = {}
runStart_TLine = {}
runStop_TLine = {}

c_positive_encap = ROOT.TCanvas("Positive Endcap","Positive Endcap",1600,900)
c_negative_encap = ROOT.TCanvas("Negative Endcap","Negative Endcap",1600,900)
c_positive_encap.Divide(6,6)
c_negative_encap.Divide(6,6)
OutF = ROOT.TFile("./HV_Status_Run_"+str(RunNumber)+".root","RECREATE")

## Looping over all SCs
for endcap in [1,-1]:
    for ch_n in range(1,37):
        ch = '%02d' %ch_n
        re = "_" if endcap == -1 else "+"
        SC_ID = "SC GE"+re+ch

        ChID_L1 = ReChLa2chamberName(endcap,ch_n,1)
        ChID_L2 = ReChLa2chamberName(endcap,ch_n,2)        

        MaskDict.setdefault(ChID_L1,[])
        MaskDict.setdefault(ChID_L2,[])
        ieq_graph[SC_ID] = ROOT.TGraph()
        runStart_TLine[SC_ID] = ROOT.TLine(RunStart_TimeStamp,0,RunStart_TimeStamp,750)
        runStop_TLine[SC_ID] = ROOT.TLine(RunStop_TimeStamp,0,RunStop_TimeStamp,750)

        ## Fetching
        try:
            G1Top = inFile.Get("GE"+re+"1_1_"+ch+"/HV_VmonChamberGE"+re+"1_1_"+ch+"_G1Top_UTC_time")
            G2Top = inFile.Get("GE"+re+"1_1_"+ch+"/HV_VmonChamberGE"+re+"1_1_"+ch+"_G2Top_UTC_time")
            G3Top = inFile.Get("GE"+re+"1_1_"+ch+"/HV_VmonChamberGE"+re+"1_1_"+ch+"_G3Top_UTC_time")
            G1Bot = inFile.Get("GE"+re+"1_1_"+ch+"/HV_VmonChamberGE"+re+"1_1_"+ch+"_G1Bot_UTC_time")
            G2Bot = inFile.Get("GE"+re+"1_1_"+ch+"/HV_VmonChamberGE"+re+"1_1_"+ch+"_G2Bot_UTC_time")
            G3Bot = inFile.Get("GE"+re+"1_1_"+ch+"/HV_VmonChamberGE"+re+"1_1_"+ch+"_G3Bot_UTC_time")
            Drift = inFile.Get("GE"+re+"1_1_"+ch+"/HV_VmonChamberGE"+re+"1_1_"+ch+"_Drift_UTC_time")
        except:
            print "Couldn't find data for ",SC_ID,"... Skipping"

        fetched_graph = [G1Top,G2Top,G3Top,G1Bot,G2Bot,G3Bot,Drift]
        
        ## Skip SCs having only 1 point cause it is associated w/ no variation in HV ==> Garbage data
        try:
            for graph in fetched_graph:
                if graph.GetN() < 2:
                    print graph.GetTitle()," has too few points... skipping ", SC_ID
                    raise RuntimeError
        except RuntimeError:
            continue


        firstX = [ ROOT.Double() for i in range(0,7)]
        firstY = [ ROOT.Double() for i in range(0,7)]
        lastX = [ ROOT.Double() for i in range(0,7)]
        lastY = [ ROOT.Double() for i in range(0,7)]
        newGraph = [ROOT.TGraph() for i in range(0,7)]
        temp_x, temp_y = ROOT.Double(),ROOT.Double()


        ## Evaluating widest range in which at least 1 of the channels has data
        for index,graph in enumerate(fetched_graph):
            graph.GetPoint(0,firstX[index],firstY[index])
            graph.GetPoint(graph.GetN()-1,lastX[index],lastY[index])

            previous_x = firstX[index]
            previous_y = firstY[index]

        lastTimestamp = max(lastX)
        firstTimestamp = min(firstX)

        ## Creating an extendend version of previous graphs, covering the whole time range
        ## and with points spaced no more than granularity
        for index,graph in enumerate(fetched_graph):
            new_graph_point = 0
            previous_x = firstTimestamp
            previous_y = firstY[index]
            # Extending backward
            for point in range(0,graph.GetN()):
                graph.GetPoint(point,temp_x,temp_y)

                if temp_x - previous_x <= granularity:
                    newGraph[index].SetPoint(new_graph_point,temp_x,temp_y)
                    new_graph_point+=1
                else:
                    for i in range(int((temp_x-previous_x)/granularity)):
                        newGraph[index].SetPoint(new_graph_point,previous_x+i*granularity,previous_y)
                        new_graph_point+=1

                previous_x = float(temp_x)
                previous_y = float(temp_y)
            # Extending forward
            for i in range(int((lastTimestamp-previous_x)/granularity)):
                newGraph[index].SetPoint(new_graph_point,previous_x+i*granularity,previous_y)
                new_graph_point+=1

        
        ## Generating the final plot
        for i in range(int((lastTimestamp - firstTimestamp )/granularity)):
            secondsSinceEpoch = firstTimestamp + i*granularity

            evaluatedVoltages = [graph.Eval(secondsSinceEpoch) if  secondsSinceEpoch>= firstX[index] else firstY[index] for index,graph in enumerate(newGraph)]

            stackedVoltage = sum(evaluatedVoltages)
            ieq = stackedVoltage/4.7

            if secondsSinceEpoch > RunStart_TimeStamp and secondsSinceEpoch < RunStop_TimeStamp and abs(ieq - desiredIeq) >= 5:
                LS = int(UTCtime_2_LS(secondsSinceEpoch,RunStart_TimeStamp))
                MaskDict[ChID_L1].append(LS)
                MaskDict[ChID_L2].append(LS)

            ieq_graph[SC_ID].SetPoint(i,secondsSinceEpoch,ieq)


        ieq_graph[SC_ID].SetTitle(SC_ID)
        ieq_graph[SC_ID].SetName(SC_ID)
        ieq_graph[SC_ID].GetYaxis().SetTitle("Equivalent Divider Current (uA)")
        ieq_graph[SC_ID].GetXaxis().SetTitle("UTC Date Time")
        ieq_graph[SC_ID].GetXaxis().SetTitleOffset(1.35)
        ieq_graph[SC_ID].SetMarkerStyle(20)
        ieq_graph[SC_ID].SetMinimum(0)
        ieq_graph[SC_ID].SetMaximum(750)
        ieq_graph[SC_ID].GetXaxis().SetTimeDisplay(1)
        ieq_graph[SC_ID].GetXaxis().SetNdivisions(-503)
        ieq_graph[SC_ID].GetXaxis().SetLabelOffset(0.025)
        ieq_graph[SC_ID].GetXaxis().SetLabelSize(0.02)
        ieq_graph[SC_ID].GetXaxis().SetTimeFormat("#splitline{%y-%m-%d}{%H:%M:%S}%F1970-01-01 00:00:00")
        ieq_graph[SC_ID].GetXaxis().SetTimeOffset(0,"UTC")

        runStart_TLine[SC_ID].SetLineColor(ROOT.kGreen +2)
        runStop_TLine[SC_ID].SetLineColor(ROOT.kRed)

        writeToTFile(OutF,ieq_graph[SC_ID],"SCs")

        if endcap == 1:
            print SC_ID
            pad = c_positive_encap.cd(ch_n)
            ieq_graph[SC_ID].Draw("AP")
            runStart_TLine[SC_ID].Draw()
            runStop_TLine[SC_ID].Draw()
            c_positive_encap.Modified()
            c_positive_encap.Update()
        if endcap == -1:
            print SC_ID
            pad = c_negative_encap.cd(ch_n)
            ieq_graph[SC_ID].Draw("AP")
            runStart_TLine[SC_ID].Draw()
            runStop_TLine[SC_ID].Draw()
            c_negative_encap.Modified()
            c_negative_encap.Update()

        ## Remove duplicate LSs
        MaskDict[ChID_L1] = list(set(MaskDict[ChID_L1]))
        MaskDict[ChID_L2] = list(set(MaskDict[ChID_L2]))
        ## If always bad, put -1
        if len(MaskDict[ChID_L1]) == N_LumiSections:
            MaskDict[ChID_L1] = [-1]
        if len(MaskDict[ChID_L2]) == N_LumiSections:
            MaskDict[ChID_L2] = [-1]

writeToTFile(OutF,runStart_TLine[SC_ID],"SCs")
writeToTFile(OutF,runStop_TLine[SC_ID],"SCs")
writeToTFile(OutF,c_negative_encap)
writeToTFile(OutF,c_negative_encap)

jsonFile = open("ChamberOFF_Run_"+str(RunNumber)+".json", "w")
json_data = json.dumps(MaskDict) 
jsonFile.write(json_data)

print "\n### Output produced ###"
print "\tChamberOFF_Run_"+str(RunNumber)+".json"
print "\tHV_Status_Run_"+str(RunNumber)+".root"