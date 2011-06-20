'''
Created on 19 juin 2011

@author: damiendrix
'''
import tables
from tables import IsDescription, UInt8Col, Float32Col, UInt32Col, Filters, VLStringAtom
import os.path
import time
import itertools

class TimestampedZeoDesc(IsDescription):
	timestamp = UInt32Col()
	timestamp_subsec =Float32Col()
	version = UInt8Col()

class ZeoLinkRecorder(object):
	"""
	Records a Zeo Raw Data Link stream (decoded by a ZeoRawData.BaseLink instance) to an HDF5 file.
	The resulting file can be replayed with the ZeoLinkReplay class or used for offline analysis.
	To start recording when the user undocks the headband, use the HeadbandDockController class.
	At maximum compression levels, one hour of data takes about 1.5MB of disk space.
	
	Basic usage:
	>>> recorder = ZeoLinkRecorder()
	>>> recorder.start("destination.hdf5")
	>>> link = BaseLink(device)
	>>> link.addCallback(recorder.update)
	>>> link.run()
	>>> ...
	>>> recorder.stop()
	"""
	
	expected_hours = 8.0
	
	def __init__(self, base_dir=".", compression_level=9, checksum=True):
		"""
		Creates a Zeo Raw Data Link recorder.
		base_dir -- default directory for storing recordings.
		compression_level -- an int: 0 disables compression, 9 is the maximum level
		checksum -- set to true to enable checksums on recorded data.
		"""
		self.base_dir = base_dir
		self.compression_level = compression_level
		self.checksum = checksum
		self.h5file = None
		
	def start(self, filename=None):
		"""
		Starts recording incomming events to a file.
		If no filename is given, a new timestamped file is created
		in the directory that was specified to the constructor.
		"""
		if filename is None:
			datestring = time.strftime("%Y-%m-%dT%H:%M:%S")
			filename = os.path.abspath(os.path.join(self.base_dir, "zeodata_%s.h5" % datestring))
		
		filters = Filters(complevel=self.compression_level, fletcher32=self.checksum)
		h5file = tables.openFile(filename, mode = "w", filters=filters)
		group = h5file.createGroup("/", "zeolinkdata", "Zeo Raw Data Link Recording")
		self.replay_data = h5file.createVLArray(group, 'data', VLStringAtom(), "Link Replay Data",
									expectedsizeinMB=(self.expected_hours*3600*300)/(1024.0**2))
		self.replay_metadata = h5file.createTable(group, 'metadata', TimestampedZeoDesc, "Link Replay Metadata",
									expectedrows=self.expected_hours*3600*5)
		self.h5file = h5file
		print "Recording to %s started." % filename
	
	def stop(self):
		""" Ends the recording and closes the target file. """
		if self.h5file:
			self.replay_data.flush()
			self.replay_metadata.flush()
			print
			print "Recording complete."
			print "%d seconds of data were recorded." % (self.replay_metadata[-1]['timestamp'] - self.replay_metadata[0]['timestamp'])
			self.h5file.close()
			del self.replay_data
			del self.replay_metadata
			self.h5file = None
	
	def update(self, timestamp, timestamp_subsec, version, data):
		"""
		Update the current Slice with new data from Zeo.
		This function is setup to be easily added to the 
		BaseLink's callbacks.
		"""
		if not self.h5file: return
		replay_metadata = self.replay_metadata.row
		replay_metadata['timestamp'] = timestamp
		replay_metadata['timestamp_subsec'] = timestamp_subsec
		replay_metadata['version'] = version
		replay_metadata.append()
		self.replay_data.append(data)

class ZeoLinkReplay(object):
	"""
	A BaseLink drop-in replacement that plays back previously recorded data.
	No active connection to the Zeo device is necessary during replay.
	"""
	def __init__(self, file):
		if hasattr(file, 'root'):
			h5file = file
		else:
			self.h5file = h5file = tables.openFile(file, mode = "r")
		
		self.replay_data = h5file.root.zeolinkdata.data
		self.replay_metadata = h5file.root.zeolinkdata.metadata
		self.callbacks = []
		
	def __del__(self):
		if self.h5file:
			self.h5file.close()

	def addCallback(self, callback):
		"""Add a function to call when an Event has occured."""
		self.callbacks.append(callback)
	
	def run(self, speed=1.0, start=None, stop=None):
		"""
		Replays the data to the registered callbacks.
		speed -- sets the replay speed as a multiple of real-time.
		         To replay recordings at twice real-time, use speed=2.0.
		         To replay at maximum speed, use speed='max'.
		start, stop -- optional timestamps defining the interval to replay.
		"""
		record_start = self.replay_metadata[0]['timestamp']
		record_end = self.replay_metadata[-1]['timestamp']

		if start is None and stop is None:
			event_iterator = itertools.izip(self.replay_data, self.replay_metadata)
		else:
			query = []
			if start is not None:
				query.append('(timestamp >= %d)' % start)
				record_start = start
			if stop is not None:
				query.append('(timestamp < %d)' % stop)
				record_end = stop
			metadata_rows = self.replay_metadata.where('&'.join(query))
			event_iterator = ((self.replay_data[row.nrow], row) for row in metadata_rows)
		
		if speed in ("max", float('inf')):
			# Push the data to the callbacks as fast as it can be read
			i = 0
			for event_data, event_metadata in event_iterator:
				self._replay(event_data, event_metadata)
				if i % 1000 == 0:
					print int(100 * (event_metadata['timestamp'] - record_start) / (record_end - record_start)), "%"
				i += 1
		else:
			# Replay the event timeline
			replay_start = time.time()
			def record_time(): return record_start + (time.time() - replay_start) * speed
			def replay_sleep(delay): time.sleep(delay/float(speed))
			for event_data, event_metadata in event_iterator:
				now = record_time()
				delay = event_metadata['timestamp'] - int(now) + event_metadata['timestamp_subsec'] - (now - int(now))
				if delay > 0: replay_sleep(delay)
				self._replay(event_data, event_metadata)

	def _replay(self, event_data, event_metadata):
		for c in self.callbacks:
			c(event_metadata['timestamp'], event_metadata['timestamp_subsec'], event_metadata['version'], event_data)
		
if __name__ == "__main__":
	from zeo_tools.converters.audio import WaveformToWAV
	
	# Prepare to replay this file:
	fname = "zeodata_2011-06-19T23:35:24.h5"
	replay = ZeoLinkReplay(fname)
	
	# Make another copy using the ZeoLinkRecorder again
	copy = ZeoLinkRecorder()
	replay.addCallback(copy.update)
	copy.start()
	
	# Also extract waveform data to a WAV file
	wav_converter = WaveformToWAV()
	replay.addCallback(wav_converter.update)
	
	# Go!
	print "replaying..."
	replay.run(speed='max')
	print "done."
	
	# Cleanup
	copy.stop()
	wav_converter.write("waveform2.wav", speedup=200)
	del replay
	