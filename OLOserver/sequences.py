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
    """
    a sequence contains :
    - ID a unique ID (random int)
    - events : a numpy array containing tuples of 3 : (time_ms, lampID, value)
    - usedLights : a list of int containing the IDs of every lamp used in the sequence
    - dampen : an int that will be substracted from the lamps values
    - nextPassDampening : the increment of dampen per loop
    - eventIndex : index of the last event played (int)
    """

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
        # print("new sequence ", self.ID)
        # print("events :\n", self.events)
        # print("used lights :", self.usedLights)

    def playByLight(self, ID, startTime, stopTime):
        """
        returns the value of one lamp at a given time period (of the last event occured within this period)
        - ID : (int) lamp identifier
        - startTime (datetime object) : start of the period of interest
        - stopTime (datetime object) : enc of the period of interest
        """
        assert ID in self.usedLights
        # for event in [e for e in self.events if e["ID"] == ID] :
        event = self.events[self.eventIndex]
        if event["ID"] != ID : return # last event doesn't concern this lights
        eventTime = self.timeStarted + timedelta(milliseconds=int(event["time"])) 
        if eventTime > startTime and eventTime < stopTime : # the last event is in the period of interest
            if self.eventIndex < len(self.events)-1 :
                self.eventIndex += 1
            else : # we have reached the end of the sequence, time to start over again
                self.eventIndex = 0
                self.timeStarted = datetime.now()
                self.dampen += self.nextPassDampening # update the dampening
            if event["value"] == 100 : return event["value"] - self.dampen
            else : return 0
        else : # no event played during this time, we must return the value of the previous event
            if self.eventIndex > 0 : return self.events[self.eventIndex-1]["value"] - self.dampen
            else : return self.events[-1] ["value"] - self.dampen -self.nextPassDampening # which will be the first one if we are at the last event

    def remove(self):
        """ removes the sequence from activeSequences and turn off every light used"""
        global activeSequences
        for light in self.usedLights :
            OSC.setLight(light, 0) # set every used light to OFF
        activeSequences.pop(self.ID)

def addNew(ID, jsSequence):
    """
    append a sequence containing the events described as a list of tuple (time_ms, lampID, value)
    to the activeSequences dictionnary {seqID:seqObject} \n
     - ID is the unique identifier of this sequence (int), randomly generated on the UI
     - jsSequence is the list of tuple sent by the UI
     """
    global activeSequences
    activeSequences.update({ID:Sequence(ID, jsSequence)})

def playSequencesForLight(ID):
    """
    calculate the mean value for this lamp by averaging every sequence using it in this time interval.
    - ID is an int 0-7
    """
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
        if value is not None:
            lightStates[ID]["seqCount"] += 1
            if value > 0 : lightStates[ID]["sum"] += value
    if lightStates[ID]["seqCount"] < 1 : return
    lightValue = int(lightStates[ID]["sum"] / lightStates[ID]["seqCount"])
    if lightValue != lightStates[ID]["lastSent"] : 
        lightStates[ID]["lastSent"] = lightValue
        OSC.setLight(ID,lightValue)
        # print("setting light %i to %i "%(ID, lightValue), "lightStates[%i] :"%ID, lightStates[ID])
    for sequence in activeSequences.values() :
        sequence.nextPassDampening = lightStates[ID]["seqCount"] * dampeningPerUser + dampeningPerLoop
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
    """plays every sequence in activeSequence lamp by lamp while isPlaying is True"""
    Thread(target=playThread).start()

def blackoutThread():
    print("  blacking out...")
    for i in range(8):
        OSC.setLight(i,0)
        time.sleep(.1)

def blackout() :
    Thread(target=blackoutThread).start()