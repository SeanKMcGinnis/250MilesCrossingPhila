import numpy as np
import pyKML
from os import path

"""
        A Class to pass arrays into to filter
"""
class track_filter:
    def __init__(self):
        print "Starting filter application"
        self.kmlpath = 'C:/Users/Sean/Documents/GitHub/250MilesCrossingPhila/Python/SampleData/140519-2Dorienlog12.kml'

    def moving_average(a, n=3):
        print "Rolling Average\n"
        ret = np.cumsum(a, dtype=float)
        ret[n:] = ret[n:] - ret[:-n]
        return ret[n - 1:]

    def average(kml_path):
        print 'Moving average'
        doc = pyKML.parser.parse(kml_path)
        
    filter_options = {
        'average' : average,
    }
