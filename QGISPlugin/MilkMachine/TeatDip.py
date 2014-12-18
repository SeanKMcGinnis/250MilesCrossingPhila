import gpxpy
import gpxpy.gpx
import simplekml
import os, sys
import time, wave
from qgis.core import *
from qgis.gui import *

class Wave(object):
    def __init__(self, wavfilepath):
        self.wavfilepath = wavfilepath

    def wav_info(self):
        # Last Modified Time
        self.mtime = time.ctime(os.path.getmtime(self.wavfilepath))
        # File Creation Time
        self.ctime = time.ctime(os.path.getctime(self.wavfilepath))
        # Wave Object - ref: https://docs.python.org/3.4/library/wave.html
        self.w = wave.open(self.wavfilepath)
        # Frame Rate of the Wave File
        self.framerate = self.w.getframerate()
        # Number of Frames in the File
        self.frames = self.w.getnframes()
        # Estimate length of the file by dividing frames/framerate
        self.length = self.frames/self.framerate

        info_dict = {'modified time': self.mtime, 'created time': self.ctime, 'frames': self.frames, 'frame rate': self.framerate, 'file length': self.length}
        return info_dict


class mmGPX(object):
    outfile = None
    def __init__(self, filepath):
        self.filepath = filepath
        self.kml = simplekml.Kml()
        self.gpx_file = open(self.filepath)
        self.gpx = gpxpy.parse(self.gpx_file)

    def tokml(self, path=None):
        cnt = 0
        for waypoint in self.gpx.waypoints:
            wpt = self.kml.newpoint(name="Red Button", coords=[(waypoint.longitude, waypoint.latitude)],description=str(waypoint.time))
            wpt.timestamp.when = waypoint.time

        self.track_counter = 0
        pt_count = 0
        for track in self.gpx.tracks:
            self.track_counter = self.track_counter + 1
            for segment in track.segments:
                points = []
                for point in segment.points:
                    coord = (point.longitude, point.latitude)
                    pnt = self.kml.newpoint(name=str(pt_count),coords=[coord],description=str(point.time))
                    pnt.timestamp.when = point.time
                    pnt.style.iconstyle.icon.href= 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
                    points.append(coord)
                    pt_count += 1

        self.lin = self.kml.newlinestring(name="Test", description="Test", coords=points)

        if not path:
            self.kml.save(self.filepath.split(".")[0] + ".kml")
            mmGPX.outfile = self.filepath.split(".")[0] + ".kml"
        else:
            self.kml.save(path)
            mmGPX.outfile = path
    def toGeoJSON(self, path=None):
        if not path:
            self.jsonpath = self.filepath.split(".")[0]# + ".json"
            Qkml = QgsVectorLayer(mmGPX.outfile, 'importkml', "ogr")
            error = QgsVectorFileWriter.writeAsVectorFormat(Qkml, self.jsonpath, "utf-8", None, "GeoJSON")
        else:
            Qkml = QgsVectorLayer(mmGPX.outfile, 'importkml', "ogr")
            error = QgsVectorFileWriter.writeAsVectorFormat(Qkml, path, "utf-8", None, "GeoJSON")

def compass_bearing(pointA, pointB):
    """
    Calculates the bearing between two points.

    :Parameters:
    - pointA: The tuple representing the latitude/longitude for the
    first point. Latitude and longitude must be in decimal degrees
    - pointB: The tuple representing the latitude/longitude for the
    second point. Latitude and longitude must be in decimal degrees

    :Returns:
    The bearing in degrees

    :Returns Type:
    float
    """


    import math
    if (type(pointA) != tuple) or (type(pointB) != tuple):
        raise TypeError("Only tuples are supported as arguments")

    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])

    diffLong = math.radians(pointB[1] - pointA[1])

    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1)
    * math.cos(lat2) * math.cos(diffLong))

    initial_bearing = math.atan2(x, y)

    # Now we have the initial bearing but math.atan2 return values
    # from -180 to + 180 which is not what we want for a compass bearing
    # The solution is to normalize the initial bearing as shown below
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing


def mean_angle(deg):
    from cmath import rect, phase
    from math import radians, degrees
    return degrees(phase(sum(rect(1, radians(d)) for d in deg)/len(deg))) % 360

