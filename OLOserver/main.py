#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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

from threading import Thread
# import eventlet, atexit, signal, os
import atexit, signal, os
import OSC, UI, sequences

# flaskBind = "10.0.0.1"
flaskBind = "OLOserver.local"
HTTPlisteningPort = 8080

def exitCleanly(*args):
    """gracefully quit every thread before SystemExit"""
    print("shutting the server down :")
    print("  exiting OSCserver thread")
    OSC.runOSCserver = False
    print("  exiting validation thread")
    OSC.runValidation = False
    print("  exiting playThread...")
    sequences.isPlaying = False
    print("  turning the lights off...")
    sequences.blackout()
    print("all good, see you around !")
    raise SystemExit

if __name__ == '__main__':
    signal.signal(signal.SIGTERM, exitCleanly) # register this exitCleanly function to be called on sigterm
    atexit.register(exitCleanly) # idem when called from within this script
    # ~ eventlet.spawn(OSCserver.listen)
    print("starting the OSC server...")
    Thread(target=OSC.listenToOSC).start()
    print("starting the validation (ACK) thread...")
    Thread(target=OSC.validateLights).start()
    print("asking lights to identify themselves ...")
    OSC.askLightsForID(1) # FIXME : DEBUG, should be at least 3
    # OSC.askLightsForID(2)
    print("turning the lights off...")
    sequences.blackout()
    print("generating UI notes ...")
    UI.generateNotes()
    # Thread(target=OSC.askLightsForID).start()
    # print("starting check disconnect thread...")
    # Thread(target=clients.checkDisconnected).start()
    print("starting up webserver on %s:%i..." %(flaskBind, HTTPlisteningPort))
    # eventlet.spawn(UI.socketio.run, UI.app, {"host":flaskBind, "port":HTTPlisteningPort})
    sequences.play()
    try: UI.socketio.run(UI.app, host=flaskBind, port=HTTPlisteningPort)  # Start the asynchronous web server (flask-socketIO)
    except KeyboardInterrupt : exitCleanly()
    
