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

        self.logger.info('-----------------------------------------------------------------------------------------------')
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
    ############################################################################
    ## SLOTS

    def Time(self):
        global NOW, pointid, ClockDateTime

        if NOW and pointid and ClockDateTime:
            try:

                # Clock Time


                ClockTime_delta = ClockDateTime + datetime.timedelta(seconds=1)
                diff_sec = ClockDateTime - self.audio_start
                faker = datetime.datetime(2014,1,1,0,0,0) + datetime.timedelta(seconds=diff_sec.seconds)
                self.lcd1_C.display(ClockTime_delta.strftime("%H:%M:%S"))
                self.lcd1_D.display(faker.strftime("%H:%M:%S"))
                ClockDateTime = ClockTime_delta

##                # Durationinto audio
##
##                nn = datetime.datetime.now() - NOW
##                self.lcd1_D.display(str(nn).split('.')[0])

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

    def addedCombo(self):
        #QMessageBox.information( self.iface.mainWindow(),"Info", 'You added' )
        self.dlg.ui.comboBox_export.clear()
        for layer in self.iface.legendInterface().layers():
            self.dlg.ui.comboBox_export.addItem(layer.name())
##            lty = layer.type()
##            if lty is not None:
##                if layer.type() == 0:#QgsMapLayer.VectorLayer:
##                    self.dlg.ui.comboBox_export.addItem(layer.name())

    def removeCombo(self):
        #QMessageBox.information( self.iface.mainWindow(),"Info", 'You removed' )
        self.dlg.ui.comboBox_export.clear()
        for layer in self.iface.legendInterface().layers():
            self.dlg.ui.comboBox_export.addItem(layer.name())
