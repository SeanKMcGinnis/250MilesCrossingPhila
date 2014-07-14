"""
	Sample code to estimate file length in time by referencing the framerate and number of frames

"""

import os.path, time, wave

# Sample File to Test
sample = 'C:/Users/Edward/Documents/Philly250/Scratch/NAG10038.wav'
# Last Modified Time
mtime = time.ctime(os.path.getmtime(sample))
# File Creation Time
ctime = time.ctime(os.path.getctime(sample))
# Wave Object - ref: https://docs.python.org/3.4/library/wave.html
w = wave.open(sample)
# Frame Rate of the Wave File
framerate = w.getframerate()
# Number of Frames in the File
frames = w.getnframes()
# Estimate length of the file by dividing frames/framerate
length = frames/framerate

# Display the information
print  "last modified: %s" % mtime
print  "created: %s" % ctime
print "frames: %s" % frames
print "frame rate: %s" %framerate
print "estimated file length: %s" %length
