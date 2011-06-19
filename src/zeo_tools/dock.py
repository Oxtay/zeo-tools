'''
Created on 19 juin 2011

@author: damiendrix
'''

from ZeoRawData.Utility import dataTypes, eventTypes, getUInt32

class HeadbandDockController(object):
	"""
	Helper to trigger processing when the user picks up the headband from the dock.
	Events are passed through to each delegate's update() method while the headband is undocked,
	and blocked otherwise. Additionally, if a delegate has start() and stop() methods, these will be called
	when undocking and docking the headband, respectively.
	"""
	def __init__(self):
		self.delegates = []
		self.active = False
	
	def add_delegate(self, delegate):
		self.delegates.append(delegate)
		
	def remove_delegate(self, delegate):
		self.delegates.remove(delegate)
	
	def update(self, timestamp, timestamp_subsec, version, data):
		""" BaseLink callback """
		datatype = dataTypes[ord(data[0])]
		
		# Detect headband undocking and docking to start and stop recording
		kind = None
		if datatype == 'Event': kind = eventTypes[getUInt32(data[1:5])]
		
		if kind == "HeadbandUnDocked":
			for d in self.delegates:
				if hasattr(d, "start"): d.start()
			self.active = True
			
		# Pass the new data through to the recorder
		if self.active:
			for d in self.delegates: d.update(timestamp, timestamp_subsec, version, data)

		if kind == "HeadbandDocked":
			for d in self.delegates:
				if hasattr(d, "stop"): d.stop()
			self.active = False
		
	