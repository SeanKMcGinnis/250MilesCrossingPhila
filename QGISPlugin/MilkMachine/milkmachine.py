# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MilkMachine
                                 A QGIS plugin
 Process, edit, and scyncronize GPS and audio tracks with KML output
                              -------------------
        begin                : 2014-06-11
        copyright            : (C) 2014 by polakvanbekkum
        email                : marketst@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from milkmachinedialog import MilkMachineDialog
import os, sys, traceback

import gpxpy
import gpxpy.gpx
import simplekml


class mmGPX(object):
    outfile = None
    def __init__(self, gpxfilepath):
        self.filepath = gpxfilepath
        self.kml = simplekml.Kml()
        self.gpx_file = open(self.filepath)
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
            self.kml.save(self.filepath.split(".")[0] + ".kml")
            mmGPX.outfile = self.filepath.split(".")[0] + ".kml"
        else:
            self.kml.save(path)
            mmGPX.outfile = path

#--------------------------------------------------------------------------------

class MilkMachine:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # a reference to our map canvas
        self.canvas = self.iface.mapCanvas()
        # this Qgis tool emits a Qgis point after each map click on the map canvas
        self.clickTool = QgsMapToolEmitPoint(self.canvas)

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir, 'i18n', 'milkmachine_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = MilkMachineDialog()
        # create a list to hold our selected feature ids
        self.selectList = []
        # current layer ref (set in handleLayerChange)
        self.cLayer = None
        # current layer dataProvider ref (set in handleLayerChange)
        self.provider = None

    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(
            QIcon(":/plugins/milkmachine/icon.png"),
            u"Milk Machine", self.iface.mainWindow())
        # connect the action to the run method
        self.action.triggered.connect(self.run)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u"&Milk Machine", self.action)


        QObject.connect(self.dlg.ui.chkActivate,SIGNAL("stateChanged(int)"),self.changeActive)
        QObject.connect(self.dlg.ui.buttonImportGPS, SIGNAL("clicked()"), self.browseOpen)
        QObject.connect(self.dlg.ui.buttonDrawTrack, SIGNAL("clicked()"), self.drawtrack)
        QObject.connect(self.dlg.ui.buttonExportTrack, SIGNAL("clicked()"), self.exportToFile)
        QObject.connect(self.iface.legendInterface(), SIGNAL("itemRemoved()"), self.removeCombo)  #currentIndexChanged(int)
        QObject.connect(self.iface.legendInterface(), SIGNAL("itemAdded(QModelIndex)"), self.addedCombo)

    def addedCombo(self):
        #QMessageBox.information( self.iface.mainWindow(),"Info", 'You added' )
        self.dlg.ui.comboBox_export.clear()
        for layer in self.iface.legendInterface().layers():
            if layer.type() == QgsMapLayer.VectorLayer:
                self.dlg.ui.comboBox_export.addItem(layer.name())

    def removeCombo(self):
        #QMessageBox.information( self.iface.mainWindow(),"Info", 'You removed' )
        self.dlg.ui.comboBox_export.clear()
        for layer in self.iface.legendInterface().layers():
            if layer.type() == QgsMapLayer.VectorLayer:
                self.dlg.ui.comboBox_export.addItem(layer.name())


    def browseOpen(self):
        #QMessageBox.information( self.iface.mainWindow(),"Info", "You clicked browse" )
        #QFileDialog.getOpenFileName(QWidget parent=None, QString caption=QString(), QString directory=QString(), QString filter=QString(), QString selectedFilter=None, QFileDialog.Options options=0)
        self.gpsfile = QFileDialog.getOpenFileName(caption="Import Raw GPS File",filter="*.gpx")
        try:
            if self.gpsfile:
                gpx = mmGPX(self.gpsfile)  # make the gpx class object
                gpx.tokml()  # convert the gpx to kml
                self.dlg.ui.lineEdit_ImportGPS.setText(gpx.outfile) # set the text in the lineedit to the kml path
                self.gpx_to_kml = gpx.outfile # make a self variable for the path to the kml
                self.iface.messageBar().pushMessage("Success", "GPX converted to KML and saved as: {0}".format(gpx.outfile), level=QgsMessageBar.INFO, duration=10)
        except:
            self.iface.messageBar().pushMessage("Error", "Failed to import specified file. Loser", level=QgsMessageBar.ERROR, duration=10)

    def drawtrack(self):
        try:
            #self.kmlpath = self.dlg.ui.lineEdit_ImportGPS.text() # get the path that is in the lineedit
            if self.gpx_to_kml:
                self.dlg.ui.lineEdit_ImportGPS.setText(""); self.gpsfile = ""
                kmllayer = self.iface.addVectorLayer(self.gpx_to_kml, 'testkml', "ogr")
                #self.iface.QgsMapLayerRegistry.instance().addMapLayer(layer)
