#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
import liblo, time, sys
from threading import Thread, Timer
import config, UI

knownLights = {}
OSCsendPort = 8000
OSClistenPort = 9000
runOSCserver, runValidation = True, True
lightAdresses = ["light"+str(i)+".local" for i in config.activeWindows]

class Light:
    def __init__(self, hostname, ip):
        self.hostname = hostname
        self.ip = ip
        self.ack = 0 # value of the last ACK received
        self.value = 0 # current light value
        self.validationTime = time.time()*1000 # when last ACK has been received
        self.validated = False # ACK value == value
        self.retriesLeft = config.maxRetryPerMessage # number of retries allowed for this light
        self.resetRetry = None # time at which the validation will expire

    def setLight(self, value):
        """ send the /light OSC message to this light and prepare for it's validation"""
        self.value = max(0, min(int(value), 100))
        liblo.send((self.ip, OSCsendPort), "/"+self.hostname+"/light", self.value)
        self.validationTime = time.time()
        self.validated = False

    def startFade(self, start, end, duration):
        """ send the /fade OSC message to this light and prepare for it's validation"""
        constrain = lambda x : max(0, min(int(x), 100))
        start, end = constrain(start), constrain(end)
        self.value = [start, end, duration]
        if start == end : 
            print("ERROR unable to send fade : same start and end")
            return
        print("starting fade on ", self.hostname, " : start ", start, "end", end, "duration", duration)
        liblo.send((self.ip, OSCsendPort), "/"+self.hostname+"/fade", start, end, duration)
        self.validationTime = time.time()
        self.validated = False
    
    def validate(self):
        """ evaluate if the last received ACK correspond to the last value asked"""
        currentTime = time.time()
        if not self.validated and currentTime - self.validationTime > config.validationTime :
            if self.ack == self.value : # FIXME : this value may very well be from another (later) message
                self.validated = True
                self.retriesLeft = config.maxRetryPerMessage
                # print("validated :", self.value)
            elif self.retriesLeft > 0:
                if isinstance(self.value, int) : self.setLight(self.value)
                elif isinstance(self.value, list) :
                    # print("trying to validate a fade :", self.value)
                    self.startFade(*self.value)
                print("sending last value again for", self.hostname)
                self.retriesLeft -= 1


def unknownOSC(address, args, tags, IPaddress):
    """callback on reception of a malformed/unknown OSC message"""
    print("got unknown message '%s' from '%s'" % (address, IPaddress.url))
    for a, t in zip(args, tags):
        print ("  argument of type '%s': %s" % (t, a))

def handleAck(address, args, tags, IPaddress):
    """
    callback when an "/ACK" or "/fadeACK" OSC msg is received. Arguments contain the value acknowledged
    """
    global knownLights
    if address == "/ACK" : hostname, value = args
    if address == "/fadeACK" :
        hostname = args[0]
        value = args[1:]
    # print("got ACK for %s : %i"%(hostname, value))
    if hostname in knownLights : knownLights[hostname].ack = value
    else : 
        print("WARNING : received ACK from unknown device %s at %s" %(hostname, IPaddress.url))
        handleID(address, args, tags, IPaddress)

def handleID(address, args, tags, IPaddress):
    """
    callback when an "/myID" OSC msg is recieved. The arguments received should be the hostname of this light.
    The IP is directly read from the packet itself
    """
    global knownLights
    ip = IPaddress.url.split("//")[1].split(":")[0] # retrieve IP from an url like osc.udp://10.0.0.12:35147/
    hostname = str(args[0])
    if hostname not in knownLights :
        print("added new device "+hostname)
    else : print("updated device "+hostname)
    knownLights.update({hostname:Light(hostname, ip)})
    print ("knownLights :", *knownLights)
    

def setLight(hostname, value):
    """
    send the "/hostname/light value" OSC message to the address corresponding to the light ID
    - hostname : can be an int 0-7 or a string with the complete hostname ("light0")
    - value : int 0 (off) - 100 (full power)
    """
    value = int(value)
    if isinstance(hostname, int) : 
        if config.playNotesOnUI : UI.playNoteOnUI(hostname, value)
        hostname = "light"+str(hostname)
    # print("setting %s to %i" %(hostname, value))
    if hostname in knownLights : knownLights[hostname].setLight(value)
    else : print("ERROR : cannot set light value on unknown device "+hostname)

def broadcastOSC(OSCaddress, OSCport, OSCargs=None):
    """
    since sending OSC to broadcast addresses is forbidden for non-root users,
    this function sends OSC to every ip addresses from 1 to 254 manually
    """
    for i in range(1,255):
        ip = "10.0.0."+str(i)
        if OSCargs : liblo.send((ip, OSCport), OSCaddress, *OSCargs)
        else : liblo.send((ip, OSCport), OSCaddress)
        time.sleep(.01)

def validateLights():
    """ run validation on every connected lights"""
    while runValidation :
        for light in knownLights.values() : light.validate()
        time.sleep(0.001)
    print("  closing the validation thread")

def listenToOSC():
    """ this function handles OSC reception. It is blocking and meant to be run as a thread. 
    The thread will exit gracefully when the runOSCserver bool is set to False"""
    try:
        server = liblo.Server(OSClistenPort)
        print("  listening to incoming OSC on port %i" % OSClistenPort)
    except liblo.ServerError as e:
        print(e)
        raise SystemError

    server.add_method("/ACK", None, handleAck)
    server.add_method("/fadeACK", None, handleAck)
    server.add_method("/myID", None, handleID)
    server.add_method(None, None, unknownOSC)
    
    while runOSCserver : 
        server.recv(50)
    print("  OSC server has closed")

def askLightsForID(iterations):
    """
    broadcast the OSC message "/whoIsThere" asking lights to identify themselves, responding with their IP and hostname
    For added safety, this message is broadcasted multiple times according to the iterations parameter
    """
    for _ in range(iterations):
        broadcastOSC("/whoIsThere", OSCsendPort)
        time.sleep(1) # gives ESPs time to respond
