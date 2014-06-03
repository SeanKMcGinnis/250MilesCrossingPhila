"""
	Sample code to estimate file length in time by referencing the framerate and number of frames
	
"""

import os.path, time, wave

# Sample File to Test
sample = 'SampleData/Nagra01-0003.WAV'
# Last Modified Time
mtime = time.ctime(os.path.getmtime(sample))
# File Creation Time
ctime = time.ctime(os.path.getctime(sample))

print  "last modified: %s" % mtime
print  "created: %s" % ctime

w = wave.open(sample)
framerate = w.getframerate()
frames = w.getnframes()
length = frames/framerate

print "frames: %s" % frames
print "frame rate: %s" %framerate
print "file length: %s" %length
