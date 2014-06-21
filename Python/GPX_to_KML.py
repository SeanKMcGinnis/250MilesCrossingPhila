import gpxpy
import gpxpy.gpx
import simplekml

kml = simplekml.Kml()

gpx_file = open('SampleData/140606.gpx')
gpx = gpxpy.parse(gpx_file)

for waypoint in gpx.waypoints:
	#print 'waypoint {0} -> ({1},{2})'.format(waypoint.name, , )
	#kml.newpoint(name="Red Button", coords=[(waypoint.latitude, waypoint.longitude)])
	kml.newpoint(name="Red Button", coords=[(waypoint.longitude, waypoint.latitude)])

track_counter = 0
for track in gpx.tracks:
	track_counter = track_counter + 1
	print 'Track #%s' % str(track_counter)
	for segment in track.segments:
		points = []
		for point in segment.points:
			coord = (point.longitude, point.latitude)
			pnt = kml.newpoint(coords=[coord])
			pnt.style.iconstyle.icon.href= 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
			points.append(coord)
			#print 'Point at ({0},{1}) -> {2}'.format(point.latitude, point.longitude, point.elevation)

lin = kml.newlinestring(name="Test", description="Test", coords=points)
kml.save("test.kml")