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
   - RunNumberList
   - Expected Ieq List
   For each run in the RunNumberList this utility produces as output 
   - ChamberOFF_Run_<RunNumber>.json 
        (a JSON formatted file containing LS to mask for each chamber)
   - HV_Status_Run_<RunNumber>.root)
        (a ROOT file containing plots)

   NOTE:
    DCS.root and DQM.root have all timestamps in UTC time
"""
import ROOT
import datetime
import time
import json
import argparse
from argparse import RawTextHelpFormatter
import os
import re
import pytz
import sys


__author__ = "Francesco Ivone"
__copyright__ = "Copyright 2021, CMS GEM"
__credits__ = ["Simone Calzaferri, Monika Mittal, Federica Simone"]
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

# Input must be formatted like "%Y-%m-%d %H:%M:%S"
def BerlinTime_2_UTC(Berlin_Datetime):
    local = pytz.timezone("Europe/Berlin")
    local_datetime = datetime.datetime.strptime(Berlin_Datetime, "%Y-%m-%d_%H:%M:%S")
    local_dt = local.localize(local_datetime, is_dst=None)
    utc_dt = local_dt.astimezone(pytz.utc)
    Datetime_UTC = utc_dt.strftime("%Y-%m-%d_%H:%M:%S")
    TimeStamp_UTC = time.mktime(time.strptime(Datetime_UTC, "%Y-%m-%d_%H:%M:%S"))

    return Datetime_UTC,TimeStamp_UTC

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
            description='''Scripts that generates chamber mask file for PFA Efficiency analyzer for a given run.\nIf for a given LS a chamber has Ieq != Ieq_Expected it will be listed in the OutputFile --> ChamberOFF_Run_<RunNumber>.json.\nThe scripts interrogates DCS and DQM to fetch the run conditions''',
            epilog="""Typical exectuion\n\t python PFA_MaskGenerator.py  --RunNumberList 344681 344680 344679  --ieq_expected_list 690 690 700""",
            formatter_class=RawTextHelpFormatter
    )
    
    parser.add_argument('-rl','--RunNumberList', type=int,help="Run Number List ",required=True,nargs='*')
    parser.add_argument('-iexpl','--ieq_expected_list', type=int,help="Expected list of ieq for the run list",required=True,nargs='*')
    args = parser.parse_args()
    
    ROOT.gROOT.SetBatch(True)
    
    ## Inputs
    DesiredIeqList = args.ieq_expected_list
    RunNumberList = args.RunNumberList
    SECONDS_PER_LUMISECTION = 24
    granularity = 20 # max delta t between 2 points --> has to be less than SECONDS_PER_LUMISECTION
    ## End Inputs
    
    
    ## Mapping RunNumber to associated DesiredIeq in a Dict
    if len(RunNumberList) != len(DesiredIeqList):
        print "RunNumberList,desiredIeqList \tparsed argument of different sizes...\nExiting .."
        sys.exit(0)
    
    Run2DesiredIeq = {}
    Run2DQM_FileName = {}     
    ##
    
    
    ## Fetching multiple DQM.root
    # Using a .txt containing all the desired addresses in order to insert the PEM psw only once
    for index,RunNumber in enumerate(RunNumberList):
        DQM_FileName = "DQM_V0001_GEM_R000"+str(RunNumber)+".root"
        Run2DesiredIeq[RunNumber] = DesiredIeqList[index]
        Run2DQM_FileName[RunNumber] = DQM_FileName
    
        RunNumber_MSDigits2 = str(RunNumber)[:2]+"xxxx"
        RunNumber_MSDigits4 = str(RunNumber)[:4]+"xx"
    
        temp_txt = open('Temp_ListOfDQMurls.txt', 'a')
        url = "https://cmsweb.cern.ch/dqm/offline/data/browse/ROOT/OnlineData/original/000"+RunNumber_MSDigits2+"/000"+RunNumber_MSDigits4+"/"+DQM_FileName+"\n"
        temp_txt.write(url)
    temp_txt.close()
    
    print "\n## Fetching DQM file ..."
    username = os.getenv("USER")
    cert_path = "/afs/cern.ch/user/"+username[0]+"/"+username+"/.globus/"
    cmd = "wget --ca-cert="+cert_path+"/usercert.p12 --certificate="+cert_path+"/usercert.pem --private-key="+cert_path+"/userkey.pem  -i Temp_ListOfDQMurls.txt"
    print cmd
    os.system(cmd)
    os.system("rm Temp_ListOfDQMurls.txt")
    ## End of fetching multiple DQM.root
    
    
    
    ## Produce output file for all Runs
    for RunNumber in RunNumberList:
        desiredIeq = Run2DesiredIeq[RunNumber]
        DQM_FileName = Run2DQM_FileName[RunNumber]
        
        try:
            DQMFile = ROOT.TFile.Open(DQM_FileName,"READ")
        except:
            print ("ERROR:\n\tCan't open the input\n\t"+DQM_FileName+"\n\twith ROOT\nEXITING...\n")
            sys.exit(0)
            
    
        ## Step 1: Acquiring N_LumiSection and RunStart in Europe TimeZone and UTC
        s = DQMFile.Get("DQMData/Run "+str(RunNumber)+"/GEM/Run summary/EventInfo")
        TList = s.GetListOfKeys()
        for item in TList:
            if  "iEvent" in item.GetName():
                N_Event = int(re.sub("[^0-9]", "", item.GetName())) ## removes all non digis chars
            if "iLumiSection" in item.GetName():
                N_LumiSection = int(re.sub("[^0-9]", "", item.GetName())) ## removes all non digis chars
            if "runStartTimeStamp" in item.GetName():
                RunStart_TimeStamp_CET = float(re.sub("[^0-9,.]", "", item.GetName())) ## removes all non digis chars but comma
                RunStart_Datetime_CET = datetime.datetime.fromtimestamp(RunStart_TimeStamp_CET).strftime('%Y-%m-%d_%H:%M:%S')
    
        RunStop_TimeStamp_CET = RunStart_TimeStamp_CET + N_LumiSection*SECONDS_PER_LUMISECTION
        RunStop_Datetime_CET = datetime.datetime.fromtimestamp(RunStop_TimeStamp_CET).strftime('%Y-%m-%d_%H:%M:%S')
    
        RunStart_Datetime_UTC,RunStart_TimeStamp_UTC = BerlinTime_2_UTC(RunStart_Datetime_CET)
        RunStop_Datetime_UTC,RunStop_TimeStamp_UTC = BerlinTime_2_UTC(RunStop_Datetime_CET)
        # deleting DQM_File
        os.system("rm "+DQM_FileName)
    
        ## End of Step 1
    
    
        ## Step 2: Fetching DCS.root
        # Using a 36h window centered on the run to avoid DCS channels without HV points
        DayBefore_RunStart_TimeStamp_UTC = RunStart_TimeStamp_UTC - 18*3600
        DayAfter_RunStop_TimeStamp_UTC = RunStop_TimeStamp_UTC + 18*3600
        DayBefore_RunStart_Datetime_UTC = datetime.datetime.fromtimestamp(DayBefore_RunStart_TimeStamp_UTC).strftime('%Y-%m-%d_%H:%M:%S')
        DayAfter_RunStop_Datetime_UTC = datetime.datetime.fromtimestamp(DayAfter_RunStop_TimeStamp_UTC).strftime('%Y-%m-%d_%H:%M:%S')
    
        print "\n## Fetching DCS file ..."
        DCS_TOOL_folder = os.getenv("DCS_TOOL")
        cmd = "python "+DCS_TOOL_folder+"/GEMDCSP5Monitor.py "+DayBefore_RunStart_Datetime_UTC +" "+ DayAfter_RunStop_Datetime_UTC +" HV 0 all"
        print cmd
        os.system(cmd)
        DCS_dump_file = DCS_TOOL_folder+"/OutputFiles/P5_GEM_HV_monitor_UTC_start_"+DayBefore_RunStart_Datetime_UTC.replace(":", "-")+"_end_"    +DayAfter_RunStop_Datetime_UTC.replace(":", "-")+".root"
        print "\n## Fetch COMPLETE"
        ## End of Step 2
    
        ## Run Info Summary
        print "\n########################################################"
        print "\nRunNumber \t\t",RunNumber
        print "N of LumiSections \t",N_LumiSection
        print "N of Events \t\t",N_Event
        print "\nStarts on "
        print "\tDatetime Europe/Berlin\t = ",RunStart_Datetime_CET,"\tTimestamp Europe/Berlin\t = ",RunStart_TimeStamp_CET
        print "\tDatetime UTC\t\t = ",RunStart_Datetime_UTC,"\tTimestamp UTC\t\t = ",RunStart_TimeStamp_UTC
        print "\nStops on (deduced)"
        print "\tDatetime Europe/Berlin\t = ",RunStop_Datetime_CET,"\tTimestamp Europe/Berlin\t = ",RunStop_TimeStamp_CET
        print "\tDatetime UTC\t\t = ",RunStop_Datetime_UTC,"\tTimestamp UTC\t\t = ",RunStop_TimeStamp_UTC
        print "\n########################################################"
    
    
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
    
        ##Step 3: Looping over all SCs and stire LS for which Ieq != IeqDesired in the MaskDict
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
                runStart_TLine[SC_ID] = ROOT.TLine(RunStart_TimeStamp_UTC,0,RunStart_TimeStamp_UTC,750)
                runStop_TLine[SC_ID] = ROOT.TLine(RunStop_TimeStamp_UTC,0,RunStop_TimeStamp_UTC,750)
    
                ## Fetching TGraphs
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
                        try:
                            N_Points = graph.GetN()
                        except:
                            raise RuntimeError
                        
                        if N_Points < 2:
                            print graph.GetTitle()," has too few points... "
                            raise RuntimeError
                except RuntimeError:
                    print "Skipping ", SC_ID
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
                    next_Timestamp = firstTimestamp + i*granularity
    
                    evaluatedVoltages = [graph.Eval(next_Timestamp) if  next_Timestamp>= firstX[index] else firstY[index] for index,graph in  enumerate(newGraph)]
    
                    stackedVoltage = sum(evaluatedVoltages)
                    ieq = stackedVoltage/4.7
    
                    if next_Timestamp > RunStart_TimeStamp_UTC and next_Timestamp < RunStop_TimeStamp_UTC and abs(ieq - desiredIeq) >= 5:
                        LS = int(UTCtime_2_LS(next_Timestamp,RunStart_TimeStamp_UTC))
                        MaskDict[ChID_L1].append(LS)
                        MaskDict[ChID_L2].append(LS)
    
                    ieq_graph[SC_ID].SetPoint(i,next_Timestamp,ieq)
    
    
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
                if len(MaskDict[ChID_L1]) == N_LumiSection:
                    MaskDict[ChID_L1] = [-1]
                if len(MaskDict[ChID_L2]) == N_LumiSection:
                    MaskDict[ChID_L2] = [-1]
        ##End of Step 3
    
    
        ##Step 4: Store output files
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
        ##End of Step 4
