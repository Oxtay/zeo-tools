'''
Created on 20 juin 2011

@author: damiendrix
'''
from ZeoRawData.Utility import dataTypes, getInt16
import wave
import numpy as np

class WaveformToWAV(object):
	"""
	A BaseLink callback that records the waveform data to a WAV file.
	No filter is applied to remove mains hum, the raw waveform is recorded.
	"""
	def __init__(self):
		self.data = []
	
	def update(self, timestamp, timestamp_subsec, version, data):
		datatype = dataTypes[ord(data[0])]
		if datatype == 'Waveform':
			waveform = [getInt16(data[i:i+2]) for i in range(1,256,2)]
			self.data.append(waveform)
	
	def write(self, dest_filename, speedup=1):
		"""
		Writes the recorded data to the destination file.
		speedup -- controls the framerate (128Hz for speedup=1).
		           A speedup of about 200 makes the timeseries audible.
		"""
		data = np.array(self.data, dtype=np.int16).flatten().data
		wf = wave.open(dest_filename, 'wb')
		try:
			wf.setnchannels(1)
			wf.setsampwidth(2)
			wf.setframerate(128*speedup)
			wf.writeframes(data)
		finally:
			wf.close()
		print "WAV file written to %s" % dest_filename
		self.data = []

def record_to_wav(record_filename, wav_filename, speedup=1, **replay_kwargs):
	from zeo_tools.link_recorder import ZeoLinkReplay
	# Prepare to replay this file:
	replay = ZeoLinkReplay(record_filename)
	
	# Extract waveform data to a WAV file
	wav_converter = WaveformToWAV()
	replay.addCallback(wav_converter.update)
	
	# Go!
	print "replaying..."
	replay.run(speed="max", **replay_kwargs)
	print "done."
	
	# Cleanup
	wav_converter.write(wav_filename, speedup=speedup)
	del replay
	

if __name__ == "__main__":
	record_to_wav("zeodata_2011-06-19T23:35:24.h5", "waveform.wav")
