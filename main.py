#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  
#  Copyright 2019 Reso-nance Numérique <laurent@reso-nance.org>
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
import liblo, time
from threading import Thread

knownDevices = {}
OSCsendPort = 8000
OSClistenPort = 9000
runOSCserver = True

class Light:
    def __init__(self, hostname, ip):
        self.hostname = hostname
        self.ip = ip
        self.ack = 0

def unknownOSC(address, args, tags, IPaddress):
    print("got unknown message '%s' from '%s'" % (address, IPaddress.url))
    for a, t in zip(args, tags):
        print ("  argument of type '%s': %s" % (t, a))

def handleAck(address, args, tags, IPaddress):
    global knownDevices
    hostname, value = args
    if hostname in knownDevices : knownDevices[hostname].ack = value
    else : 
        print("WARNING : received ACK from unknown device %s at %s" %(hostname, IPaddress.url))

def handleID(address, args, tags, IPaddress):
    global knownDevices
    ip = IPaddress.url.split("//")[1].split(":")[0] # retrieve IP from an url like osc.udp://10.0.0.12:35147/
    hostname = str(args[0])
    if hostname not in knownDevices : print("added new device "+hostname)
    else : print("updated device "+hostname)
    knownDevices.update({hostname:Light(hostname, ip)})

def setLight(hostname, value):
    value = int(value)
    if hostname in knownDevices :
        liblo.send((knownDevices[hostname].ip, OSCsendPort), "/"+hostname+"/light", value)
    else : print("ERROR : cannot set light value on unknown device "+hostname)

# TODO : implement a logarithmic fade
def fadeLight(hostname, fadeFrom, fadeTo, duration) :
    stepsCount = max(fadeFrom, fadeTo) - min(fadeFrom, fadeTo) +1
    delay = duration/stepsCount
    delay /= 2 # why ??? it does works but why ??
    currentValue = fadeFrom
    for steps in range(stepsCount):
        setLight(hostname, currentValue)
        time.sleep(delay)
        currentValue = currentValue+1 if fadeFrom<fadeTo else currentValue-1

def broadcastOSC(OSCaddress, OSCport, OSCargs=None):
    """
    since sending OSC to broadcast addresses is forbidden for non-root users,
    this function sends OSC to every ip addresses from 1 to 254 manually
    """
    for i in range(1,255):
        ip = "10.0.0."+str(i)
        if OSCargs : liblo.send((ip, OSCport), OSCaddress, *OSCargs)
        else : liblo.send((ip, OSCport), OSCaddress)

def listenToOSC():
    try:
        server = liblo.Server(OSClistenPort)
        print("listening to incoming OSC on port %i" % OSClistenPort)
    except liblo.ServerError as e:
        print(e)
        raise SystemError

    server.add_method("/ACK", None, handleAck)
    server.add_method("/myID", None, handleID)
    server.add_method(None, None, unknownOSC)
    
    while runOSCserver : 
        server.recv(50)
    print("  OSC server has closed")

if __name__ == '__main__':

    print("OSC server starting...")
    oscServerThread = Thread(target=listenToOSC)
    oscServerThread.start()

    print("broadcasting /whoIsThere")
    broadcastOSC("/whoIsThere", OSCsendPort)
    time.sleep(1) # gives ESPs time to respond

    if "light_84F3EB583BDB" in knownDevices :
        print("fading light")
        fadeLight("light_84F3EB583BDB", 0, 1024, 10)

    try : 
        while True : time.sleep(.1)
    except KeyboardInterrupt :
        runOSCserver = False