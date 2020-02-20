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

class Sequence:
    def __init__(self, events):
        dtypes = [("time", "float32"), ("ID", "uint8"), ("value", "uint8")]
        self.events = numpy.array(events, dtype=dtypes)
        self.isPlaying = False
        self.timeStarted = datetime.now()

    def start(self):
        self.timeStarted = datetime.now()
        self.isPlaying = True
    
    def play(self):
        if self.timeStarted + timedelta(seconds = self.events[0]["time"]) >= datetime.now():
            ID, value = self.events[0]["ID"], self.events[0]["value"]
            self.events = numpy.delete(self.events, 0)
            return ID, value
        else : return None
