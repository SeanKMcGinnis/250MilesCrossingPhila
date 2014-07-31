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
os.sys.path.append(os.path.dirname(__file__))

import gpxpy
import gpxpy.gpx
import simplekml
import time, datetime, wave
import TeatDip
import subprocess
import logging
import platform
import re

#--------------------------------------------------------------------------------
NOW = None
pointid = None
ClockDateTime = None
Scratch = None

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

        self.dlg.timer = QTimer()
        self.dlg.timer.timeout.connect(self.Time)

        self.lastdirectory = ''


    def initGui(self):
        global Scratch
        self.Scratch = os.path.dirname(__file__)  #     r'C:\Users\Edward\Documents\Philly250\Scratch'
        self.loggerpath = os.path.join(self.Scratch, 'milkmachine_log.log')
        self.logging = True

        #####################################
        #LOGGER
        self.logger = logging.getLogger('milkmachine')
        self.logger.setLevel(logging.DEBUG)

        # create a file handler
        self.handler = logging.FileHandler(self.loggerpath)
        self.handler.setLevel(logging.INFO)

        # create a logging format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)
        self.logger.info('-----------------------------------------------------------------------------------------------------------------------------------------------')
        self.logger.info('-----------------------------------------------------------------------------------------------------------------------------------------------')
        self.logger.info('-----------------------------------------------------------------------------------------------------------------------------------------------')
        self.logger.info('Milk Machine plugin initialized')

        #####################################



        # Create action that will start plugin configuration
        self.action = QAction(
            QIcon(":/plugins/milkmachine/icon.png"),
            u"Milk Machine", self.iface.mainWindow())
        # connect the action to the run method
        self.action.triggered.connect(self.run)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u"&Milk Machine", self.action)

        # Audio Counters - Audio 1
        self.lcd1_C = self.dlg.ui.lcdNumber_Audio1_C
        self.lcd1_D = self.dlg.ui.lcdNumber_Audio1_D
        self.lcd1_P = self.dlg.ui.lcdNumber_Audio1_P


        QObject.connect(self.dlg.ui.chkActivate,SIGNAL("stateChanged(int)"),self.changeActive)
        QObject.connect(self.dlg.ui.buttonImportGPS, SIGNAL("clicked()"), self.browseOpen)
        QObject.connect(self.dlg.ui.buttonDrawTrack, SIGNAL("clicked()"), self.drawtrack)
        QObject.connect(self.dlg.ui.buttonExportTrack, SIGNAL("clicked()"), self.exportToFile)
        QObject.connect(self.iface.legendInterface(), SIGNAL("itemRemoved()"), self.removeCombo)  #currentIndexChanged(int)
        QObject.connect(self.iface.legendInterface(), SIGNAL("itemAdded(QModelIndex)"), self.addedCombo)
        QObject.connect(self.dlg.ui.buttonImport_audio, SIGNAL("clicked()"), self.browseOpenAudio)
        QObject.connect(self.dlg.ui.pushButton_clearAudio1, SIGNAL("clicked()"), self.clearaudio1)
        QObject.connect(self.dlg.ui.pushButton_Audio1, SIGNAL("clicked()"), self.playAudio1)
        QObject.connect(self.dlg.ui.pushButton_stop1, SIGNAL("clicked()"), self.stopAudio1)
        QObject.connect(self.dlg.ui.pushButton_Audio1info, SIGNAL("clicked()"), self.info_Audio1)
        QObject.connect(self.dlg.ui.pushButton_sync, SIGNAL("clicked()"), self.sync)
        QObject.connect(self.iface, SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.active_layer)
        QObject.connect(self.dlg.ui.checkBox_visualization_edit,SIGNAL("stateChanged(int)"),self.vischeck)
        QObject.connect(self.dlg.ui.pushButton_camera_apply, SIGNAL("clicked()"), self.camera_apply)
    ############################################################################
    ## SLOTS


    ############################################################################
    ############################################################################
    ## Visualization
    ############################################################################

    def active_layer(self):
        try:
            self.dlg.ui.checkBox_visualization_edit.setChecked(False)  # uncheck the box everytime
            # get the active layer and populate the combo boxes
            self.ActiveLayer = self.iface.activeLayer()
            if self.ActiveLayer:
                self.ActiveLayer_name = self.ActiveLayer.name()
                self.dlg.ui.lineEdit_visualization_active.setText(self.ActiveLayer_name)
                self.dlg.ui.lineEdit_export_active.setText(self.ActiveLayer_name)

                # enable the checkBox_visualization_edit
                # Get the curretly selected feature

                if self.ActiveLayer.type() == 0: # is the active layer a vector layer?
                    self.dlg.ui.checkBox_visualization_edit.setEnabled(True)

                    # export
                    if self.ActiveLayer.storageType() == 'ESRI Shapefile' and self.ActiveLayer.geometryType() == 0:
                        self.dlg.ui.buttonExportTrack.setEnabled(True)
                        self.dlg.ui.pushButton_TrackInfo.setEnabled(True)
                        self.dlg.ui.pushButton_google_earth.setEnabled(True)
                    else:
                        self.dlg.ui.buttonExportTrack.setEnabled(False)
                        self.dlg.ui.pushButton_TrackInfo.setEnabled(False)
                        self.dlg.ui.pushButton_google_earth.setEnabled(False)
                else:
                    self.dlg.ui.buttonExportTrack.setEnabled(False)
                    self.dlg.ui.pushButton_TrackInfo.setEnabled(False)
                    self.dlg.ui.pushButton_google_earth.setEnabled(False)


            else:
                self.dlg.ui.lineEdit_visualization_active.setText(None)
                self.dlg.ui.lineEdit_export_active.setText(None)
                self.dlg.ui.lineEdit_visualization_camera_longitude.setText(None)
                self.dlg.ui.lineEdit_visualization_camera_latitude.setText(None)
                self.dlg.ui.lineEdit_visualization_camera_altitude.setText(None)
                self.dlg.ui.lineEdit__visualization_camera_gxhoriz.setText(None)
                self.dlg.ui.lineEdit__visualization_camera_heading.setText(None)
                self.dlg.ui.lineEdit__visualization_camera_roll.setText(None)
                self.dlg.ui.lineEdit__visualization_camera_tilt.setText(None)
                self.dlg.ui.checkBox_visualization_edit.setChecked(False)
                self.dlg.ui.checkBox_visualization_edit.setEnabled(False)
                self.dlg.ui.pushButton_camera_apply.setEnabled(False)

                #export
                self.dlg.ui.buttonExportTrack.setEnabled(False)
                self.dlg.ui.pushButton_TrackInfo.setEnabled(False)
                self.dlg.ui.pushButton_google_earth.setEnabled(False)
        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('active_layer function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to update after the current layer was changed. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


    def vischeck(self,state):  # the checkbox is checked or unchecked for vis Editing
        if self.dlg.ui.checkBox_visualization_edit.isChecked():  # the checkbox is check for vis Editing

            if not self.ActiveLayer.isEditable():  # the layer is not editable
                QMessageBox.information(self.iface.mainWindow(),"Visualization Error", 'The currently active layer is not in an "Edit Session".' )
                self.dlg.ui.checkBox_visualization_edit.setChecked(False)
                #iface.actionToggleEditing.trigger()
            else:  # cleared for editing...

                # Get the curretly selected feature
                self.cLayer = self.iface.mapCanvas().currentLayer()
                self.selectList = []
                features = self.cLayer.selectedFeatures()
                for f in features:
                    self.selectList.append(f.id())  #[u'689',u'2014-06-06 13:30:54']  #[u'2014/06/06 10:30:10', u'Time:10:30:10, Latitude: 39.966531, Longitude: -75.172003, Speed: 3.382047, Altitude: 1.596764']

                if len(self.selectList) >= 1:
                    # enable everything
                    self.dlg.ui.lineEdit_visualization_camera_longitude.setEnabled(True)
                    self.dlg.ui.lineEdit_visualization_camera_latitude.setEnabled(True)
                    self.dlg.ui.lineEdit_visualization_camera_altitude.setEnabled(True)
                    self.dlg.ui.comboBox_altitudemode.setEnabled(True)
                    self.dlg.ui.comboBox_gxaltitudemode.setEnabled(True)
                    self.dlg.ui.lineEdit__visualization_camera_gxhoriz.setEnabled(True)
                    self.dlg.ui.lineEdit__visualization_camera_heading.setEnabled(True)
                    self.dlg.ui.lineEdit__visualization_camera_roll.setEnabled(True)
                    self.dlg.ui.lineEdit__visualization_camera_tilt.setEnabled(True)
                    self.dlg.ui.pushButton_camera_apply.setEnabled(True)
                else:
                    QMessageBox.warning( self.iface.mainWindow(),"Active Layer Warning", "Please select points in the active layer to be edited." )



        else:  # checkbox is false, clear shit out
            self.dlg.ui.lineEdit_visualization_camera_longitude.setEnabled(False)
            self.dlg.ui.lineEdit_visualization_camera_latitude.setEnabled(False)
            self.dlg.ui.lineEdit_visualization_camera_altitude.setEnabled(False)
            self.dlg.ui.comboBox_altitudemode.setEnabled(False)
            self.dlg.ui.comboBox_gxaltitudemode.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_camera_gxhoriz.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_camera_heading.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_camera_roll.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_camera_tilt.setEnabled(False)
            self.dlg.ui.pushButton_camera_apply.setEnabled(False)

    def camera_apply(self):

        try:
            # make a dictionary of all of the camera parameters
            camera = {'longitude': None, 'latitude': None,'altitude' : None, 'altitudemode': None,'gxaltitudemode' : None,'gxhoriz' : None,'heading' : None,'roll' : None,'tilt' : None}
            camera['longitude'] = self.dlg.ui.lineEdit_visualization_camera_longitude.text()
            camera['latitude'] = self.dlg.ui.lineEdit_visualization_camera_latitude.text()
            camera['altitude'] = self.dlg.ui.lineEdit_visualization_camera_altitude.text()
            camera['altitudemode'] = self.dlg.ui.comboBox_altitudemode.currentText()
            camera['gxaltitudemode'] = self.dlg.ui.comboBox_gxaltitudemode.currentText()
            camera['gxhoriz'] = self.dlg.ui.lineEdit__visualization_camera_gxhoriz.text()
            camera['heading'] = self.dlg.ui.lineEdit__visualization_camera_heading.text()
            camera['roll'] = self.dlg.ui.lineEdit__visualization_camera_roll.text()
            camera['tilt'] = self.dlg.ui.lineEdit__visualization_camera_tilt.text()
            #QMessageBox.information(self.iface.mainWindow(),"Camera dict", str(camera) )

##            # Populate the Visualization Camera Combo boxes
##            self.dlg.ui.comboBox_altitudemode.clear()
##            altitudemode = [None, 'absolute', 'clampToGround', 'relativeToGround']
##            for alt in altitudemode:
##                self.dlg.ui.comboBox_altitudemode.addItem(alt)
##            self.dlg.ui.comboBox_gxaltitudemode.clear()
##            gxaltitudemode = [None, 'clampToSeaFloor', 'relativeToSeaFloor']
##            for gxalt in gxaltitudemode:
##                self.dlg.ui.comboBox_gxaltitudemode.addItem(gxalt)

            # Get the curretly selected feature
            self.cLayer = self.iface.mapCanvas().currentLayer()
            self.selectList = []
            features = self.cLayer.selectedFeatures()
            for f in features:
                self.selectList.append(f.id())  #[u'689',u'2014-06-06 13:30:54']  #[u'2014/06/06 10:30:10', u'Time:10:30:10, Latitude: 39.966531, Longitude: -75.172003, Speed: 3.382047, Altitude: 1.596764']


            try:
                self.ActiveLayer.beginEditCommand("Camera Editing")
                if len(self.selectList) >= 1:
                    self.ActiveLayer.beginEditCommand("Camera Editing")
                    for f in self.selectList:
                        #self.ActiveLayer.dataProvider().changeAttributeValues({ f : {2: str(camera)} })
                        self.ActiveLayer.changeAttributeValue(f, 2, str(camera))
                    #self.ActiveLayer.updateFields()
                    self.ActiveLayer.endEditCommand()
                else:
                    QMessageBox.warning( self.iface.mainWindow(),"Active Layer Warning", "Please select points in the active layer to be edited." )
            except:
                self.ActiveLayer.destroyEditCommand()
                self.logger.error('camera_apply destroy edit session')
                self.logger.exception(traceback.format_exc())
                self.iface.messageBar().pushMessage("Error", "Failed to apply camera view parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)



        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('camera_apply function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to apply camera view parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


    ############################################################################
    ############################################################################
    ## Import and Sync
    ############################################################################


    def browseOpen(self):
        self.gpsfile = QFileDialog.getOpenFileName(None, "Import Raw GPS File", self.lastdirectory, "*.kml")  #C:\Users\Edward\Documents\Philly250\Scratch
        self.lastdirectory = os.path.dirname(self.gpsfile)

        try:
            if self.gpsfile:
                ftype = self.gpsfile.split(".")[-1]
                if ftype == 'kml':
                    #gpx = TeatDip.mmGPX(self.gpsfile)  # make the gpx class object
                    #gpx.tokml()  # convert the gpx to kml
                    self.dlg.ui.lineEdit_ImportGPS.setText(self.gpsfile) # set the text in the lineedit to the kml path
                    #self.gpx_to_kml = gpx.outfile # make a self variable for the path to the kml
                    #gpx.toGeoJSON()
                    self.dlg.ui.lineEdit_ImportGPS.setText(self.gpsfile)
                    self.dlg.ui.buttonDrawTrack.setEnabled(True)
                    self.dlg.ui.checkBox_headoftrack.setEnabled(True)
                    self.iface.messageBar().pushMessage("Success", "kml file imported into Milk Machine: {0}".format(self.gpsfile), level=QgsMessageBar.INFO, duration=5)
        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('browseOpen function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to import specified file. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

    def drawtrack(self):
        try:
            if self.gpsfile:
                self.dlg.ui.lineEdit_ImportGPS.setText("")  # clear the text of the input

                # make a qgs layer out of the kml, in memory. Then save it as a shapefile. The name of the shapefile will be the same as the kml
                layername = self.gpsfile.split(".")[0].split('/')[-1]
                kmllayer = QgsVectorLayer(self.gpsfile, layername, "ogr")
                # save the kml layer as
                shapepath = self.gpsfile.split(".")[0] + '.shp'
                shapepath_dup = self.gpsfile.split(".")[0] + '_duplicate.shp'
                QgsVectorFileWriter.writeAsVectorFormat(kmllayer, shapepath, "utf-8", None, "ESRI Shapefile")  # working copy
                QgsVectorFileWriter.writeAsVectorFormat(kmllayer, shapepath_dup, "utf-8", None, "ESRI Shapefile")  # duplicate of original
                #bring the shapefile back in, and render it on the map
                shaper = QgsVectorLayer(shapepath, layername, "ogr")
                shaper.dataProvider().addAttributes( [ QgsField("camera",QVariant.String), QgsField("pointsize", QVariant.Int) ] )
                shaper.updateFields()

                # define the layer properties as a dict
                properties = {'size': '3.0'}
                # initalise a new symbol layer with those properties
                symbol_layer = QgsSimpleMarkerSymbolLayerV2.create(properties)
                # replace the default symbol layer with the new symbol layer
                shaper.rendererV2().symbols()[0].changeSymbolLayer(0, symbol_layer)
                shaper.commitChanges()


                QgsMapLayerRegistry.instance().addMapLayer(shaper)
                #kmllayer2 = self.iface.addVectorLayer(shapepath, layername, "ogr")


                #kmlinpath = self.gpsfile + '|layername=WayPoints'
                #kmllayer = self.iface.addVectorLayer(self.gpsfile, 'testkml', "ogr")
                self.dlg.ui.buttonDrawTrack.setEnabled(False)
                self.dlg.ui.checkBox_headoftrack.setEnabled(False)
                #self.iface.QgsMapLayerRegistry.instance().addMapLayer(layer)
                self.iface.messageBar().pushMessage("Track Rendering Success", "The track: {0} has been drawn.".format(self.gpsfile.split("/")[-1]), level=QgsMessageBar.INFO, duration=5)
                self.gpsfile = None

                if self.dlg.ui.checkBox_headoftrack.isChecked(): # draw the head of track
                    #QMessageBox.information(self.iface.mainWindow(),"Head of track", 'head of track yo' )
                    headof = {}
                    cc = 0
                    for f in shaper.getFeatures():
                        if cc == 0:
                            geom = f.geometry()
                            if geom.type() == QGis.Point:
                                headof['coordinates'] = geom.asPoint()
                        cc += 1
                        break

                    # create layer
                    lname = layername + '_head'
                    head = QgsVectorLayer("Point?crs=EPSG:4326", lname, "memory")
                    pr = head.dataProvider()
                    # add a feature
                    fet = QgsFeature()
                    fet.setGeometry( QgsGeometry.fromPoint(QgsPoint(headof['coordinates'][0],headof['coordinates'][1])) )
                    pr.addFeatures([fet])

                    # define the layer properties as a dict
                    properties = {'size': '5.0', 'color': '0,255,0,255'}

                    # initalise a new symbol layer with those properties
                    symbol_layer = QgsSimpleMarkerSymbolLayerV2.create(properties)

                    # replace the default symbol layer with the new symbol layer
                    head.rendererV2().symbols()[0].changeSymbolLayer(0, symbol_layer)
                    head.setLayerTransparency(30)
                    head.commitChanges()
                    QgsMapLayerRegistry.instance().addMapLayer(head)

            else:
                self.iface.messageBar().pushMessage("No Input Track", "Please import a .gpx file or provide a file path (above)", level=QgsMessageBar.WARNING, duration=5)
        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('drawtrack function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to draw track. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


    def browseOpenAudio(self):
        #QMessageBox.information( self.iface.mainWindow(),"Info", "You clicked browse" )
        #QFileDialog.getOpenFileName(QWidget parent=None, QString caption=QString(), QString directory=QString(), QString filter=QString(), QString selectedFilter=None, QFileDialog.Options options=0)
        self.audiopath = QFileDialog.getOpenFileName(None, "Import Raw .wav Audio File",self.lastdirectory, "*.wav")
        self.lastdirectory = os.path.dirname(self.audiopath)
        try:
            if self.audiopath:
                self.dlg.ui.lineEdit_InAudio1.setText(self.audiopath)
                self.lcd1_C.display('0'); self.lcd1_D.display('0'); self.lcd1_P.display('0')
                self.dlg.ui.pushButton_clearAudio1.setEnabled(True)
                self.dlg.ui.pushButton_Audio1info.setEnabled(True)
                self.dlg.ui.pushButton_Audio1.setEnabled(True)
                self.dlg.ui.pushButton_stop1.setEnabled(True)
                self.dlg.ui.pushButton_sync.setEnabled(True)

                self.line_audiopath = self.dlg.ui.lineEdit_InAudio1.text()
                audioname_ext = self.line_audiopath.split('/')[-1]
                audioname = audioname_ext.split('.')[0]
                # Audio start date and time

                w = wave.open(self.line_audiopath)
                # Frame Rate of the Wave File
                framerate = w.getframerate()
                # Number of Frames in the File
                frames = w.getnframes()
                # Estimate length of the file by dividing frames/framerate
                length = frames/framerate # seconds


                self.audio_start = datetime.datetime(int(audioname[0:4]), int(audioname[4:6]), int(audioname[6:8]), int(audioname[8:10]), int(audioname[10:12]), int(audioname[12:14]))
                # Audio end time. Add seconds to the start time
                self.audio_end = self.audio_start + datetime.timedelta(seconds=length)

                self.iface.messageBar().pushMessage("Success", ".wav file imported and ready to play: {0}".format(self.audiopath), level=QgsMessageBar.INFO, duration=5)
        except:

            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('browseOpenAudio function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to import specified file. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

    def clearaudio1(self):
        try:
            self.dlg.ui.lineEdit_InAudio1.setText(None)
            if self.audiopath:
                self.audiopath = None
                self.lcd1_C.display('0')
                self.lcd1_D.display('0')
                self.lcd1_P.display('0')
                self.dlg.ui.pushButton_clearAudio1.setEnabled(False)
                self.dlg.ui.pushButton_Audio1info.setEnabled(False)
                self.dlg.ui.pushButton_Audio1.setEnabled(False)
                self.dlg.ui.pushButton_stop1.setEnabled(False)
                self.dlg.ui.pushButton_sync.setEnabled(False)
                global NOW, pointid, ClockDateTime
                NOW = None; pointid = None; ClockDateTime = None
                self.audio_start = None
                self.audio_end = None
        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('clearaudio1 function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to import specified file. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

    def Time(self):
        global NOW, pointid, ClockDateTime

        if NOW and pointid and ClockDateTime:
            try:

                # Clock Time and Duration
                ClockTime_delta = ClockDateTime + datetime.timedelta(seconds=1)
                diff_sec = ClockDateTime - self.audio_start
                faker = datetime.datetime(2014,1,1,0,0,0) + datetime.timedelta(seconds=diff_sec.seconds)
                self.lcd1_C.display(ClockTime_delta.strftime("%H:%M:%S"))
                self.lcd1_D.display(faker.strftime("%H:%M:%S"))
                ClockDateTime = ClockTime_delta

                # Point ID
                pointid += 1
                self.lcd1_P.display(str(pointid))
                self.cLayer.setSelectedFeatures([pointid])

            except:

                NOW = None; pointid = None; ClockDateTime = None
                if self.pp:
                    self.pp.terminate()
                    self.dlg.timer.stop()
                trace = traceback.format_exc()
                if self.logging == True:
                    self.logger.error('Time function error')
                    self.logger.exception(trace)
                self.iface.messageBar().pushMessage("Error", "Error in Time function. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


    def playAudio1(self):
        try:
            self.line_audiopath = self.dlg.ui.lineEdit_InAudio1.text()
            if self.audiopath and self.line_audiopath:
                #self.audio_start = None
                #self.audio_end = None
                global NOW, pointid, ClockDateTime



                # Get the curretly selected feature
                self.cLayer = self.iface.mapCanvas().currentLayer()
                selectList = []
                try:
                    features = self.cLayer.selectedFeatures()
                    for f in features:
                        selectList.append(f.attributes())  #[u'689',u'2014-06-06 13:30:54']  #[u'2014/06/06 10:30:10', u'Time:10:30:10, Latitude: 39.966531, Longitude: -75.172003, Speed: 3.382047, Altitude: 1.596764']
                        fid = f.id()
                except AttributeError:
                    QMessageBox.warning( self.iface.mainWindow(),"Selected Layer Warning", "Please select the layer and starting point where you would like the audio to start." )

                if len(selectList) == 1:
                    pointid = fid
                    pointdate = selectList[0][0].split(" ")[0]  #2014/06/06
                    pointtime = selectList[0][0].split(" ")[1]  #10:30:10

                    # global date and time for the selected point
                    ClockDateTime = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
                    # local date and time for the selected point
                    selected_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))

                    # Start the video using VLC Media player. Start the video at the specified time
                    # in the video file...

                    #start time of videofile
                    # C:/Users/Edward/Documents/Philly250/Scratch/20140606100800.WAV

                    # Last Modified Time
                    #mtime = time.ctime(os.path.getmtime(sample))
                    # File Creation Time
                    #ctime = time.ctime(os.path.getctime(sample))
                    # Wave Object - ref: https://docs.python.org/3.4/library/wave.html
                    w = wave.open(self.line_audiopath)
                    # Frame Rate of the Wave File
                    framerate = w.getframerate()
                    # Number of Frames in the File
                    frames = w.getnframes()
                    # Estimate length of the file by dividing frames/framerate
                    length = frames/framerate # seconds

                    jumptime = None
                    # if the start of the audio is before the start of the gps track
                    if selected_dt >= self.audio_start and selected_dt < self.audio_end: # if the selected time is larger than the audio start and less than the audio end
                        # how many seconds does the audio have jump ahead to match
                        timediff = selected_dt - self.audio_start # a timedelta object
                        jumptime = timediff.seconds

                    if selected_dt < self.audio_start: # if the selected time is less than audio start
                        global NOW, pointid, ClockDateTime
                        NOW = None; pointid = None; ClockDateTime = None
                        QMessageBox.warning( self.iface.mainWindow(),"Audio Sync Warning", "The selected point occurs before the start of the audio" )

                    if selected_dt > self.audio_end:# if the selected time is greater than audio start
                        global NOW, pointid, ClockDateTime
                        NOW = None; pointid = None; ClockDateTime = None
                        QMessageBox.warning( self.iface.mainWindow(),"Audio Sync Warning", "The selected point occurs after the end of the audio\nThe selected date/time is:{0}\nThe end of the audio is: {1}".format(selected_dt.strftime("%H:%M:%S"), self.audio_end.strftime("%H:%M:%S")) )

                    if jumptime and ClockDateTime:
                        # "C:\Program Files (x86)\VideoLAN\VLC\vlc.exe" file:///C:/Users/Edward/Documents/Philly250/Scratch/Nagra01-0003.WAV --start-time 5
                        #stime = 5
                        wav_path = "file:///" + self.line_audiopath
                        lan_vlc_path = "C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
                        #startupinfo = subprocess.STARTUPINFO()
                        #startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        UserOs = platform.platform()
                        WindOs = re.search('Windows', UserOs, re.I)
                        if WindOs == 'Windows':
                            self.pp = subprocess.Popen(["C:/Program Files (x86)/VideoLAN/VLC/vlc.exe", wav_path, "--start-time", str(jumptime)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        else:
                            self.pp = subprocess.Popen(["/Applications/VLC.app/Contents/MacOS/VLC", self.line_audiopath, "--start-time", str(jumptime)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        NOW = datetime.datetime.now()
                        self.dlg.timer.start(1000)

                        #stdout, stderr = pp.communicate()

        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('playaudio function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Play audio error. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

                    #self.Sound1 = QSound(self.audiopath)
                    #self.Sound1.play()
                    #time.sleep(5)
                    #self.Sound.stop()

                    ##features = cLayer.selectedFeatures()
                    ##features = cLayer.selectedFeatures()
                    ##features = cLayer.selectedFeatures()

    def stopAudio1(self):
        try:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            try:
                self.pp.terminate()
                self.dlg.timer.stop()
            except:
                pass
        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('stopAudio function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed stop audio properly. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

    def info_Audio1(self):
        try:
            if self.audiopath and self.dlg.ui.lineEdit_InAudio1.text():
                iwave = TeatDip.Wave(self.audiopath)
                wavinfo = iwave.wav_info()

                message = ''
                if self.audio_start:
                    wavinfo['Audio Start Header'] = self.audio_start.strftime("%x %X")
                if self.audio_end:
                    wavinfo['Audio End Header'] = self.audio_end.strftime("%x %X")

                message = message + 'Audio Start: \t' + wavinfo['Audio Start Header'] + '\n'
                message = message + 'Audio End: \t' + wavinfo['Audio End Header'] + '\n'
                message = message + 'File length: \t' + str(wavinfo['file length']) + ' seconds\n'
                message = message + 'Frames: \t' + str(wavinfo['frames']) + '\n'

                QMessageBox.information(self.iface.mainWindow(),"Audio File Info", message )
        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('audioInfo function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Audio info error. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

    def sync(self):
        try:
            if self.audiopath and self.dlg.ui.lineEdit_InAudio1.text():
                # iterate through the selected shapefile until you find the matching date/time

                # Get the curretly selected feature
                self.aLayer = self.iface.activeLayer()  #selected layer in TOC. QgsVectorLayer
                matchdict = {}
                cc = 0
                try:
                    for f in self.aLayer.getFeatures(): #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
                        currentatt = f.attributes()
                        pointdate = currentatt[0].split(" ")[0]  #2014/06/06
                        pointtime = currentatt[0].split(" ")[1]
                        current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
                        if cc == 0:
                            track_start_dt = current_dt
                            if current_dt > self.audio_start: # if it is the first attribute and there is no match and the track time is larger than the start of the audio.
                                diff = current_dt - self.audio_start
                                QMessageBox.information(self.iface.mainWindow(),"Audio File Sync Info", 'Audio starts before the begining of the track by {0}'.format(diff) )
                                break
                        elif current_dt == self.audio_start: # the track time and the audio start match
                            matchdict['fid'] = f.id()
                            matchdict['attributes'] = currentatt
                            geom = f.geometry()  # QgsGeometry object, get the geometry
                            if geom.type() == QGis.Point:
                                matchdict['coordinates'] = geom.asPoint() #(-75.1722,39.9659)
                            break
                        cc += 1


                except AttributeError:
                    QMessageBox.warning( self.iface.mainWindow(),"Selected Layer Warning", "Please select the layer that matches the audio track." )

                if matchdict:
                    #make a marker in memory

                    QMessageBox.information(self.iface.mainWindow(),"Audio File Sync Info", 'The audio starts at {0}\nStarting point in track is FID: {1}\nCoordinates: {2}\n\nTrack starts at: {3}'.format(self.audio_start.strftime("%x %X"), matchdict['fid'], str(matchdict['coordinates']),track_start_dt.strftime("%x %X") ) )

                    # create layer
                    lname = self.aLayer.name() + '_audio_start'
                    vl = QgsVectorLayer("Point?crs=EPSG:4326", lname, "memory")
                    pr = vl.dataProvider()

                    # add fields
                    pr.addAttributes( [ QgsField("name", QVariant.String),
                                        QgsField("age",  QVariant.Int),
                                        QgsField("size", QVariant.Double) ] )

                    # add a feature
                    fet = QgsFeature()
                    fet.setGeometry( QgsGeometry.fromPoint(QgsPoint(matchdict['coordinates'][0],matchdict['coordinates'][1])) )
                    fet.setAttributes(["Johny", 2, 0.3])
                    pr.addFeatures([fet])


                    # get the symbol layer
                    symbol_layerq = self.iface.activeLayer().rendererV2().symbols()[0].symbolLayer(0)

                    # get the properties of the symbol layer
                    self.logger.info('Size: {0}'.format( symbol_layerq.size()))
                    self.logger.info('Color: {0}'.format(symbol_layerq.color().name()))


                    # define the layer properties as a dict
                    size2 = float(symbol_layerq.size()) * 2
                    properties = {'size': str(size2), 'color': '255,0,0,255'}

                    # initalise a new symbol layer with those properties
                    symbol_layer = QgsSimpleMarkerSymbolLayerV2.create(properties)

                    # replace the default symbol layer with the new symbol layer
                    vl.rendererV2().symbols()[0].changeSymbolLayer(0, symbol_layer)
                    vl.setLayerTransparency(30)



                    vl.commitChanges()
                    # update layer's extent when new features have been added
                    # because change of extent in provider is not propagated to the layer
                    vl.updateExtents()

                    #starting_point_marker = self.iface.addVectorLayer('memory/' + vl)
                    #self.iface.QgsMapLayerRegistry.instance().addMapLayer(vl)

                    #starting_point_marker = self.iface.addVectorLayer(vl, 'layername', "ogr")
                    QgsMapLayerRegistry.instance().addMapLayer(vl)

                #QMessageBox.information(self.iface.mainWindow(),"Audio File Info", str(self.audio_start) )
        except:
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('sync function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Sync button error. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)



    ############################################################################
    ############################################################################
    ## Export and Details
    ############################################################################

    def addedCombo(self):
        #QMessageBox.information( self.iface.mainWindow(),"Info", 'You added' )
        self.dlg.ui.comboBox_export.clear()
        #self.dlg.ui.comboBox_visualization_active.clear()
        self.layerX = {}
        ii = 0
        for layer in self.iface.legendInterface().layers():
            self.dlg.ui.comboBox_export.addItem(layer.name())
            #self.dlg.ui.comboBox_visualization_active.addItem(layer.name())
            self.layerX[layer.name()] = {'layer source': layer.source()}
            self.layerX[layer.name()] = {'index': ii}
            ii += 1
##            lty = layer.type()
##            if lty is not None:
##                if layer.type() == 0:#QgsMapLayer.VectorLayer:
##                    self.dlg.ui.comboBox_export.addItem(layer.name())

    def removeCombo(self):
        #QMessageBox.information( self.iface.mainWindow(),"Info", 'You removed' )
        self.dlg.ui.comboBox_export.clear()
        #self.dlg.ui.comboBox_visualization_active.clear()
        self.layerX = {}
        ii = 0
        for layer in self.iface.legendInterface().layers():
            self.dlg.ui.comboBox_export.addItem(layer.name())
            #self.dlg.ui.comboBox_visualization_active.addItem(layer.name())
            self.layerX[layer.name()] = {'layer source': layer.source()}
            self.layerX[layer.name()] = {'index': ii}
            ii += 1
##            lty = layer.type()
##            if lty is not None:
##                if layer.type() == 0:#QgsMapLayer.VectorLayer:
##                    self.dlg.ui.comboBox_export.addItem(layer.name())



    def exportToFile(self):

        try:
            cc = 0
            kml = simplekml.Kml()
            for f in self.ActiveLayer.getFeatures(): #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
                geom = f.geometry()
                coords = geom.asPoint() #(-75.1722,39.9659)
                currentatt = f.attributes()

                pointdate = currentatt[0].split(" ")[0]  #2014/06/06
                pointtime = currentatt[0].split(" ")[1] #10:38:48
                current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))


                pnt = kml.newpoint(name=str(cc), coords=[(coords[0], coords[1])], description=str(currentatt[1]))
                pnt.timestamp.when = current_dt.strftime('%Y-%m-%dT%XZ')
                if currentatt[2]:
                    cameradict = eval(currentatt[2])
                    if cameradict['longitude']:
                        pnt.camera.longitude = cameradict['longitude']
                    if cameradict['latitude']:
                        pnt.camera.latitude = cameradict['latitude']
                    if cameradict['altitude']:
                        pnt.camera.altitude = cameradict['altitude']
                    if cameradict['altitudemode']:
                        if cameradict['altitudemode'] == 'absolute':
                            pnt.camera.altitudemode = simplekml.AltitudeMode.absolute
                        if cameradict['altitudemode'] == 'clampToGround':
                            pnt.camera.altitudemode = simplekml.AltitudeMode.clamptoground
                        if cameradict['altitudemode'] == 'relativeToGround':
                            pnt.camera.altitudemode = simplekml.AltitudeMode.relativetoground
                    if cameradict['gxaltitudemode']:
                        if cameradict['gxaltitudemode'] == 'clampToSeaFloor':
                            pnt.camera.gxaltitudemode = simplekml.GxAltitudeMode.clampToSeaFloor
                        if cameradict['gxaltitudemode'] == 'relativeToSeaFloor':
                            pnt.camera.gxaltitudemode = simplekml.GxAltitudeMode.relativetoseafloor
                    if cameradict['gxhoriz']:
                        pnt.camera.gxhoriz = cameradict['gxhoriz']
                    if cameradict['heading']:
                        pnt.camera.heading = cameradict['heading']
                    if cameradict['roll']:
                        pnt.camera.roll = cameradict['roll']
                    if cameradict['tilt']:
                        pnt.camera.tilt = cameradict['tilt']


                    #pnt.camera.altitudemode = simplekml.AltitudeMode.relativetoground



                cc += 1

            exportpath = QFileDialog.getSaveFileName(None, "Save Track", self.lastdirectory, "*.kml")
            kml.save(exportpath)
            self.iface.messageBar().pushMessage("Success", "kml file exported to: {0}".format(exportpath), level=QgsMessageBar.INFO, duration=5)
        except:
            if self.logging == True:
                self.logger.error('sync function error')
                self.logger.exception(traceback.format_exc())
            self.iface.messageBar().pushMessage("Error", "exportToFile error. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)



##        #QMessageBox.information( self.iface.mainWindow(),"Info", "You clicked browse" )
##        #QFileDialog.getOpenFileName(QWidget parent=None, QString caption=QString(), QString directory=QString(), QString filter=QString(), QString selectedFilter=None, QFileDialog.Options options=0)
##
##        # get the current layername in the TOC
##        exportlayername = self.dlg.ui.comboBox_export.currentText()
##        exportlayersource = self.layerX[exportlayername]
##        #QMessageBox.information( self.iface.mainWindow(),"Info", exportlayersource )
##
##        self.iface.actionLayerSaveAs()
##        #exportpath = QFileDialog.getSaveFileName(caption="Import Raw GPS File")


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

    ############################################################################
    ############################################################################
    ## Top Level Functions
    ############################################################################
    def unload(self):  # tear down
        # Remove the plugin menu item and icon
        global NOW, pointid, ClockDateTime
        NOW = None; pointid = None; ClockDateTime = None
        self.logger.info('Quit Milk Machine')
        self.logger.removeHandler(self.handler)
        self.iface.removePluginMenu(u"&Milk Machine", self.action)
        self.iface.removeToolBarIcon(self.action)
        self.dlg.ui.lineEdit_InAudio1.setText(None)
        self.dlg.ui.lineEdit_ImportGPS.setText(None)
        self.dlg.ui.lineEdit_visualization_active.setText(None)
        self.dlg.ui.lineEdit_export_active.setText(None)

        try: self.ActiveLayer_name = None
        except: pass
        try: self.ActiveLayer = None
        except: pass

    # run method that performs all the real work
    def run(self):
        global NOW, pointid, ClockDateTime
        # make our clickTool the tool that we'll use for now
        self.canvas.setMapTool(self.clickTool)
        # show the dialog
        self.dlg.show()

        #if a layer is active, put it in the viz entry
        self.active_layer()

        # Populate the Export combo box
        self.layerX = {}
        ii = 0
        self.dlg.ui.comboBox_export.clear()
        #self.dlg.ui.comboBox_visualization_active.clear()
        for layer in self.iface.legendInterface().layers():
            if layer.type() == QgsMapLayer.VectorLayer:
                self.dlg.ui.comboBox_export.addItem(layer.name())
                #self.dlg.ui.comboBox_visualization_active.addItem(layer.name())
                self.layerX[layer.name()] = {'layer source': layer.source()}
                self.layerX[layer.name()] = {'index': ii}
                ii += 1

        # Populate the Visualization Camera Combo boxes
        self.dlg.ui.comboBox_altitudemode.clear()
        altitudemode = [None, 'absolute', 'clampToGround', 'relativeToGround']
        for alt in altitudemode:
            self.dlg.ui.comboBox_altitudemode.addItem(alt)
        self.dlg.ui.comboBox_gxaltitudemode.clear()
        gxaltitudemode = [None, 'clampToSeaFloor', 'relativeToSeaFloor']
        for gxalt in gxaltitudemode:
            self.dlg.ui.comboBox_gxaltitudemode.addItem(gxalt)

        # Run the dialog event loop
        result = self.dlg.exec_()
        #QMessageBox.information(self.iface.mainWindow(),"result", str(result) )
        # See if OK was pressed
        if result == 1:
            # do something useful (delete the line containing pass and
            # substitute with your code)
            QMessageBox.information(self.iface.mainWindow(),"ok", 'you clicked ok' )
            self.logger.info('Clicked OK')
            self.logger.removeHandler(self.handler)

        if result == 0:

            self.logger.info('Clicked Cancel')
            self.logger.removeHandler(self.handler)

        self.dlg.ui.lineEdit_InAudio1.setText(None)
        self.dlg.ui.lineEdit_ImportGPS.setText(None)
        NOW = None; pointid = None; ClockDateTime = None
        self.dlg.ui.lineEdit_InAudio1.setText(None)
        self.dlg.ui.lineEdit_ImportGPS.setText(None)

        # Export
        self.dlg.ui.lineEdit_export_active.setText(None)

        # Viz
        self.dlg.ui.lineEdit_visualization_active.setText(None)
        try: self.ActiveLayer_name = None
        except: pass
        try: self.ActiveLayer = None
        except: pass
        self.dlg.ui.lineEdit_visualization_active.setText(None)
        self.dlg.ui.checkBox_visualization_edit.setEnabled(False)

        self.dlg.ui.lineEdit_visualization_camera_longitude.setText(None)
        self.dlg.ui.lineEdit_visualization_camera_latitude.setText(None)
        self.dlg.ui.lineEdit_visualization_camera_altitude.setText(None)
        self.dlg.ui.lineEdit__visualization_camera_gxhoriz.setText(None)
        self.dlg.ui.lineEdit__visualization_camera_heading.setText(None)
        self.dlg.ui.lineEdit__visualization_camera_roll.setText(None)
        self.dlg.ui.lineEdit__visualization_camera_tilt.setText(None)

        self.dlg.ui.lineEdit_visualization_camera_longitude.setEnabled(False)
        self.dlg.ui.lineEdit_visualization_camera_latitude.setEnabled(False)
        self.dlg.ui.lineEdit_visualization_camera_altitude.setEnabled(False)
        self.dlg.ui.comboBox_altitudemode.setEnabled(False)
        self.dlg.ui.comboBox_gxaltitudemode.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_camera_gxhoriz.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_camera_heading.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_camera_roll.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_camera_tilt.setEnabled(False)
        self.dlg.ui.checkBox_visualization_edit.setChecked(False)