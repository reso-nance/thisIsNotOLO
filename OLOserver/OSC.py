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

knownLights = {}
OSCsendPort = 8000
OSClistenPort = 9000
runOSCserver, runValidation = True, True
validationTime = .2 # time in s after which a light value will be sent again if no ACK has been received
lightAdresses = [str(i)+".local" for i in range(8)]

class Light:
    def __init__(self, hostname, ip):
        self.hostname = hostname
        self.ip = ip
        self.ack = 0
        self.value = 0
        self.validationTime = time.time()*1000
        self.validated = False

    def setLight(self, value):
        self.value = max(0, min(int(value), 100))
        liblo.send((self.ip, OSCsendPort), "/"+self.hostname+"/light", self.value)
        self.validationTime = time.time()
        self.validated = False

    def startFade(self, start, end, duration):
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
        if not self.validated and time.time() - self.validationTime > validationTime :
            if self.ack == self.value : 
                self.validated = True
                print("validated :", self.value)
            else : 
                if isinstance(self.value, int) : self.setLight(self.value)
                elif isinstance(self.value, list) :
                    print("trying to validate a fade :", self.value)
                    self.startFade(*self.value)
                print("sending again")


def unknownOSC(address, args, tags, IPaddress):
    print("got unknown message '%s' from '%s'" % (address, IPaddress.url))
    for a, t in zip(args, tags):
        print ("  argument of type '%s': %s" % (t, a))

def handleAck(address, args, tags, IPaddress):
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
    global knownLights
    ip = IPaddress.url.split("//")[1].split(":")[0] # retrieve IP from an url like osc.udp://10.0.0.12:35147/
    hostname = str(args[0])
    if hostname not in knownLights : print("added new device "+hostname)
    else : print("updated device "+hostname)
    knownLights.update({hostname:Light(hostname, ip)})

def setLight(hostname, value):
    value = int(value)
    # print("setting %s to %i" %(hostname, value))
    if hostname in knownLights : knownLights[hostname].setLight(value)
    else : print("ERROR : cannot set light value on unknown device "+hostname)

# deprecated since fades are generated on the ESP8266 directly
# def fadeLight(hostname, fadeFrom, fadeTo, duration, exp=2, delay=0.05) :
#     reverse = True if fadeFrom > fadeTo else False
#     if reverse : fadeFrom, fadeTo = fadeTo, fadeFrom
#     stepsCount = int(duration/delay)
#     values = [i**exp for i in range(0,stepsCount)]
#     mapToRange = lambda x, a, b, c, d : int((x-a)/(b-a)*(d-c)+c)
#     values = [mapToRange(x,min(values), max(values), fadeFrom, fadeTo) for x in values]
#     if reverse : values.reverse()
#     for i in range(len(values)) :
#         Timer(delay*i+1, setLight, args=[hostname, values[i]]).start()

def lightShow(hostname, fadeTime, totalTime=False):
    timeStarted = time.time()
    while runOSCserver :
        if totalTime and time.time() - timeStarted > totalTime : return
        if hostname in knownLights :
            knownLights[hostname].startFade(0, 100, fadeTime)
            time.sleep(fadeTime/1000+.1)
            knownLights[hostname].startFade(100, 0, fadeTime)
            time.sleep(fadeTime/1000+.1)

def broadcastOSC(OSCaddress, OSCport, OSCargs=None):
    """
    since sending OSC to broadcast addresses is forbidden for non-root users,
    this function sends OSC to every ip addresses from 1 to 254 manually
    """
    for i in range(1,255):
        ip = "10.0.0."+str(i)
        if OSCargs : liblo.send((ip, OSCport), OSCaddress, *OSCargs)
        else : liblo.send((ip, OSCport), OSCaddress)
        i = int(i/10)
        sys.stdout.write("\r{0}>".format("="*i))
        sys.stdout.flush()
        time.sleep(.01)
    print("done")

def sendValueToLight(value, lightID):
    value = min(100, max(value, 0))
    # FIXME debug
    liblo.send(("10.0.120.85", OSCsendPort), "/light%i/light"%lightID, value)
    print("sent /light%i/light"%lightID, value)

def validateLights():
    while runValidation :
        for light in knownLights.values() : light.validate()
        time.sleep(0.001)
    print("  closing the validation thread")

def listenToOSC():
    try:
        server = liblo.Server(OSClistenPort)
        print("listening to incoming OSC on port %i" % OSClistenPort)
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

if __name__ == '__main__':

    print("starting the OSC server thread...")
    oscServerThread = Thread(target=listenToOSC)
    oscServerThread.start()

    print("starting the validation thread...")
    validationThread = Thread(target=validateLights)
    validationThread.start()

    print("broadcasting /whoIsThere...")
    broadcastOSC("/whoIsThere", OSCsendPort)
    time.sleep(1) # gives ESPs time to respond

    if "light_3C71BF264A9B" in knownLights :
        print("starting test lightshow on light_3C71BF264A9B")
        Thread(target=lightShow, args=("light_3C71BF264A9B", 2000)).start()

    try : 
        lightShowStarted = False
        while True : 
            time.sleep(.1)
            if "light_3C71BF264A9B" in knownLights and not lightShowStarted:
                print("starting test lightshow on light_3C71BF264A9B")
                Thread(target=lightShow, args=("light_3C71BF264A9B", 2000)).start()
                lightShowStarted = True
    except KeyboardInterrupt :
        runOSCserver = False
        runValidation = False