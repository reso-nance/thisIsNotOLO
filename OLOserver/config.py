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


""" ------- lights -------"""
activeWindows = [0, 1, 2, 4, 5, 6, 7, 8, 10, 11] # IDs from 0 to 11 corresponding to the currently available lights

"""------- sequences -----"""
dampeningPerLoop = 10 # percents to substract from the light value at each loop
dampeningPerUser = 5 # value in percent that will be multiplied by the number of sequences using this light then substracted from the light value
mainLoopDelay = 8 # time in milliseconds at which the sequences are evaluated and played for each light

"""---- web interface ----"""
notes = ["C", "D", "E", "G", "A"] # list of notes that will be played on the UI
startOctave = 3 # lowest octave to be played
playNotesOnUI = True # play sounds corresponding to lights on the UI when sequences are played
sequenceMaxLength = 30000 # max duration of a sequence (in milliseconds)

"""--- wifi management ---"""
validationTime = .2 # time in s after which a light value will be sent again if no ACK has been received
maxRetryPerMessage = 3 # max retry without receiving the correponding ACK for a given message