def rolling_window(array, window=(0,), asteps=None, wsteps=None, axes=None, toend=True):
    import numpy as np
    """Create a view of `array` which for every point gives the n-dimensional
    neighbourhood of size window. New dimensions are added at the end of
    `array` or after the corresponding original dimension.

    Parameters
    ----------
    array : array_like
        Array to which the rolling window is applied.
    window : int or tuple
        Either a single integer to create a window of only the last axis or a
        tuple to create it for the last len(window) axes. 0 can be used as a
        to ignore a dimension in the window.
    asteps : tuple
        Aligned at the last axis, new steps for the original array, ie. for
        creation of non-overlapping windows. (Equivalent to slicing result)
    wsteps : int or tuple (same size as window)
        steps for the added window dimensions. These can be 0 to repeat values
        along the axis.
    axes: int or tuple
        If given, must have the same size as window. In this case window is
        interpreted as the size in the dimension given by axes. IE. a window
        of (2, 1) is equivalent to window=2 and axis=-2.
    toend : bool
        If False, the new dimensions are right after the corresponding original
        dimension, instead of at the end of the array. Adding the new axes at the
        end makes it easier to get the neighborhood, however toend=False will give
        a more intuitive result if you view the whole array.

    Returns
    -------
    A view on `array` which is smaller to fit the windows and has windows added
    dimensions (0s not counting), ie. every point of `array` is an array of size
    window.

    Examples
    --------
    >>> a = np.arange(9).reshape(3,3)
    >>> rolling_window(a, (2,2))
    array([[[[0, 1],
             [3, 4]],

            [[1, 2],
             [4, 5]]],


           [[[3, 4],
             [6, 7]],

            [[4, 5],
             [7, 8]]]])

    Or to create non-overlapping windows, but only along the first dimension:
    >>> rolling_window(a, (2,0), asteps=(2,1))
    array([[[0, 3],
            [1, 4],
            [2, 5]]])

    Note that the 0 is discared, so that the output dimension is 3:
    >>> rolling_window(a, (2,0), asteps=(2,1)).shape
    (1, 3, 2)

    This is useful for example to calculate the maximum in all (overlapping)
    2x2 submatrixes:
    >>> rolling_window(a, (2,2)).max((2,3))
    array([[4, 5],
           [7, 8]])

    Or delay embedding (3D embedding with delay 2):
    >>> x = np.arange(10)
    >>> rolling_window(x, 3, wsteps=2)
    array([[0, 2, 4],
           [1, 3, 5],
           [2, 4, 6],
           [3, 5, 7],
           [4, 6, 8],
           [5, 7, 9]])
    """
    array = np.asarray(array)
    orig_shape = np.asarray(array.shape)
    window = np.atleast_1d(window).astype(int) # maybe crude to cast to int...

    if axes is not None:
        axes = np.atleast_1d(axes)
        w = np.zeros(array.ndim, dtype=int)
        for axis, size in zip(axes, window):
            w[axis] = size
        window = w

    # Check if window is legal:
    if window.ndim > 1:
        raise ValueError("`window` must be one-dimensional.")
    if np.any(window < 0):
        raise ValueError("All elements of `window` must be larger then 1.")
    if len(array.shape) < len(window):
        raise ValueError("`window` length must be less or equal `array` dimension.")

    _asteps = np.ones_like(orig_shape)
    if asteps is not None:
        asteps = np.atleast_1d(asteps)
        if asteps.ndim != 1:
            raise ValueError("`asteps` must be either a scalar or one dimensional.")
        if len(asteps) > array.ndim:
            raise ValueError("`asteps` cannot be longer then the `array` dimension.")
        # does not enforce alignment, so that steps can be same as window too.
        _asteps[-len(asteps):] = asteps

        if np.any(asteps < 1):
             raise ValueError("All elements of `asteps` must be larger then 1.")
    asteps = _asteps

    _wsteps = np.ones_like(window)
    if wsteps is not None:
        wsteps = np.atleast_1d(wsteps)
        if wsteps.shape != window.shape:
            raise ValueError("`wsteps` must have the same shape as `window`.")
        if np.any(wsteps < 0):
             raise ValueError("All elements of `wsteps` must be larger then 0.")

        _wsteps[:] = wsteps
        _wsteps[window == 0] = 1 # make sure that steps are 1 for non-existing dims.
    wsteps = _wsteps

    # Check that the window would not be larger then the original:
    if np.any(orig_shape[-len(window):] < window * wsteps):
        raise ValueError("`window` * `wsteps` larger then `array` in at least one dimension.")

    new_shape = orig_shape # just renaming...

    # For calculating the new shape 0s must act like 1s:
    _window = window.copy()
    _window[_window==0] = 1

    new_shape[-len(window):] += wsteps - _window * wsteps
    new_shape = (new_shape + asteps - 1) // asteps
    # make sure the new_shape is at least 1 in any "old" dimension (ie. steps
    # is (too) large, but we do not care.
    new_shape[new_shape < 1] = 1
    shape = new_shape

    strides = np.asarray(array.strides)
    strides *= asteps
    new_strides = array.strides[-len(window):] * wsteps

    # The full new shape and strides:
    if toend:
        new_shape = np.concatenate((shape, window))
        new_strides = np.concatenate((strides, new_strides))
    else:
        _ = np.zeros_like(shape)
        _[-len(window):] = window
        _window = _.copy()
        _[-len(window):] = new_strides
        _new_strides = _

        new_shape = np.zeros(len(shape)*2, dtype=int)
        new_strides = np.zeros(len(shape)*2, dtype=int)

        new_shape[::2] = shape
        new_strides[::2] = strides
        new_shape[1::2] = _window
        new_strides[1::2] = _new_strides

    new_strides = new_strides[new_shape != 0]
    new_shape = new_shape[new_shape != 0]

    return np.lib.stride_tricks.as_strided(array, shape=new_shape, strides=new_strides)