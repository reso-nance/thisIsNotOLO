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

from flask import Flask, g, render_template, redirect, request
from flask_socketio import SocketIO, emit
# ~ import os, logging, subprocess, eventlet
import os, logging, subprocess, urllib.parse, json
import sequences
# ~ eventlet.monkey_patch() # needed to make eventlet work asynchronously with socketIO, 

mainTitle = "OLO"

if __name__ == '__main__':
    raise SystemExit("this file is made to be imported as a module, not executed")

# Initialize Flask and flask-socketIO
app = Flask(__name__) 
app.url_map.strict_slashes = False # don't terminate each url by / ( can mess with href='/#' )
# ~ socketio = SocketIO(app, async_mode="eventlet")
socketio = SocketIO(app, async_mode="threading", ping_timeout=36000)# set the timeout to ten hours, defaut is 60s and frequently disconnects
# disable flask debug (except errors)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --------------- FLASK ROUTES ----------------

@app.route('/')
def rte_homePage():
    general_Data = {'title':mainTitle}
    return render_template('index.html', **general_Data)

# --------------- SOCKET IO EVENTS ----------------

@socketio.on('connect', namespace='/home')
def onConnect():
    print("client connected, session id : "+request.sid)

@socketio.on('disconnect', namespace='/home')
def onDisconnect():
    print("client disconnected")

@socketio.on('newSequence', namespace='/home')
def receivedNewSequence(sequenceID, jsSequence):
    print("new sequence received")
    sequences.addNew(sequenceID, jsSequence)

@socketio.on('removeSequence', namespace='/home')
def removeSequence(sequenceID):
    print("removing sequence", sequenceID)
    sequences.activeSequences.pop(sequenceID)

@socketio.on('clearAllSequences', namespace='/home')
def clearAllSequences():
    print("clearing all sequences")
    sequences.activeSequences = {}
    
# --------------- FUNCTIONS ----------------
