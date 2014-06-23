import gpxpy
import gpxpy.gpx
import simplekml
## Variables to be transferred to inputs in UI script
tour_name = 'Test'
gpx = 'SampleData/140606.gpx'
flyto_duration = 2

# Create the output KML File
kml = simplekml.Kml()
# Create the tour
tour = kml.newgxtour(name=tour_name)
# Create a playlist in the tour
playlist = tour.newgxplaylist()

#get the raw GPX information
gpx_file = open(gpx)
gpx = gpxpy.parse(gpx_file)

# Let's make sure we see whenever someone hit the 'Red Button' and iterate through the waypoints
for waypoint in gpx.waypoints:
	kml.newpoint(name="Red Button", coords=[(waypoint.longitude, waypoint.latitude)])

for track in gpx.tracks:
	for segment in track.segments:
		points = []
		for point in segment.points:
			coord = (point.longitude, point.latitude)
			#print(point.time)
			pnt = kml.newpoint(coords=[coord])
			pnt.timestamp.when = point.time
			pnt.style.iconstyle.icon.href= 'http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png'
			points.append(coord)
			flyto = playlist.newgxflyto(gxduration=flyto_duration)
			

lin = kml.newlinestring(name="Test", description="Test", coords=points)
kml.save("test.kml")