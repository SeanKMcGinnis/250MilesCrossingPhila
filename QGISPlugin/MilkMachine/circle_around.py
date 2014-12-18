import simplekml, os
"""
    A Class to build a circle around view
"""
class circle_around:
    def __init__(self, lookat_x, lookat_y, fly_to_mode):
        # KML file
        self.kml = simplekml.Kml(name="Circle Around")
        # Tour
        self.tour = self.kml.newgxtour()
        # X Value
        self.x = lookat_x
        # Y Value
        self.y = lookat_y
        # Fly to Mode
        self.fly_to_mode = fly_to_mode

    def create(self, circle_count, time_seconds, view_angle, camera_tilt, camera_range):
        # Calculate the duration: (Total Time/Number of Circles)/36
        duration = (float(time_seconds)/circle_count)/36
        # Playlist
        playlist = self.tour.newgxplaylist()
        # Loop through Circle Count
        for x in range(circle_count):
            # Define the initial heading based on current heading
            heading = view_angle
            # 360 Degrees/10 = 36 intervals to iterate through
            for y in range(0, 36):
                # New Fly To
                flyto = playlist.newgxflyto(gxduration=duration, gxflytomode=self.fly_to_mode)
                flyto.lookat.latitude = self.x
                flyto.lookat.longitude = self.y
                flyto.lookat.tilt = camera_tilt
                flyto.lookat.range = camera_range
                flyto.lookat.heading = heading
                # adjust the heading by 10 degrees
                heading = heading + 10
                # adjust degrees if above 360
                if heading >= 360:
                    heading = heading - 360
        # Save the file
        self.kml.save("test_circle.kml")
                
