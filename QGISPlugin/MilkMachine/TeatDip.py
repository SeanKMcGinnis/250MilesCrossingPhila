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

class Shape:
    def __init__(self, ActiveLayer):
        self.activelayer = ActiveLayer
