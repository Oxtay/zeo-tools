'''
Created on 18 juin 2011

@author: damiendrix
'''
from ZeoRawData import Parser

def default_print_recorder():
	printer = PrintRecorder()
	parser = Parser.Parser()
	parser.addEventCallback(printer.new_event)
	parser.addSliceCallback(printer.new_slice)
	return parser

class PrintRecorder(object):
	def new_slice(self, slice):
		print slice
	
	def new_event(self, timestamp, version, event):
		print timestamp, version, event
	
