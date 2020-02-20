#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  
#  Copyright 2020 Reso-nance Numérique <laurent@reso-nance.org>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
from datetime import datetime, timedelta
from threading import Thread
import numpy, time
import OSC

dampeningPerLoop = 10
dampeningPerUser = 5
mainLoopDelay = 8 # time in milliseconds at which the sequences are evaluated and played for each light
activeSequences = {} # will contain the sequences currently playing
# activeSequences = [] # will contain the sequences currently playing
# this variable will contain for each lamp :
#   the sum of the sequences playing it (accordingly damped)
#   the number of sequences using this lamp (to calculate mean)
#   the last value sent to avoid unnecessary OSC packets
lightStates = numpy.array([0]*8, dtype=[("sum", "uint16"), ("seqCount", "uint8"), ("lastSent", "uint8")])
lightTimestamps = [datetime.now()]*8

isPlaying = True # set this to False to exit the play thread

class Sequence:
    def __init__(self, ID, jsSequence):
        dtypes = [("time", "uint32"), ("ID", "uint8"), ("value", "uint8")]
        self.ID = ID
        self.events = numpy.array([(0, 0, 0)]*len(jsSequence), dtype=dtypes)
        initialTime = jsSequence[0][0] # time at which the first event started
        for i in range(len(jsSequence)) : # converting the jsSequence array into a structured numpy array
            self.events[i]["time"] = jsSequence[i][0] - initialTime # first event = zero delay
            self.events[i]["ID"] = jsSequence[i][1] # number of the lamp
            self.events[i]["value"] = jsSequence[i][2] # could be 0 or 100 (bools are stored as uint8 in numpy)
        self.usedLights = numpy.unique(self.events["ID"])
        self.dampen = 0
        self.nextPassDampening = dampeningPerLoop
        self.isPlaying = False
        self.timeStarted = datetime.now()
        self.eventIndex = 0

    def playByLight(self, ID, startTime, stopTime):
        assert ID in self.usedLights
        # for event in [e for e in self.events if e["ID"] == ID] :
        event = self.events[self.eventIndex]
        eventTime = self.timeStarted + timedelta(milliseconds=int(event["time"])) 
        if eventTime > startTime and eventTime < stopTime :
            if self.eventIndex < len(self.events)-1 :
                self.eventIndex += 1
            else : # we have reached the end of the sequence, time to start over again
                self.eventIndex = 0
                self.timeStarted = datetime.now()
                self.dampen += self.nextPassDampening
            if event["value"] == 100 : return event["value"] - self.dampen
            else : return 0
        else : # no event played during this time, we must return the value of the previous event
            if self.eventIndex > 0 : return self.events[self.eventIndex-1]["value"] - self.dampen
            else : return self.events[-1] ["value"] - self.dampen -self.nextPassDampening # which will be the first one if we are at the last event

def addNew(ID, jsSequence):
    global activeSequences
    # activeSequences.append(Sequence(jsSequence))
    activeSequences.update({ID:Sequence(ID, jsSequence)})

def playSequencesForLight(ID):
    # print("evaluating sequences for light :", ID)
    global lightTimestamps, lightStates
    startTime = lightTimestamps[ID] # last time we checked this lamp
    stopTime = datetime.now()
    lightTimestamps[ID] = stopTime
    lightStates[ID]["sum"] = 0
    lightStates[ID]["seqCount"] = 0
    for sequence in [s for s in activeSequences.values() if ID in s.usedLights]:
        # if sequence.dampen >= 100 : activeSequences.remove(sequence)
        if sequence.dampen >= 100 : activeSequences.pop(sequence.ID)
        value = sequence.playByLight(ID, startTime, stopTime)
        value = sequence.playByLight(ID, startTime, stopTime)
        lightStates[ID]["seqCount"] += 1
        if value > 0 : lightStates[ID]["sum"] += value
    if lightStates[ID]["seqCount"] < 1 : return
    lightValue = int(lightStates[ID]["sum"] / lightStates[ID]["seqCount"])
    if lightValue != lightStates[ID]["lastSent"] : 
        lightStates[ID]["lastSent"] = lightValue
        OSC.sendValueToLight(lightValue, ID)
        # FIXME : should send an OSC message here
    for sequence in activeSequences.values() : sequence.nextPassDampening = lightStates[ID]["seqCount"]*dampeningPerUser + dampeningPerLoop
    # print(lightStates)
        
def playThread():
    global isPlaying
    nextLightTimer = datetime.now()
    currentLight = 0
    isPlaying = True
    print("starting to play sequences...")
    while isPlaying :
        while datetime.now() < nextLightTimer : time.sleep(0.0005)
        nextLightTimer += timedelta(milliseconds=mainLoopDelay/8)
        if activeSequences : playSequencesForLight(currentLight)
        currentLight = currentLight+1 if currentLight<7 else 0

def play() :
    Thread(target=playThread).start()

