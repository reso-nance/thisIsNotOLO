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

# activeWindows = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
lightCount = 8 # number of lights that will be connected
dampeningPerLoop = 10 # percents to substract from the light value at each loop
dampeningPerUser = 5 # value in percent that will be multiplied by the number of sequences using this light then substracted from the light value
mainLoopDelay = 8 # time in milliseconds at which the sequences are evaluated and played for each light
notes = ["C", "D", "E", "G", "A"] # list of notes that will be played on the UI
startOctave = 3 # lowest octave to be played
# lightCount = len(activeWindows) # number of lights that will be connected