##            lty = layer.type()
##            if lty is not None:
##                if layer.type() == 0:#QgsMapLayer.VectorLayer:
##                    self.dlg.ui.comboBox_export.addItem(layer.name())

    def browseOpen(self):
        self.gpsfile = QFileDialog.getOpenFileName(None, "Import Raw GPS File", "", "*.kml")  #C:\Users\Edward\Documents\Philly250\Scratch
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
                    self.iface.messageBar().pushMessage("Success", "kml file imported: {0}".format(self.gpsfile), level=QgsMessageBar.INFO, duration=5)
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
                self.dlg.ui.lineEdit_ImportGPS.setText("")
                kmlinpath = self.gpsfile + '|layername=WayPoints'
                kmllayer = self.iface.addVectorLayer(self.gpsfile, 'testkml', "ogr")
                self.dlg.ui.buttonDrawTrack.setEnabled(False)
                #self.iface.QgsMapLayerRegistry.instance().addMapLayer(layer)
                self.iface.messageBar().pushMessage("Track Rendering Success", "The track: {0} has been drawn.".format(self.gpsfile.split("/")[-1]), level=QgsMessageBar.INFO, duration=5)
                self.gpsfile = None
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
        self.audiopath = QFileDialog.getOpenFileName(None, "Import Raw .wav Audio File","", "*.wav")
        try:
            if self.audiopath:
                self.dlg.ui.lineEdit_InAudio1.setText(self.audiopath)
                self.lcd1_C.display('0'); self.lcd1_D.display('0'); self.lcd1_P.display('0')
                self.dlg.ui.pushButton_clearAudio1.setEnabled(True)
                self.dlg.ui.pushButton_Audio1info.setEnabled(True)
                self.dlg.ui.pushButton_Audio1.setEnabled(True)
                self.dlg.ui.pushButton_stop1.setEnabled(True)

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
                global NOW, pointid, ClockDateTime
                NOW = None; pointid = None; ClockDateTime = None
        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('clearaudio1 function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to import specified file. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

    def playAudio1(self):
        try:
            self.line_audiopath = self.dlg.ui.lineEdit_InAudio1.text()
            if self.audiopath and self.line_audiopath:
                self.audio_start = None
                self.audio_end = None
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


                    audioname_ext = self.line_audiopath.split('/')[-1]
                    audioname = audioname_ext.split('.')[0]
                    # Audio start date and time
                    audio_start_dt = datetime.datetime(int(audioname[0:4]), int(audioname[4:6]), int(audioname[6:8]), int(audioname[8:10]), int(audioname[10:12]), int(audioname[12:14]))
                    self.audio_start = audio_start_dt
                    # Audio end time. Add seconds to the start time
                    audio_end_dt = audio_start_dt + datetime.timedelta(seconds=length)
                    self.audio_end = audio_end_dt

                    jumptime = None
                    # if the start of the audio is before the start of the gps track
                    if selected_dt >= audio_start_dt and selected_dt < audio_end_dt: # if the selected time is larger than the audio start and less than the audio end
                        # how many seconds does the audio have jump ahead to match
                        timediff = selected_dt - audio_start_dt # a timedelta object
                        jumptime = timediff.seconds

                    if selected_dt < audio_start_dt: # if the selected time is less than audio start
                        global NOW, pointid, ClockDateTime
                        NOW = None; pointid = None; ClockDateTime = None
                        QMessageBox.warning( self.iface.mainWindow(),"Audio Sync Warning", "The selected point occurs before the start of the audio" )

                    if selected_dt > audio_end_dt:# if the selected time is greater than audio start
                        global NOW, pointid, ClockDateTime
                        NOW = None; pointid = None; ClockDateTime = None
                        QMessageBox.warning( self.iface.mainWindow(),"Audio Sync Warning", "The selected point occurs after the end of the audio\nThe selected date/time is:{0}\nThe end of the audio is: {1}".format(selected_dt.strftime("%H:%M:%S"), audio_end_dt.strftime("%H:%M:%S")) )

                    if jumptime and ClockDateTime:
                        # "C:\Program Files (x86)\VideoLAN\VLC\vlc.exe" file:///C:/Users/Edward/Documents/Philly250/Scratch/Nagra01-0003.WAV --start-time 5
                        #stime = 5
                        wav_path = "file:///" + self.line_audiopath
                        lan_vlc_path = "C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
                        #startupinfo = subprocess.STARTUPINFO()
                        #startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        self.pp = subprocess.Popen(["C:/Program Files (x86)/VideoLAN/VLC/vlc.exe", wav_path, "--start-time", str(jumptime)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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

            #self.Sound1.stop()

    def exportToFile(self):
        #QMessageBox.information( self.iface.mainWindow(),"Info", "You clicked browse" )
        #QFileDialog.getOpenFileName(QWidget parent=None, QString caption=QString(), QString directory=QString(), QString filter=QString(), QString selectedFilter=None, QFileDialog.Options options=0)
        self.gpsfile = QFileDialog.getOpenFileName(caption="Import Raw GPS File")

    def info_Audio1(self):
        try:
            if self.audiopath and self.dlg.ui.lineEdit_InAudio1.text():
                iwave = TeatDip.Wave(self.audiopath)
                wavinfo = iwave.wav_info()




                audio_start_dt = None; audio_end_dt = None
                line_audiopath = self.dlg.ui.lineEdit_InAudio1.text()
                audioname_ext = line_audiopath.split('/')[-1]
                audioname = audioname_ext.split('.')[0]
                # Audio start date and time
                audio_start_dt = datetime.datetime(int(audioname[0:4]), int(audioname[4:6]), int(audioname[6:8]), int(audioname[8:10]), int(audioname[10:12]), int(audioname[12:14]))
                # Audio end time. Add seconds to the start time
                audio_end_dt = audio_start_dt + datetime.timedelta(seconds=wavinfo['file length'])

                message = ''
                if audio_start_dt:
                    wavinfo['Audio Start Header'] = audio_start_dt.strftime("%H:%M:%S")
                if audio_end_dt:
                    wavinfo['Audio End Header'] = audio_end_dt.strftime("%H:%M:%S")


                for key,value in wavinfo.iteritems():
                    message = message + str(key) + ': ' + str(value) + '\n'
                #QMessageBox.information(self.iface.mainWindow(),"Info", str(wavinfo) )
                QMessageBox.information(self.iface.mainWindow(),"Audio File Info", message )
        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('audioInfo function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Audio info error. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

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
        global NOW, pointid, ClockDateTime
        NOW = None; pointid = None; ClockDateTime = None
        self.logger.info('Quit Milk Machine')
        self.logger.removeHandler(self.handler)
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