##                with open(r'C:\Users\Edward\Documents\Philly250\Scratch\kml.txt', 'w') as f:
##                    f.write(self.gpx_to_kml)
##                trackpts = self.gpxpath + "?type=route" #     "path/to/gpx/file.gpx?type=track"  track, route, waypoint,
##                tracklayer = self.iface.addVectorLayer(trackpts, "TestTrack", "gpx")

                self.iface.messageBar().pushMessage("Track Rendering Success", "The track: {0} has been drawn.".format(self.gpx_to_kml.split("/")[-1]), level=QgsMessageBar.INFO, duration=10)
                self.gpx_to_kml = ""
            else:
                self.iface.messageBar().pushMessage("No Input Track", "Please import a .gpx file or provide a file path (above)", level=QgsMessageBar.WARNING, duration=10)
        except:
            trace = traceback.format_exc()
            with open(r'C:\Users\Edward\Documents\Philly250\Scratch\error.txt', 'w') as f:
                f.write(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to draw track", level=QgsMessageBar.CRITICAL, duration=10)


    def exportToFile(self):
        #QMessageBox.information( self.iface.mainWindow(),"Info", "You clicked browse" )
        #QFileDialog.getOpenFileName(QWidget parent=None, QString caption=QString(), QString directory=QString(), QString filter=QString(), QString selectedFilter=None, QFileDialog.Options options=0)
        self.gpsfile = QFileDialog.getOpenFileName(caption="Import Raw GPS File")

    def changeActive(self,state):
        if (state==Qt.Checked):
            # connect to click signal
            QObject.connect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.handleMouseDown)
            # connect our select function to the canvasClicked signal
            QObject.connect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.selectFeature)
        else:
            # disconnect from click signal
            QObject.disconnect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.handleMouseDown)
            # disconnect our select function to the canvasClicked signal
            QObject.disconnect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.selectFeature)

    def unload(self):  # tear down
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu(u"&Milk Machine", self.action)
        self.iface.removeToolBarIcon(self.action)

    def handleMouseDown(self, point, button):
        self.dlg.clearTextBrowser()
        self.dlg.setTextBrowser(str(point.x()) + " , " +str(point.y()))
        #QMessageBox.information( self.iface.mainWindow(),"Info", "X,Y = %s,%s" % (str(point.x()),str(point.y())) )

    def selectFeature(self, point, button):
        #QMessageBox.information( self.iface.mainWindow(),"Info", "in selectFeature function ININ" )
        # setup the provider select to filter results based on a rectangle
        pntGeom = QgsGeometry.fromPoint(point)
        # scale-dependent buffer of 2 pixels-worth of map units
        pntBuff = pntGeom.buffer( (self.canvas.mapUnitsPerPixel() * 2),0)
        rect = pntBuff.boundingBox()
        # get currentLayer and dataProvider
        cLayer = self.canvas.currentLayer()

        layerlist = []
        layerdatasource = []
        for layer in self.iface.legendInterface().layers():
            layerlist.append(layer.name())
            layerdatasource.append(layer.source())

        QMessageBox.information( self.iface.mainWindow(),"Info", str(layerlist) + str(layerdatasource) )
##        selectList = []
##        if cLayer:
##            provider = cLayer.dataProvider()
##            feat = QgsFeature()
##            # create the select statement
##            provider.select([],rect) # the arguments mean no attributes returned, and do a bbox filter with our buffered rectangle to limit the amount of features
##            while provider.nextFeature(feat):
##                # if the feat geom returned from the selection intersects our point then put it in a list
##                if feat.geometry().intersects(pntGeom):
##                    selectList.append(feat.id())
##
##            # make the actual selection
##            cLayer.setSelectedFeatures(selectList)
##        else:
##            QMessageBox.information( self.iface.mainWindow(),"Info", "No layer currently selected in TOC" )


    # run method that performs all the real work
    def run(self):
        # make our clickTool the tool that we'll use for now
        self.canvas.setMapTool(self.clickTool)
        # show the dialog
        self.dlg.show()

        self.dlg.ui.comboBox_export.clear()
        for layer in self.iface.legendInterface().layers():
            if layer.type() == QgsMapLayer.VectorLayer:
                self.dlg.ui.comboBox_export.addItem(layer.name())


        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result == 1:
            # do something useful (delete the line containing pass and
            # substitute with your code)
            pass
