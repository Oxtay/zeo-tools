'''
Created on 18 juin 2011

@author: damiendrix
'''
from ZeoRawData import BaseLink
from zeo_tools.dock import HeadbandDockController
from zeo_tools.link_recorder import ZeoLinkRecorder

def acquisition_loop(device):
	link = BaseLink.BaseLink(device)
	data_recorder = ZeoLinkRecorder()
	dock_controller = HeadbandDockController()
	dock_controller.add_delegate(data_recorder)
	link.addCallback(dock_controller.update)
	print "Undock sensor to start recording..."
	link.run()

if __name__ == "__main__":
	acquisition_loop(device="/dev/tty.usbserial-A800ctM3")
	