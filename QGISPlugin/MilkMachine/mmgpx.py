import gpxpy
import gpxpy.gpx
import simplekml
import os, sys

class mmGPX(gpxfilepath):
    filepath = gpxfilepath
    def __init__(self):
        self.kml = simplekml.Kml()
        self.gpx_file = open(mmGPX.filepath)
        self.gpx = gpxpy.parse(self.gpx_file)

    def tokml(self, path=None):
        for waypoint in self.gpx.waypoints:
        	#print 'waypoint {0} -> ({1},{2})'.format(waypoint.name, , )
        	#kml.newpoint(name="Red Button", coords=[(waypoint.latitude, waypoint.longitude)])
        	self.kml.newpoint(name="Red Button", coords=[(waypoint.longitude, waypoint.latitude)])

        self.track_counter = 0
        for track in self.gpx.tracks:
        	self.track_counter = self.track_counter + 1
        	for segment in track.segments:
        		points = []
        		for point in segment.points:
        			coord = (point.longitude, point.latitude)
        			pnt = self.kml.newpoint(coords=[coord])
        			pnt.style.iconstyle.icon.href= 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
        			points.append(coord)
        			#print 'Point at ({0},{1}) -> {2}'.format(point.latitude, point.longitude, point.elevation)

        self.lin = self.kml.newlinestring(name="Test", description="Test", coords=points)

        if not path:
            self.kml.save(mmGPX.filepath.split(".")[0] + ".kml")
        else:
            self.kml.save(path)


