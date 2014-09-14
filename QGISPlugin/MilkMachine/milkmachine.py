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
import re, os, StringIO
import math

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

        # Order of the fields in the shapefile
        self.fields ={}


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
        QObject.connect(self.dlg.ui.pushButton_TrackInfo, SIGNAL("clicked()"), self.trackdetails)
        QObject.connect(self.dlg.ui.checkBox_rendering_edit,SIGNAL("stateChanged(int)"),self.rendercheck)
        QObject.connect(self.dlg.ui.pushButton_rendering_icon_apply, SIGNAL("clicked()"), self.icon_apply)
        QObject.connect(self.dlg.ui.pushButton_rendering_label_apply, SIGNAL("clicked()"), self.label_apply)
        QObject.connect(self.dlg.ui.comboBox_rendering_icon_color, SIGNAL("activated(int)"), self.trans_enable)
        QObject.connect(self.dlg.ui.pushButton_rendering_model_apply, SIGNAL("clicked()"), self.model_apply)
        QObject.connect(self.dlg.ui.pushButton_rendering_model_file, SIGNAL("clicked()"), self.model_link)
        QObject.connect(self.dlg.ui.pushButton_rendering_model_xy, SIGNAL("clicked()"), self.model_xy)
        QObject.connect(self.dlg.ui.pushButton_visualization_camera_xy, SIGNAL("clicked()"), self.camera_xy)
        QObject.connect(self.dlg.ui.checkBox_rendering_model_z,SIGNAL("stateChanged(int)"),self.model_altitude_check)
        QObject.connect(self.dlg.ui.pushButton_export_audio_file, SIGNAL("clicked()"), self.file_export_audio)
        QObject.connect(self.dlg.ui.pushButton_google_earth, SIGNAL("clicked()"), self.exportToFile)
        QObject.connect(self.dlg.ui.pushButton_follow_apply, SIGNAL("clicked()"), self.follow_apply)
        QObject.connect(self.dlg.ui.pushButton_time_apply_startend, SIGNAL("clicked()"), self.time_startend_apply)
        QObject.connect(self.dlg.ui.checkBox_time_edit,SIGNAL("stateChanged(int)"),self.timecheck)
        QObject.connect(self.dlg.ui.lineEdit_visualization_follow_altitude,SIGNAL("editingFinished()"),self.tiltpopulate)
        QObject.connect(self.dlg.ui.lineEdit__visualization_follow_range,SIGNAL("editingFinished()"),self.tiltpopulate)
    ############################################################################
    ## SLOTS

    def tiltpopulate(self):
        if self.dlg.ui.lineEdit_visualization_follow_altitude.text() and self.dlg.ui.lineEdit__visualization_follow_range.text():
            altitude = float(self.dlg.ui.lineEdit_visualization_follow_altitude.text())
            ranger = float(self.dlg.ui.lineEdit__visualization_follow_range.text())
            angle = round(math.degrees(math.acos(altitude/ranger)),1)
            self.dlg.ui.lineEdit__visualization_follow_tilt.setText(str(angle))


    # generic function for finding the idices of qgsvector layers
    def field_indices(self, qgsvectorlayer):
        field_dict = {}
        fields = qgsvectorlayer.dataProvider().fields()
        for f in fields:
            field_dict[f.name()] = qgsvectorlayer.fieldNameIndex(f.name())
        return field_dict

    def to_dt(self, dt_string):
        import datetime
        pointdate = dt_string.split(" ")[0]  #2014/06/06
        pointtime = dt_string.split(" ")[1]
        dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
        return dt
        #fid_dt.append(current_dt.strftime("%Y/%m/%d %X"))



    def google_earth(self):
        pass


    ############################################################################
    ############################################################################
    ## Time
    ############################################################################

    def timecheck(self,state):  # the checkbox is checked or unchecked for vis Editing
        try:

            if self.dlg.ui.checkBox_time_edit.isChecked():  # the checkbox is check for vis Editing

                self.ActiveLayer = self.iface.activeLayer()
                if self.ActiveLayer:
                    self.fields = self.field_indices(self.ActiveLayer)

                    if not self.ActiveLayer.isEditable():  # the layer is not editable
                        QMessageBox.information(self.iface.mainWindow(),"Time Editing Error", 'The currently active layer is not in an "Edit Session".' )
                        self.dlg.ui.checkBox_time_edit.setChecked(False)
                        #iface.actionToggleEditing.trigger()
                    else:  # cleared for editing...

                        # Get the curretly selected feature
                        self.cLayer = self.iface.mapCanvas().currentLayer()
                        self.selectList = []
                        features = self.cLayer.selectedFeatures()
                        for f in features:
                            self.selectList.append(f.id())  #[u'689',u'2014-06-06 13:30:54']  #[u'2014/06/06 10:30:10', u'Time:10:30:10, Latitude: 39.966531, Longitude: -75.172003, Speed: 3.382047, Altitude: 1.596764']

                        if len(self.selectList) >= 1:

                            # inputs
                            self.dlg.ui.checkBox_time_before.setEnabled(True)
                            self.dlg.ui.dateTimeEdit_start.setEnabled(True)
                            self.dlg.ui.dateTimeEdit_end.setEnabled(True)
                            self.dlg.ui.checkBox_time_after.setEnabled(True)

                            #populate
                            features = self.ActiveLayer.selectedFeatures()
                            i = 0
                            for f in features:
                                if i == 0:
                                    sel_start = f.attributes()[self.fields['datetime']]
                                else:
                                    sel_end = f.attributes()[self.fields['datetime']]
                                i += 1
                            qdt_start = QDateTime.fromString(sel_start, "yyyy/MM/dd hh:mm:ss")
                            self.dlg.ui.dateTimeEdit_start.setDateTime(qdt_start)
                            qdt_end = QDateTime.fromString(sel_end, "yyyy/MM/dd hh:mm:ss")
                            self.dlg.ui.dateTimeEdit_end.setDateTime(qdt_end)

                            # Apply Buttons
                            self.dlg.ui.pushButton_time_apply_startend.setEnabled(True)

                        else:
                            QMessageBox.warning( self.iface.mainWindow(),"Active Layer Warning", "Please select points in the active layer to be edited." )

            else:  # checkbox is false, clear shit out

                # inputs
                self.dlg.ui.checkBox_time_before.setEnabled(False)
                self.dlg.ui.dateTimeEdit_start.setEnabled(False)
                self.dlg.ui.dateTimeEdit_end.setEnabled(False)
                self.dlg.ui.checkBox_time_after.setEnabled(False)

                # Apply Buttons
                self.dlg.ui.pushButton_time_apply_startend.setEnabled(False)

        except:
            self.dlg.ui.checkBox_time_edit.setChecked(False)
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('timecheck function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to apply time start and end parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)



    def time_startend_apply(self):
        try:
            self.ActiveLayer = self.iface.activeLayer()
            self.fields = self.field_indices(self.ActiveLayer)

            # Start Time
            Qstart_y = self.dlg.ui.dateTimeEdit_start.dateTime().toString('yyyy') #Qdatetime object
            Qstart_m = self.dlg.ui.dateTimeEdit_start.dateTime().toString('M')
            Qstart_d = self.dlg.ui.dateTimeEdit_start.dateTime().toString('d')
            Qstart_h = self.dlg.ui.dateTimeEdit_start.dateTime().toString('h') #Qdatetime object
            Qstart_mm = self.dlg.ui.dateTimeEdit_start.dateTime().toString('m')
            Qstart_s = self.dlg.ui.dateTimeEdit_start.dateTime().toString('s')

            dt_start = datetime.datetime(int(Qstart_y), int(Qstart_m), int(Qstart_d), int(Qstart_h), int(Qstart_mm), int(Qstart_s))

            # End Time
            Qend_y = self.dlg.ui.dateTimeEdit_end.dateTime().toString('yyyy') #Qdatetime object
            Qend_m = self.dlg.ui.dateTimeEdit_end.dateTime().toString('M')
            Qend_d = self.dlg.ui.dateTimeEdit_end.dateTime().toString('d')
            Qend_h = self.dlg.ui.dateTimeEdit_end.dateTime().toString('h') #Qdatetime object
            Qend_mm = self.dlg.ui.dateTimeEdit_end.dateTime().toString('m')
            Qend_s = self.dlg.ui.dateTimeEdit_end.dateTime().toString('s')

            dt_end = datetime.datetime(int(Qend_y), int(Qend_m), int(Qend_d), int(Qend_h), int(Qend_mm), int(Qend_s))

            # Find the starting and end fid for the layer, and the start and end fid for the selection
            allfids = self.ActiveLayer.allFeatureIds()
            selectfids = self.ActiveLayer.selectedFeaturesIds()

            features = self.ActiveLayer.getFeatures()
            i = 0
            for f in features:
                if i == 0:
                    layer_start = f.attributes()[self.fields['datetime']]
                else:
                    layer_end = f.attributes()[self.fields['datetime']]
                i += 1

            features = self.ActiveLayer.selectedFeatures()
            i = 0
            for f in features:
                if i == 0:
                    sel_start = f.attributes()[self.fields['datetime']]
                else:
                    sel_end = f.attributes()[self.fields['datetime']]
                i += 1

            layer_start_dt = self.to_dt(layer_start)
            layer_end_dt = self.to_dt(layer_end)
            sel_start_dt = self.to_dt(sel_start)
            sel_end_dt = self.to_dt(sel_end)

            self.logger.info(layer_start)
            self.logger.info(layer_end)
            self.logger.info(sel_start)
            self.logger.info(sel_end)

            seldiff = sel_end_dt - sel_start_dt
            newdiff = dt_end - dt_start

            currentinterval = round(float(len(selectfids)) / seldiff.seconds, 3) # how many pts per time
            self.logger.info(currentinterval)

            #newinterval = round(float(len(selectfids)) / newdiff.seconds,3)
            newinterval = round(newdiff.seconds / float((len(selectfids)-1)),3)
            self.logger.info(newinterval)

            newtimelist = [dt_start]
            for i in range(len(selectfids)-1):
                ct = newtimelist[i]
                newtimelist.append(ct + datetime.timedelta(milliseconds = newinterval)) # add miliseconds to the time

            self.logger.info(newtimelist)

            newtimelistround = [dt_start]
            for i,t in enumerate(newtimelist):
                if i > 0:
                    estime = newtimelist[i]
                    calcsec = int(round(float(estime.microsecond) /1000))
                    rtime = dt_start + datetime.timedelta(seconds = calcsec)
                    #rtime = datetime.datetime(estime.year, estime.month, estime.day, estime.hour, estime.minute, calcsec)
                    newtimelistround.append(rtime)

            self.logger.info(newtimelistround)

            self.ActiveLayer.startEditing()
            self.ActiveLayer.beginEditCommand('datetime edit selected')
            for i,v in enumerate(newtimelistround):
                valstr = v.strftime("%Y/%m/%d %X")
                self.ActiveLayer.changeAttributeValue(selectfids[i], self.fields['datetime'], valstr)
            self.ActiveLayer.endEditCommand()
##            #self.ActiveLayer.commitChanges()

            # If the user wants to adjust the time beforehand by the chosen interval...
            if self.dlg.ui.checkBox_time_before.isChecked():
                if layer_start_dt < sel_start_dt:

                    difflen = selectfids[0] - allfids[0]  #sel_start_dt - layer_start_dt
                    newtimelist = [dt_start]
                    for i in range(difflen):
                        ct = newtimelist[i]
                        newtimelist.append(ct + datetime.timedelta(milliseconds = newinterval)) # add miliseconds to the time

                    self.logger.info(newtimelist)

                    newtimelistround = [dt_start]
                    for i,t in enumerate(newtimelist):
                        if i > 0:
                            estime = newtimelist[i]
                            calcsec = int(round(float(estime.microsecond) /1000))
                            rtime = dt_start - datetime.timedelta(seconds = calcsec)
                            newtimelistround.append(rtime)

                    newtimelistround.reverse() # revese the list
                    newtimelistround.pop()
                    self.logger.info(newtimelistround)

                    #allfids
                    #selectfids

                    self.ActiveLayer.startEditing()
                    self.ActiveLayer.beginEditCommand('datetime edit before')
                    for i,v in enumerate(newtimelistround):
                        valstr = v.strftime("%Y/%m/%d %X")
                        self.ActiveLayer.changeAttributeValue(i, self.fields['datetime'], valstr)
                    self.ActiveLayer.endEditCommand()
##                    self.ActiveLayer.endEditCommand()

            # If the user wants to adjust the time AFTER the chosen interval...
            if self.dlg.ui.checkBox_time_after.isChecked():
                if layer_end_dt > sel_end_dt:

                    difflen = allfids[-1] - selectfids[-1]
                    newtimelist = [dt_end]
                    self.logger.info('dt end {0}'.format(dt_end))
                    for i in range(difflen):
                        ct = newtimelist[i]
                        newtimelist.append(ct + datetime.timedelta(milliseconds = newinterval)) # add miliseconds to the time

                    self.logger.info(newtimelist)

                    newtimelistround = [dt_end]
                    for i,t in enumerate(newtimelist):
                        if i > 0:
                            estime = newtimelist[i]
                            calcsec = int(round(float(estime.microsecond) /1000))
                            rtime = dt_end + datetime.timedelta(seconds = calcsec)
                            newtimelistround.append(rtime)
                    self.logger.info('newtimelistround {0}'.format(newtimelistround))
                    newtimelistround.reverse() # revese the list
                    newtimelistround.pop()
                    newtimelistround.reverse()
                    self.logger.info('newtimelistround {0}'.format(newtimelistround))

                    self.logger.info('len allfids {0}'.format(len(allfids)))
                    self.logger.info('len select fids {0}'.format(len(selectfids)))
                    self.logger.info(selectfids[-1])
                    #allfids
                    #selectfids

                    self.ActiveLayer.startEditing()
                    self.ActiveLayer.beginEditCommand('datetime edit after')
                    for i,v in enumerate(newtimelistround):
                        valstr = v.strftime("%Y/%m/%d %X")
                        fid = i+selectfids[-1]+1
                        self.ActiveLayer.changeAttributeValue(allfids[fid], self.fields['datetime'], valstr)
                    self.ActiveLayer.endEditCommand()
##                    self.ActiveLayer.endEditCommand()




        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('time_startend_apply function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to apply time start and end parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


    ############################################################################
    ############################################################################
    ## Placemarks/Rendering
    ############################################################################

    def model_altitude_check(self, state):
        if state == Qt.Checked:
            self.dlg.ui.lineEdit_rendering_model_altitude.setEnabled(False)
            self.dlg.ui.lineEdit_rendering_model_altitude.setText('altitude')
        else:
            self.dlg.ui.lineEdit_rendering_model_altitude.setEnabled(True)
            self.dlg.ui.lineEdit_rendering_model_altitude.setText(None)



    def model_xy(self):
        xylist = []
        try:
            for f in self.ActiveLayer.selectedFeatures(): #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
                geom = f.geometry()
                coords = geom.asPoint() #(-75.1722,39.9659)
                xylist.append(coords)

            if len(xylist) == 1: #only 1 point selected
                self.dlg.ui.lineEdit_rendering_model_longitude.setText(str(xylist[0][0]))
                self.dlg.ui.lineEdit_rendering_model_latitude.setText(str(xylist[0][1]))
            else:
                QMessageBox.warning( self.iface.mainWindow(),"xy Button Warning", "Please select 1 point when using the xy button." )

        except:
            self.logger.error('model_xy function error')
            self.logger.exception(traceback.format_exc())
            self.iface.messageBar().pushMessage("Error", "Failed to apply coordinates to model long/lat. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

    def model_link(self):
        try:
            self.linkfile = QFileDialog.getOpenFileName(None, "Choose Collada DAE file", self.lastdirectory, "*.dae")  #C:\Users\Edward\Documents\Philly250\Scratch
            if self.linkfile:
                self.lastdirectory = os.path.dirname(self.linkfile)
                self.dlg.ui.lineEdit_rendering_model_link.setText(self.linkfile)

        except:
            self.logger.error('model_link function errir')
            self.logger.exception(traceback.format_exc())
            self.iface.messageBar().pushMessage("Error", "Failed get link to DAE file. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


    def model_apply(self):
        try:
            self.ActiveLayer = self.iface.activeLayer()
            self.fields = self.field_indices(self.ActiveLayer)
            # make a dictionary of all icon parameters
            model = {'link': None, 'longitude': None, 'latitude': None, 'altitude' : None, 'scale': None}

            model['link'] = self.dlg.ui.lineEdit_rendering_model_link.text()
            model['longitude'] = self.dlg.ui.lineEdit_rendering_model_longitude.text()
            model['latitude'] = self.dlg.ui.lineEdit_rendering_model_latitude.text()
            model['altitude'] = self.dlg.ui.lineEdit_rendering_model_altitude.text()
            model['scale'] = self.dlg.ui.lineEdit_rendering_model_scale.text()

            # Get the curretly selected feature
            self.cLayer = self.iface.mapCanvas().currentLayer()
            self.fields = self.field_indices(self.cLayer)
            self.selectList = []
            model_altitude = []
            features = self.cLayer.selectedFeatures()
            for f in features: #QgsFeature
                self.selectList.append(f.id())  #[u'689',u'2014-06-06 13:30:54']  #[u'2014/06/06 10:30:10', u'Time:10:30:10, Latitude: 39.966531, Longitude: -75.172003, Speed: 3.382047, Altitude: 1.596764']
                try:
                    model_altitude.append(f.attributes()[self.fields['descriptio']].split(",")[4].split(': ')[1])
                except:
                    try:
                        model_altitude.append(f.attributes()[self.fields['Descriptio']].split(",")[4].split(': ')[1])
                    except:
                        self.logger.error('model_apply destroy edit session')
                        self.logger.exception(traceback.format_exc())
                        self.logger.info('self.fields keys {0}'.format(self.fields.keys))
                        self.iface.messageBar().pushMessage("Error", "Failed to apply model style parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

            try:
                if len(self.selectList) >= 1:
                    self.ActiveLayer.startEditing()
                    self.ActiveLayer.beginEditCommand("Rendering Editing")
                    for i,f in enumerate(self.selectList):
                        if self.dlg.ui.lineEdit_rendering_model_altitude.text() == 'altitude':
                            model['altitude'] = model_altitude[i]
                            self.ActiveLayer.changeAttributeValue(f, self.fields['model'], str(model))
                        else:
                            self.ActiveLayer.changeAttributeValue(f, self.fields['model'], str(model))
                    self.ActiveLayer.endEditCommand()
                else:
                    QMessageBox.warning( self.iface.mainWindow(),"Active Layer Warning", "Please select points in the active layer to be edited." )
            except:
                self.ActiveLayer.destroyEditCommand()
                self.logger.error('model_apply destroy edit session')
                self.logger.exception(traceback.format_exc())
                self.iface.messageBar().pushMessage("Error", "Failed to apply model style parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)



        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('icon_apply function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to apply icon style parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)



    def trans_enable(self):
        col = self.dlg.ui.comboBox_rendering_icon_color.currentText()
        if col:
            self.dlg.ui.lineEdit_rendering_icon_transparency.setEnabled(True)
        else:
            self.dlg.ui.lineEdit_rendering_icon_transparency.setEnabled(False)


    def rendercheck(self,state):  # the checkbox is checked or unchecked for vis Editing
        if self.dlg.ui.checkBox_rendering_edit.isChecked():  # the checkbox is check for vis Editing

            if self.ActiveLayer:
                if self.ActiveLayer.isEditable():
                     # cleared for editing...

                    # Get the curretly selected feature
                    self.cLayer = self.iface.mapCanvas().currentLayer()
                    self.selectList = []
                    features = self.cLayer.selectedFeatures()
                    for f in features:
                        self.selectList.append(f.id())  #[u'689',u'2014-06-06 13:30:54']  #[u'2014/06/06 10:30:10', u'Time:10:30:10, Latitude: 39.966531, Longitude: -75.172003, Speed: 3.382047, Altitude: 1.596764']

                    if len(self.selectList) >= 1:
                        # enable everything

                        # label style
                        self.dlg.ui.comboBox_rendering_label_color.setEnabled(True)
                        self.dlg.ui.comboBox_rendering_label_colormode.setEnabled(True)
                        self.dlg.ui.lineEdit_rendering_label_scale.setEnabled(True)

                        # Icon Style
                        self.dlg.ui.comboBox_rendering_icon_color.setEnabled(True)
                        #self.dlg.ui.lineEdit_rendering_icon_transparency.setEnabled(True)
                        self.dlg.ui.comboBox_rendering_icon_colormode.setEnabled(True)
                        self.dlg.ui.lineEdit_rendering_icon_scale.setEnabled(True)
                        self.dlg.ui.lineEdit_rendering_icon_heading.setEnabled(True)
                        self.dlg.ui.lineEdit_rendering_icon_icon.setEnabled(True)
                        #self.dlg.ui.lineEdit_rendering_icon_hotspot.setEnabled(True)

                        # Model
                        self.dlg.ui.lineEdit_rendering_model_link.setEnabled(True)
                        self.dlg.ui.lineEdit_rendering_model_longitude.setEnabled(True)
                        self.dlg.ui.lineEdit_rendering_model_latitude.setEnabled(True)
                        if not self.dlg.ui.checkBox_rendering_model_z.isChecked():
                            self.dlg.ui.lineEdit_rendering_model_altitude.setEnabled(True)
                        self.dlg.ui.lineEdit_rendering_model_scale.setEnabled(True)
                        self.dlg.ui.pushButton_rendering_model_file.setEnabled(True)
                        self.dlg.ui.pushButton_rendering_model_xy.setEnabled(True)
                        self.dlg.ui.checkBox_rendering_model_z.setEnabled(True)


                        # Apply Buttons
                        self.dlg.ui.pushButton_rendering_icon_apply.setEnabled(True)
                        self.dlg.ui.pushButton_rendering_label_apply.setEnabled(True)
                        self.dlg.ui.pushButton_rendering_model_apply.setEnabled(True)

                elif not self.ActiveLayer.isEditable():  # the layer is not editable
                    QMessageBox.information(self.iface.mainWindow(),"Visualization Error", 'The currently active layer is not in an "Edit Session".' )
                    self.dlg.ui.checkBox_rendering_edit.setChecked(False)
                    #iface.actionToggleEditing.trigger()

                else:
                    QMessageBox.warning( self.iface.mainWindow(),"Active Layer Warning", "Please select points in the active layer to be edited." )



        else:  # checkbox is false, clear shit out

            # Label style
            self.dlg.ui.comboBox_rendering_label_color.setEnabled(False)
            self.dlg.ui.comboBox_rendering_label_colormode.setEnabled(False)
            self.dlg.ui.lineEdit_rendering_label_scale.setEnabled(False)

            # Icon Style
            self.dlg.ui.comboBox_rendering_icon_color.setEnabled(False)
            self.dlg.ui.lineEdit_rendering_icon_transparency.setEnabled(False)
            self.dlg.ui.comboBox_rendering_icon_colormode.setEnabled(False)
            self.dlg.ui.lineEdit_rendering_icon_scale.setEnabled(False)
            self.dlg.ui.lineEdit_rendering_icon_heading.setEnabled(False)
            self.dlg.ui.lineEdit_rendering_icon_icon.setEnabled(False)
            self.dlg.ui.lineEdit_rendering_icon_hotspot.setEnabled(False)

            # Model
            self.dlg.ui.lineEdit_rendering_model_link.setEnabled(False)
            self.dlg.ui.lineEdit_rendering_model_longitude.setEnabled(False)
            self.dlg.ui.lineEdit_rendering_model_latitude.setEnabled(False)
            self.dlg.ui.lineEdit_rendering_model_altitude.setEnabled(False)
            self.dlg.ui.lineEdit_rendering_model_scale.setEnabled(False)
            self.dlg.ui.pushButton_rendering_model_file.setEnabled(False)
            self.dlg.ui.pushButton_rendering_model_xy.setEnabled(False)
            self.dlg.ui.checkBox_rendering_model_z.setEnabled(False)

            # Apply
            self.dlg.ui.pushButton_rendering_icon_apply.setEnabled(False)
            self.dlg.ui.pushButton_rendering_label_apply.setEnabled(False)
            self.dlg.ui.pushButton_rendering_model_apply.setEnabled(False)


    def icon_apply(self):

        try:

            self.cLayer = self.iface.mapCanvas().currentLayer()
            self.fields = self.field_indices(self.cLayer)
            # make a dictionary of all icon parameters
            icon = {'color': None, 'transparency': None, 'colormode': None,'scale' : None, 'heading': None,'icon' : None ,'hotspot' : None}

            icon['color'] = self.dlg.ui.comboBox_rendering_icon_color.currentText()
            icon['transparency'] = self.dlg.ui.lineEdit_rendering_icon_transparency.text()
            icon['colormode'] = self.dlg.ui.comboBox_rendering_icon_colormode.currentText()
            icon['scale'] = self.dlg.ui.lineEdit_rendering_icon_scale.text()
            icon['heading'] = self.dlg.ui.lineEdit_rendering_icon_heading.text()
            icon['icon'] = self.dlg.ui.lineEdit_rendering_icon_icon.text()
            icon['hotspot'] = self.dlg.ui.lineEdit_rendering_icon_hotspot.text()

            # Get the curretly selected feature
            self.cLayer = self.iface.mapCanvas().currentLayer()
            self.fields = self.field_indices(self.cLayer)
            self.selectList = []
            features = self.cLayer.selectedFeatures()
            for f in features:
                self.selectList.append(f.id())  #[u'689',u'2014-06-06 13:30:54']  #[u'2014/06/06 10:30:10', u'Time:10:30:10, Latitude: 39.966531, Longitude: -75.172003, Speed: 3.382047, Altitude: 1.596764']


            try:
                self.ActiveLayer.beginEditCommand("Rendering Editing")
                if len(self.selectList) >= 1:
                    self.ActiveLayer.beginEditCommand("Rendering Editing")
                    for f in self.selectList:
                        self.ActiveLayer.changeAttributeValue(f, self.fields['iconstyle'], str(icon))
                    self.ActiveLayer.updateFields()
                    self.ActiveLayer.endEditCommand()
                else:
                    QMessageBox.warning( self.iface.mainWindow(),"Active Layer Warning", "Please select points in the active layer to be edited." )
            except:
                self.ActiveLayer.destroyEditCommand()
                self.logger.error('icon_apply destroy edit session')
                self.logger.exception(traceback.format_exc())
                self.iface.messageBar().pushMessage("Error", "Failed to apply icon style parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)
        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('icon_apply function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to apply icon style parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

    def label_apply(self):
        try:

            self.cLayer = self.iface.mapCanvas().currentLayer()
            self.fields = self.field_indices(self.cLayer)
            # make a dictionary of all icon parameters
            label = {'color': None, 'colormode': None,'scale' : None}

            label['color'] = self.dlg.ui.comboBox_rendering_label_color.currentText()
            label['colormode'] = self.dlg.ui.comboBox_rendering_label_colormode.currentText()
            label['scale'] = self.dlg.ui.lineEdit_rendering_label_scale.text()

            # Get the curretly selected feature
            self.cLayer = self.iface.mapCanvas().currentLayer()
            self.fields = self.field_indices(self.cLayer)
            self.selectList = []
            features = self.cLayer.selectedFeatures()
            for f in features:
                self.selectList.append(f.id())  #[u'689',u'2014-06-06 13:30:54']  #[u'2014/06/06 10:30:10', u'Time:10:30:10, Latitude: 39.966531, Longitude: -75.172003, Speed: 3.382047, Altitude: 1.596764']

            try:
                self.ActiveLayer.beginEditCommand("Rendering Editing")
                if len(self.selectList) >= 1:
                    self.ActiveLayer.beginEditCommand("Rendering Editing")
                    for f in self.selectList:
                        self.ActiveLayer.changeAttributeValue(f, self.fields['labelstyle'], str(label))
                    self.ActiveLayer.updateFields()
                    self.ActiveLayer.endEditCommand()
                else:
                    QMessageBox.warning( self.iface.mainWindow(),"Active Layer Warning", "Please select points in the active layer to be edited." )
            except:
                self.ActiveLayer.destroyEditCommand()
                self.logger.error('label_apply destroy edit session')
                self.logger.exception(traceback.format_exc())
                self.iface.messageBar().pushMessage("Error", "Failed to apply label style parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('label_apply function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to apply label style parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

    ############################################################################
    ############################################################################
    ## Tour / Visualization
    ############################################################################

    def follow_apply(self):
        try:
            self.fields = self.field_indices(self.ActiveLayer)
            # make a dictionary of all of the camera parameters
            camera = {'longitude': None, 'longitude_off': None, 'latitude': None, 'latitude_off': None, 'altitude' : None, 'altitudemode': None,'gxaltitudemode' : None,'gxhoriz' : None,'heading' : None,'roll' : None,'tilt' : None, 'range': None, 'follow_angle': None}
            flyto = {'name': None, 'flyToMode': None, 'duration': None}


            flyto['name'] = self.dlg.ui.lineEdit_tourname.text()
            flyto['flyToMode'] = self.dlg.ui.comboBox_flyto_mode.currentText()
            flyto['duration'] = 1 #self.dlg.ui.lineEdit_flyto_duration.text()


            # check for 'relativeToModel' in model field 'altitude' key
            camera['altitude'] = self.dlg.ui.lineEdit_visualization_follow_altitude.text()
            camera['altitudemode'] = self.dlg.ui.comboBox_follow_altitudemode.currentText()
            camera['gxaltitudemode'] = self.dlg.ui.comboBox_follow_gxaltitudemode.currentText()
            camera['gxhoriz'] = self.dlg.ui.lineEdit__visualization_follow_gxhoriz.text()
            camera['tilt'] = self.dlg.ui.lineEdit__visualization_follow_tilt.text()
            camera['range'] = self.dlg.ui.lineEdit__visualization_follow_range.text()
            camera['follow_angle'] = self.dlg.ui.lineEdit__visualization_follow_follow_angle.text()


            # Calculate Heading !! Select All Features in the Current Layer !!
            forward_int = int(self.dlg.ui.lineEdit__visualization_follow_smoother.text())  # default to 1
            #self.selectList = self.ActiveLayer.selectedFeaturesIds()  #list of all the feature ids
            layerlen = len(self.selectList)-1
            #self.ActiveLayer.setSelectedFeatures(self.selectList)  # select everything

            # calculate heading
            cordslist = []  # alist of tuples. [(x,y), (x,y)]
            altitudelist = []
            self.selectList = []  #[[id, (x,y), altitude]]
            selectflyto = []

            try:
                for f in self.ActiveLayer.selectedFeatures():          #getFeatures():
                    geom = f.geometry()

                    if camera['altitudemode'] == 'relativeToModel':
                        modelfield = eval(f.attributes()[self.fields['model']])
                        if not camera['altitude']:
                            alt = 0
                        else:
                            alt = float(camera['altitude'])
                        altitudelist.append(float(modelfield['altitude']) + alt)
                        altinum = float(modelfield['altitude']) + alt
                        self.selectList.append([f.id(), geom.asPoint(), altinum])
                    else:
                        self.selectList.append([f.id(), geom.asPoint()])

                    # get the time vector in order to calculate duration of the flyto
                    currentatt = f.attributes()
                    pointdate = currentatt[self.fields['datetime']].split(" ")[0]  #2014/06/06
                    pointtime = currentatt[self.fields['datetime']].split(" ")[1]
                    current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
                    selectflyto.append([f.id(), flyto, current_dt])  # [[fid, {'name', 'flytomode', 'duration'}, dt], ...]

                # sort self.selectList by fid
                def getKey(item):
                    return item[0]
                self.selectList = sorted(self.selectList, key=getKey)  #[[id, (x,y), altitude]]
                selectflyto = sorted(selectflyto, key=getKey)  # [[fid, {'name', 'flytomode', 'duration'}, dt], ...]
                selectflyto2 = selectflyto
                newdiff = []
                # calcualte duration of flyto and replace the dictionary value
                for i,fly in enumerate(selectflyto):
                    if i <= (len(selectflyto)-2):
                        nexttime = selectflyto[i+1][2]
                        thistime = fly[2]
                        difftime = nexttime - thistime
                        #self.logger.info('next {0}, this {1}, diff {2}'.format(nexttime, thistime, difftime.seconds))
                        #if difftime.seconds > 1:
                            #self.logger.info('larger by  {0}'.format(difftime.seconds))
                            #selectflyto2[i][1]['duration'] = str(difftime.seconds)
                        newdiff.append(difftime.seconds)
                newdiff.append(1)
                #self.logger.info(selectflyto2)
                newlistwithflyto = []
                for i,v in enumerate(newdiff):
                    newlistwithflyto.append({'name': self.dlg.ui.lineEdit_tourname.text(), 'flyToMode': self.dlg.ui.comboBox_flyto_mode.currentText(), 'duration': v})

                self.logger.info(newdiff)
                for bb in newlistwithflyto:
                    self.logger.info(bb)

            except:
                #QMessageBox.warning( self.iface.mainWindow(),"Camera Altitude Error", "Please make sure that the 'model' field has 'altitude' values. This can be calculated in the 'Placemarks' tab for Models." )
                self.logger.exception(traceback.format_exc())
                self.iface.messageBar().pushMessage("Error", "Failed to apply camera view parameters for Follow Tour. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

            headinglist = []
            featurelen = len(self.selectList) - 1
            forwardlen = featurelen - forward_int
            #self.logger.info(self.selectList)
            for i,v in enumerate(self.selectList):
                if i >= 0 and i <= forwardlen:
                    forwardlist = []
                    for ii in range(forward_int):
                        forwardlist.append(TeatDip.compass_bearing((v[1][1],v[1][0]),(self.selectList[i+ii+1][1][1] ,self.selectList[i+ii+1][1][0])))
                    #self.logger.info('list: {0}, mean: {1}'.format(forwardlist,TeatDip.mean_angle(forwardlist) ))
                    headinglist.append(TeatDip.mean_angle(forwardlist))
                    #headinglist.append(TeatDip.compass_bearing((cordslist[i-1][1] , cordslist[i-1][0]), (v[1],v[0])) )
                else:
                    headinglist.append(headinglist[i-1])
            #self.logger.info(headinglist)

            try:
                if len(self.selectList) >= 1:
                    self.ActiveLayer.startEditing()
                    self.ActiveLayer.beginEditCommand("Camera Editing")
                    for i,f in enumerate(self.selectList):   #[[id, (x,y), altitude]]
                        #self.logger.info('enum {0} {1}'.format(i,f))
                        if len(f) == 3:
                            camera['altitude'] = f[2]
                        camera['heading'] = headinglist[i]
                        camera['longitude'] = f[1][0]; camera['latitude'] = f[1][1]
                        self.ActiveLayer.changeAttributeValue(f[0], self.fields['camera'], str(camera))

                        #self.ActiveLayer.changeAttributeValue(f[0], self.fields['flyto'], str(flyto))
                        self.ActiveLayer.changeAttributeValue(f[0], self.fields['flyto'], str(newlistwithflyto[i]))

                    self.ActiveLayer.endEditCommand()
                else:
                    QMessageBox.warning( self.iface.mainWindow(),"Active Layer Warning", "Please select points in the active layer to be edited." )
            except:
                self.ActiveLayer.destroyEditCommand()
                self.logger.error('follow_apply error.')
                self.logger.exception(traceback.format_exc())
                self.iface.messageBar().pushMessage("Error", "Failed to apply camera view parameters for Follow Tour. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)



        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('follow_apply function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to apply camera view parameters for Follow Tour. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


    def active_layer(self):
        try:
            self.dlg.ui.checkBox_visualization_edit.setChecked(False)  # uncheck the box everytime
            # get the active layer and populate active layer boxes in each of the tabs
            self.ActiveLayer = self.iface.activeLayer()
            if self.ActiveLayer:
                self.ActiveLayer_name = self.ActiveLayer.name()
                self.dlg.ui.lineEdit_visualization_active.setText(self.ActiveLayer_name)
                self.dlg.ui.lineEdit_export_active.setText(self.ActiveLayer_name)
                self.dlg.ui.lineEdit_rendering_active.setText(self.ActiveLayer_name)
                self.dlg.ui.lineEdit_filtering_active.setText(self.ActiveLayer_name)
                self.dlg.ui.lineEdit_time_active.setText(self.ActiveLayer_name)
                # enable the checkBox_visualization_edit
                # Get the curretly selected feature

                if self.ActiveLayer.type() == 0: # is the active layer a vector layer?

                    # enable the checkboxes in the viz and rendering tabs
                    self.dlg.ui.checkBox_visualization_edit.setEnabled(True)
                    self.dlg.ui.checkBox_rendering_edit.setEnabled(True)
                    self.dlg.ui.checkBox_filtering_edit.setEnabled(True)
                    self.dlg.ui.checkBox_time_edit.setEnabled(True)
                    # export
                    if self.ActiveLayer.storageType() == 'ESRI Shapefile' and self.ActiveLayer.geometryType() == 0:
                        self.dlg.ui.lineEdit_export_audio.setEnabled(True)
                        if self.dlg.ui.lineEdit_InAudio1.text():
                            self.dlg.ui.lineEdit_export_audio.setText(self.dlg.ui.lineEdit_InAudio1.text())
                        else:
                            self.dlg.ui.lineEdit_export_audio.setText(None)
                        self.dlg.ui.pushButton_export_audio_file.setEnabled(True)
                        self.dlg.ui.buttonExportTrack.setEnabled(True)
                        self.dlg.ui.pushButton_TrackInfo.setEnabled(True)
                        self.dlg.ui.pushButton_sync.setEnabled(True)
                        #self.dlg.ui.pushButton_google_earth.setEnabled(True)
                    else:
                        self.dlg.ui.lineEdit_export_audio.setEnabled(False)
                        self.dlg.ui.pushButton_export_audio_file.setEnabled(False)
                        self.dlg.ui.buttonExportTrack.setEnabled(False)
                        self.dlg.ui.pushButton_TrackInfo.setEnabled(False)
                        self.dlg.ui.pushButton_google_earth.setEnabled(False)
                        self.dlg.ui.pushButton_sync.setEnabled(False)
                else:
                    self.dlg.ui.lineEdit_export_audio.setEnabled(False)
                    self.dlg.ui.pushButton_export_audio_file.setEnabled(False)
                    self.dlg.ui.buttonExportTrack.setEnabled(False)
                    self.dlg.ui.pushButton_TrackInfo.setEnabled(False)
                    self.dlg.ui.pushButton_google_earth.setEnabled(False)
                    self.dlg.ui.pushButton_sync.setEnabled(False)


            else:
                self.dlg.ui.lineEdit_tourname.setText(None)
                self.dlg.ui.lineEdit_flyto_duration.setText(None)
                self.dlg.ui.lineEdit_visualization_active.setText(None)
                self.dlg.ui.lineEdit_export_active.setText(None)
                self.dlg.ui.lineEdit_visualization_camera_longitude.setText(None)
                self.dlg.ui.lineEdit_visualization_camera_latitude.setText(None)
                self.dlg.ui.lineEdit_visualization_camera_altitude.setText(None)
                self.dlg.ui.lineEdit__visualization_camera_gxhoriz.setText(None)
                self.dlg.ui.lineEdit__visualization_camera_heading.setText(None)
                self.dlg.ui.lineEdit__visualization_camera_roll.setText(None)
                self.dlg.ui.lineEdit__visualization_camera_tilt.setText(None)

                #rendering
                # Label style
                self.dlg.ui.lineEdit_rendering_label_scale.setText(None)

                # Icon Style
                self.dlg.ui.lineEdit_rendering_icon_transparency.setText(None)
                self.dlg.ui.lineEdit_rendering_icon_scale.setText(None)
                self.dlg.ui.lineEdit_rendering_icon_heading.setText(None)
                self.dlg.ui.lineEdit_rendering_icon_icon.setText(None)
                self.dlg.ui.lineEdit_rendering_icon_hotspot.setText(None)


                # check box viz
                self.dlg.ui.checkBox_visualization_edit.setChecked(False)
                self.dlg.ui.checkBox_visualization_edit.setEnabled(False)
                self.dlg.ui.pushButton_camera_apply.setEnabled(False)
                self.dlg.ui.pushButton_visualization_camera_xy.setEnabled(False)

                # check box rendering
                self.dlg.ui.checkBox_rendering_edit.setChecked(False)
                self.dlg.ui.checkBox_rendering_edit.setEnabled(False)
                self.dlg.ui.pushButton_rendering_icon_apply.setEnabled(False)
                self.dlg.ui.pushButton_rendering_label_apply.setEnabled(False)

                # check box filtering
                self.dlg.ui.checkBox_filtering_edit.setChecked(False)
                self.dlg.ui.checkBox_filtering_edit.setEnabled(True)

                # check box time editing
                self.dlg.ui.checkBox_time_edit.setChecked(False)
                self.dlg.ui.checkBox_time_edit.setEnabled(True)

                #export
                self.dlg.ui.lineEdit_export_audio.setEnabled(False)
                self.dlg.ui.pushButton_export_audio_file.setEnabled(False)
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
            else:
                # Camera
                self.dlg.ui.lineEdit_visualization_camera_longitude.setEnabled(True)
                self.dlg.ui.lineEdit_visualization_camera_latitude.setEnabled(True)
                self.dlg.ui.lineEdit_visualization_camera_altitude.setEnabled(True)
                self.dlg.ui.comboBox_altitudemode.setEnabled(True)
                self.dlg.ui.comboBox_gxaltitudemode.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_camera_gxhoriz.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_camera_heading.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_camera_roll.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_camera_tilt.setEnabled(True)
                self.dlg.ui.lineEdit_visualization_camera_longitude_off.setEnabled(True)
                self.dlg.ui.lineEdit_visualization_camera_latitude_off.setEnabled(True)
                self.dlg.ui.pushButton_camera_apply.setEnabled(True)
                self.dlg.ui.pushButton_visualization_camera_xy.setEnabled(True)

                # Tour
                self.dlg.ui.lineEdit_tourname.setEnabled(True)

                # FlyTo
                self.dlg.ui.comboBox_flyto_mode.setEnabled(True)
                self.dlg.ui.lineEdit_flyto_duration.setEnabled(True)

                # Follow Behind
                self.dlg.ui.lineEdit_visualization_follow_altitude.setEnabled(True)
                self.dlg.ui.comboBox_follow_altitudemode.setEnabled(True)
                self.dlg.ui.comboBox_follow_gxaltitudemode.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_follow_gxhoriz.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_follow_tilt.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_follow_range.setEnabled(True)
                self.dlg.ui.pushButton_follow_apply.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_follow_follow_angle.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_follow_smoother.setEnabled(True)

        else:  # checkbox is false, clear shit out
            self.dlg.ui.lineEdit_tourname.setEnabled(False)
            self.dlg.ui.comboBox_flyto_mode.setEnabled(False)
            self.dlg.ui.lineEdit_flyto_duration.setEnabled(False)

            self.dlg.ui.lineEdit_visualization_camera_longitude.setEnabled(False)
            self.dlg.ui.lineEdit_visualization_camera_latitude.setEnabled(False)
            self.dlg.ui.lineEdit_visualization_camera_altitude.setEnabled(False)
            self.dlg.ui.comboBox_altitudemode.setEnabled(False)
            self.dlg.ui.comboBox_gxaltitudemode.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_camera_gxhoriz.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_camera_heading.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_camera_roll.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_camera_tilt.setEnabled(False)
            self.dlg.ui.lineEdit_visualization_camera_longitude_off.setEnabled(False)
            self.dlg.ui.lineEdit_visualization_camera_latitude_off.setEnabled(False)

            self.dlg.ui.pushButton_camera_apply.setEnabled(False)
            self.dlg.ui.pushButton_visualization_camera_xy.setEnabled(False)

            # Follow Behind
            self.dlg.ui.lineEdit_visualization_follow_altitude.setEnabled(False)
            self.dlg.ui.comboBox_follow_altitudemode.setEnabled(False)
            self.dlg.ui.comboBox_follow_gxaltitudemode.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_follow_gxhoriz.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_follow_tilt.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_follow_range.setEnabled(False)
            self.dlg.ui.pushButton_follow_apply.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_follow_follow_angle.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_follow_smoother.setEnabled(False)

    def camera_xy(self):
        xylist = []
        try:
            for f in self.ActiveLayer.selectedFeatures(): #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
                geom = f.geometry()
                coords = geom.asPoint() #(-75.1722,39.9659)
                xylist.append(coords)

            if len(xylist) == 1: #only 1 point selected
                self.dlg.ui.lineEdit_visualization_camera_longitude.setText(str(xylist[0][0]))
                self.dlg.ui.lineEdit_visualization_camera_latitude.setText(str(xylist[0][1]))
            else:
                QMessageBox.warning( self.iface.mainWindow(),"xy Button Warning", "Please select 1 point when using the xy button." )
        except:
            self.logger.error('camera_xy function error')
            self.logger.exception(traceback.format_exc())
            self.iface.messageBar().pushMessage("Error", "Failed to apply coordinates to camera long/lat. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


    def camera_apply(self):

        try:

            self.fields = self.field_indices(self.ActiveLayer)
            # make a dictionary of all of the camera parameters
            camera = {'longitude': None, 'longitude_off': None, 'latitude': None, 'latitude_off': None, 'altitude' : None, 'altitudemode': None,'gxaltitudemode' : None,'gxhoriz' : None,'heading' : None,'roll' : None,'tilt' : None, 'range': None}
            flyto = {'name': None, 'flyToMode': None, 'duration': None}


            flyto['name'] = self.dlg.ui.lineEdit_tourname.text()
            flyto['flyToMode'] = self.dlg.ui.comboBox_flyto_mode.currentText()
            flyto['duration'] = self.dlg.ui.lineEdit_flyto_duration.text()


            camera['longitude'] = self.dlg.ui.lineEdit_visualization_camera_longitude.text()
            camera['longitude_off'] = self.dlg.ui.lineEdit_visualization_camera_longitude_off.text()
            camera['latitude'] = self.dlg.ui.lineEdit_visualization_camera_latitude.text()
            camera['latitude_off'] = self.dlg.ui.lineEdit_visualization_camera_latitude_off.text()
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
                        self.ActiveLayer.changeAttributeValue(f, self.fields['camera'], str(camera))
                        self.ActiveLayer.changeAttributeValue(f, self.fields['flyto'], str(flyto))
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
        if self.gpsfile:
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
                shapepath_line = self.gpsfile.split(".")[0] + '_line.shp'
                shapepath_dup = self.gpsfile.split(".")[0] + '_duplicate.shp'


                QgsVectorFileWriter.writeAsVectorFormat(kmllayer, shapepath, "utf-8", None, "ESRI Shapefile")  # working copy
                QgsVectorFileWriter.writeAsVectorFormat(kmllayer, shapepath_dup, "utf-8", None, "ESRI Shapefile")  # duplicate of original
                #bring the shapefile back in, and render it on the map
                shaper = QgsVectorLayer(shapepath, layername, "ogr")
                shaper.dataProvider().addAttributes( [QgsField("datetime",QVariant.String), QgsField("audio",QVariant.String), QgsField("camera",QVariant.String), QgsField("flyto",QVariant.String), QgsField("iconstyle", QVariant.String), QgsField("labelstyle", QVariant.String), QgsField("model", QVariant.String) ] )
                shaper.updateFields()


                self.fields = self.field_indices(shaper)


##                self.fields['Name'] = shaper.fieldNameIndex('Name')
##                self.fields['Description'] = shaper.fieldNameIndex('Description')
##                self.fields['datetime'] = shaper.fieldNameIndex('datetime')
##                self.fields['audio'] = shaper.fieldNameIndex('audio')
##                self.fields['camera'] = shaper.fieldNameIndex('camera')
##                self.fields['flyto'] = shaper.fieldNameIndex('flyto')
##                self.fields['iconstyle'] = shaper.fieldNameIndex('iconstyle')
##                self.fields['labelstyle'] = shaper.fieldNameIndex('labelstyle')
##                self.fields['model'] = shaper.fieldNameIndex('model')


                # calculate the datetime field
                idx = self.fields['datetime']  #feature.attributes()[idx]
                fid_dt = []
                cc = 0
                for f in shaper.getFeatures():
                    currentatt = f.attributes()[0]
                    pointdate = currentatt.split(" ")[0]  #2014/06/06
                    pointtime = currentatt.split(" ")[1]
                    current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
                    fid_dt.append(current_dt.strftime("%Y/%m/%d %X"))
##                    dt = current_dt.strftime("%Y/%m/%d %X")
##                    attrs = {idx : dt}
##                    shaper.dataProvider().changeAttributeValues({ cc : attrs })
                    cc += 1

##                self.ActiveLayer.beginEditCommand("Rendering Editing")
##                if len(self.selectList) >= 1:
##                    self.ActiveLayer.beginEditCommand("Rendering Editing")
##                    for f in self.selectList:
##                        self.ActiveLayer.changeAttributeValue(f, self.fields['model'], str(model))
##                    self.ActiveLayer.updateFields()
##                    self.ActiveLayer.endEditCommand()

##                for i,v in enumerate(fid_dt):
##                    attrs = {idx : v}
##                    shaper.dataProvider().changeAttributeValues({ i : attrs })

                shaper.startEditing()
                shaper.beginEditCommand('datetime')
                for i,v in enumerate(fid_dt):
                    shaper.changeAttributeValue(i, idx, v)
                shaper.endEditCommand()
                shaper.commitChanges()


                # make the line shapefile
                ptlist = []
                for f in shaper.getFeatures():
                    ptlist.append(f.geometry().asPoint())
                linelayer = QgsVectorLayer("LineString?crs=EPSG:4326", layername, "memory")
                pr = linelayer.dataProvider()
                seg = QgsFeature()
                seg.setGeometry(QgsGeometry.fromPolyline(ptlist))
                pr.addFeatures([seg])
                QgsVectorFileWriter.writeAsVectorFormat(linelayer, shapepath_line, "utf-8", None, "ESRI Shapefile")
                shaper_line = QgsVectorLayer(shapepath_line, layername, "ogr")


                # define the layer properties as a dict
                properties = {'size': '3.0'}
                # initalise a new symbol layer with those properties
                symbol_layer = QgsSimpleMarkerSymbolLayerV2.create(properties)
                # replace the default symbol layer with the new symbol layer
                shaper.rendererV2().symbols()[0].changeSymbolLayer(0, symbol_layer)
                shaper.commitChanges()

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
                    self.dlg.ui.checkBox_headoftrack.setCheckState(0)

                QgsMapLayerRegistry.instance().addMapLayer(shaper_line)
                QgsMapLayerRegistry.instance().addMapLayer(shaper)
                self.canvas.setExtent(shaper.extent())
                self.canvas.refresh()
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
        if self.audiopath:
            self.lastdirectory = os.path.dirname(self.audiopath)
            self.dlg.ui.lineEdit_export_audio.setText(self.audiopath)
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

        if NOW and pointid >=0 and ClockDateTime:
            try:

                # check if the time difference is larger than 1 between points

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

                if self.dlg.ui.checkBox_import_indicator.isChecked():
                    features = self.cLayer.selectedFeatures()
                    selxy = ()
                    for f in features:
                        geom = f.geometry()
                        selxy = geom.asPoint()

                    pr = self.audioselect_layer.dataProvider()
                    # add a feature
                    fet = QgsGeometry.fromPoint(QgsPoint(selxy[0],selxy[1]))
                    self.audioselect_layer.startEditing()
                    self.audioselect_layer.beginEditCommand('selected')
                    self.audioselect_layer.changeGeometry(0,fet)
    ##                self.audioselect_layer.endEditCommand()
    ##                self.audioselect_layer.commitChanges()
                self.canvas.refresh()
                self.canvas.zoomToSelected()

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
            self.dlg.ui.pushButton_Audio1.setEnabled(False)
            self.line_audiopath = self.dlg.ui.lineEdit_InAudio1.text()
            if self.audiopath and self.line_audiopath:
                #self.audio_start = None
                #self.audio_end = None
                global NOW, pointid, ClockDateTime



                # Get the curretly selected feature
                self.cLayer = self.iface.mapCanvas().currentLayer()
                self.fields = self.field_indices(self.cLayer)
                selectList = []
                try:
                    features = self.cLayer.selectedFeatures()
                    for f in features:
                        selectList.append(f.attributes())   #[u'2014/06/06 10:30:10', u'Time:10:30:10, Latitude: 39.966531, Longitude: -75.172003, Speed: 3.382047, Altitude: 1.596764']
                        fid = f.id()
                except AttributeError:
                    QMessageBox.warning( self.iface.mainWindow(),"Selected Layer Warning", "Please select the layer and starting point where you would like the audio to start." )

                if len(selectList) == 1:
                    self.logger.info('IN selectList: {0}'.format(selectList))
                    pointid = fid
                    pointdate = selectList[0][self.fields['datetime']].split(" ")[0]  #2014/06/06
                    pointtime = selectList[0][self.fields['datetime']].split(" ")[1]  #10:30:10

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

                    if jumptime >= 0 and ClockDateTime:
                        # "C:\Program Files (x86)\VideoLAN\VLC\vlc.exe" file:///C:/Users/Edward/Documents/Philly250/Scratch/Nagra01-0003.WAV --start-time 5
                        #stime = 5
                        self.logger.info('IN jumptime: {0}, ClockDateTime'.format(jumptime, ClockDateTime))
                        wav_path = "file:///" + self.line_audiopath
                        lan_vlc_path = "C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
                        #startupinfo = subprocess.STARTUPINFO()
                        #startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        UserOs = platform.platform()
                        WindOs = re.search('Windows', UserOs, re.I)
                        self.logger.info('WindOs: {0}'.format(WindOs))
                        if WindOs:
                            if WindOs.group() == 'Windows':
                                self.pp = subprocess.Popen(["C:/Program Files (x86)/VideoLAN/VLC/vlc.exe", wav_path, "--start-time", str(jumptime)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        else:
                            self.pp = subprocess.Popen(["/Applications/VLC.app/Contents/MacOS/VLC", self.line_audiopath, "--start-time", str(jumptime)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                        #-----------
                        # make a marker to hover over the selected point
                        if self.dlg.ui.checkBox_import_indicator.isChecked():
                            toclayers = self.canvas.layers()
                            pres = False
                            for i,l in enumerate(toclayers):
                                if l.name() == 'Selected Point':
                                    pres = True
                                    self.audioselect_layer = toclayers[i]
                            if pres == False:
                                self.audioselect_layer = QgsVectorLayer("Point?crs=EPSG:4326", 'Selected Point', "memory")
                                pr = self.audioselect_layer.dataProvider()
                                fet = QgsFeature()
                                fet.setGeometry( QgsGeometry.fromPoint(QgsPoint(-75,40)) )
                                pr.addFeatures([fet])
                                properties = {'size': '6', 'color': '255,255,0,255'}
                                symbol_layer = QgsSimpleMarkerSymbolLayerV2.create(properties)
                                self.audioselect_layer.rendererV2().symbols()[0].changeSymbolLayer(0, symbol_layer)
                                self.audioselect_layer.setLayerTransparency(30)
                                self.audioselect_layer.commitChanges()
                                QgsMapLayerRegistry.instance().addMapLayer(self.audioselect_layer)



                        NOW = datetime.datetime.now()
                        self.dlg.timer.start(1000)

                        #stdout, stderr = pp.communicate()
                    self.logger.info('jumptime: {0}, ClockDateTime'.format(jumptime, ClockDateTime))
                else:
                    self.logger.info('Out selectList: {0}'.format(selectList))

        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('playaudio function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Play audio error. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

    def stopAudio1(self):
        try:
            self.dlg.ui.pushButton_Audio1.setEnabled(True)
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            try:
                self.pp.terminate()
                self.dlg.timer.stop()
            except:
                try:
                    self.audioselect_layer.endEditCommand()
                except:
                    pass
            #self.audioselect_layer.commitChanges()
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
                if not self.aLayer:
                    QMessageBox.warning(self.iface.mainWindow(),"Audio File Sync Error", 'Please select a layer in the table of contents')

                else:

                    self.fields = self.field_indices(self.aLayer)
                    matchdict = {}
                    cc = 0
                    try:

                        for f in self.aLayer.getFeatures(): #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
                            currentatt = f.attributes()
                            pointdate = currentatt[self.fields['datetime']].split(" ")[0]  #2014/06/06
                            pointtime = currentatt[self.fields['datetime']].split(" ")[1]
                            current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
                            if cc == 0:
                                track_start_dt = current_dt
                                if current_dt == self.audio_start:
                                    self.aLayer.setSelectedFeatures([int(f.id())])
                                    matchdict['fid'] = f.id()
                                    matchdict['attributes'] = currentatt
                                    geom = f.geometry()  # QgsGeometry object, get the geometry
                                    if geom.type() == QGis.Point:
                                        matchdict['coordinates'] = geom.asPoint() #(-75.1722,39.9659)
                                    break
                                elif current_dt > self.audio_start: # if it is the first attribute and there is no match and the track time is larger than the start of the audio.
                                    diff = current_dt - self.audio_start
                                    QMessageBox.information(self.iface.mainWindow(),"Audio File Sync Info", 'Audio starts before the begining of the track by {0}'.format(diff) )
                                    break
                            elif current_dt == self.audio_start: # the track time and the audio start match
                                self.aLayer.setSelectedFeatures([int(f.id())])
                                matchdict['fid'] = f.id()
                                matchdict['attributes'] = currentatt
                                geom = f.geometry()  # QgsGeometry object, get the geometry
                                if geom.type() == QGis.Point:
                                    matchdict['coordinates'] = geom.asPoint() #(-75.1722,39.9659)
                                break
                            cc += 1

                        # calculate the audio field
                        try:
                            idx = self.aLayer.fieldNameIndex('audio')  #feature.attributes()[idx]
                            fid_dt = []
                            cc = 0
                            self.aLayer.startEditing()
                            self.aLayer.beginEditCommand('audio sync')
                            for f in self.aLayer.getFeatures():
                                currentatt = f.attributes()
                                pointdate = currentatt[self.fields['datetime']].split(" ")[0]  #2014/06/06
                                pointtime = currentatt[self.fields['datetime']].split(" ")[1]
                                current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
                                if current_dt >= self.audio_start and current_dt <= self.audio_end:
                                    self.aLayer.changeAttributeValue(cc, idx, '1')
                                else:
                                    self.aLayer.changeAttributeValue(cc, idx, '0')
                                cc += 1
                            self.aLayer.endEditCommand()
                            self.aLayer.commitChanges()


                        except:
                            self.aLayer.destroyEditCommand()
                            self.logger.error('audio sync field destroy edit session')
                            self.logger.exception(traceback.format_exc())
                            self.iface.messageBar().pushMessage("Error", "Failed to apply audio category values. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)





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
                        properties = {'size': str(size2), 'color': '0,0,255,255'}

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
                        self.iface.setActiveLayer(self.aLayer)

                    #QMessageBox.information(self.iface.mainWindow(),"Audio File Info", str(self.audio_start) )
        except:
            trace = traceback.format_exc()
            self.logger.error('sync function error. row ')
            self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Sync button error. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)



    ############################################################################
    ############################################################################
    ## Export and Details
    ############################################################################

    def audio_offset(self, audiopath):
        # Audio Start and End
        audioname_ext = audiopath.split('/')[-1]
        audioname = audioname_ext.split('.')[0]
        # Audio start date and time
        w = wave.open(audiopath)
        # Frame Rate of the Wave File
        framerate = w.getframerate()
        # Number of Frames in the File
        frames = w.getnframes()
        # Estimate length of the file by dividing frames/framerate
        length = frames/framerate # seconds
        audio_start = datetime.datetime(int(audioname[0:4]), int(audioname[4:6]), int(audioname[6:8]), int(audioname[8:10]), int(audioname[10:12]), int(audioname[12:14]))
        # Audio end time. Add seconds to the start time
        audio_end = audio_start + datetime.timedelta(seconds=length)

        # Track start and end
        cc = 0
        for f in self.ActiveLayer.getFeatures(): #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
            currentatt = f.attributes()
            pointdate = currentatt[self.fields['datetime']].split(" ")[0]  #2014/06/06
            pointtime = currentatt[self.fields['datetime']].split(" ")[1] #10:38:48
            if cc == 0:
                track_dt_start = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
            else:
                track_dt_end = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
            cc += 1

        if audio_start >= track_dt_start:  #and audio_end <= track_dt_end
            diff = audio_start - track_dt_start
            return diff.seconds
            #self.audio_delay = diff.seconds

    def file_export_audio(self):
        try:
            self.ActiveLayer = self.iface.activeLayer()
            if self.ActiveLayer:
                self.fields = self.field_indices(self.ActiveLayer)
                self.audio_export = QFileDialog.getOpenFileName(None, "Choose .wav file for .kmz export", self.lastdirectory, "*.wav")  #C:\Users\Edward\Documents\Philly250\Scratch
                if self.audio_export:
                    self.lastdirectory = os.path.dirname(self.audio_export)

                if self.audio_export:
                    # Audio Start and End
                    audioname_ext = self.audio_export.split('/')[-1]
                    audioname = audioname_ext.split('.')[0]
                    # Audio start date and time
                    w = wave.open(self.audio_export)
                    # Frame Rate of the Wave File
                    framerate = w.getframerate()
                    # Number of Frames in the File
                    frames = w.getnframes()
                    # Estimate length of the file by dividing frames/framerate
                    length = frames/framerate # seconds
                    audio_start = datetime.datetime(int(audioname[0:4]), int(audioname[4:6]), int(audioname[6:8]), int(audioname[8:10]), int(audioname[10:12]), int(audioname[12:14]))
                    # Audio end time. Add seconds to the start time
                    audio_end = audio_start + datetime.timedelta(seconds=length)

                    # Track start and end
                    cc = 0
                    for f in self.ActiveLayer.getFeatures(): #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
                        currentatt = f.attributes()
                        pointdate = currentatt[self.fields['datetime']].split(" ")[0]  #2014/06/06
                        pointtime = currentatt[self.fields['datetime']].split(" ")[1] #10:38:48
                        if cc == 0:
                            track_dt_start = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
                        else:
                            track_dt_end = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
                        cc += 1

                    if audio_start >= track_dt_start:  #and audio_end <= track_dt_end
                        self.dlg.ui.lineEdit_export_audio.setText(self.audio_export)
                        diff = audio_start - track_dt_start
                        self.audio_delay = diff.seconds
                    else:
                        QMessageBox.warning(self.iface.mainWindow(),"Audio Export Warning", "The audio time does not fall within the start and end time of the GPS track.\nAudio Start: {0}\nAudio End: {1}\nTrack Start: {2}\nTrack End: {3}".format(audio_start.strftime("%x %X"),audio_end.strftime("%x %X"),track_dt_start.strftime("%x %X"),track_dt_end.strftime("%x %X")) )
        except:
            self.logger.error('file_export_audio error')
            self.logger.exception(traceback.format_exc())
            self.iface.messageBar().pushMessage("Error", "Failed to import audio file. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


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
            self.utmzone = 26918 #UTM 18N
            cc = 0
            kml = simplekml.Kml()

            self.fields = self.field_indices(self.ActiveLayer)

            self.logger.info(self.fields)
            #################################
            ## Tour and Camera

            for f in self.ActiveLayer.getFeatures(): #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
                currentatt = f.attributes()

                if currentatt[self.fields['camera']]:
                        # camera = {'longitude': None, 'longitude_off': None, 'latitude': None, 'latitude_off': None,
                        # 'altitude' : None, 'altitudemode': None,'gxaltitudemode' : None,'gxhoriz' : None,
                        # 'heading' : None,'roll' : None,'tilt' : None}

                    if cc == 0:  # establish this as the start of the tour
                        cameradict = eval(currentatt[self.fields['camera']])
                        flytodict = eval(currentatt[self.fields['flyto']])

                        # First, put in a <Camera> that matches the same <Camera> at the beginning of the tour, that
                        # there is no strange camera movement at the beginning.

                        #firstcam_pnt = kml.newpoint()
                        kml.document.camera = simplekml.Camera()


                        # Create a tour and attach a playlist to it
                        if flytodict['name']:
                            tour = kml.newgxtour(name=flytodict['name'])
                        else:
                            tour = kml.newgxtour(name="Tour")

                        playlist = tour.newgxplaylist()

                        # Start time. Will be used for TimeSpan tags
                        pointdate = currentatt[self.fields['datetime']].split(" ")[0]  #2014/06/06
                        pointtime = currentatt[self.fields['datetime']].split(" ")[1] #10:38:48
                        current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]) )
                        current_dt_end = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]) ) #+ datetime.timedelta(seconds=5)
                        CamStartTime = current_dt.strftime('%Y-%m-%dT%XZ')
                        camendtime = current_dt_end.strftime('%Y-%m-%dT%XZ')


                        # Attach a gx:SoundCue to the playlist and delay playing by 2 second (sound clip is about 4 seconds long)
                        if self.dlg.ui.lineEdit_export_audio.text():
                            soundcue = playlist.newgxsoundcue()
                            soundcue.href = self.dlg.ui.lineEdit_export_audio.text()
                            soundcue.gxdelayedstart = self.audio_offset(self.dlg.ui.lineEdit_export_audio.text())


                        if flytodict['duration']:
                            flyto = playlist.newgxflyto(gxduration=float(flytodict['duration']))
                        else:
                            flyto = playlist.newgxflyto()
                        if flytodict['flyToMode']:
                            flyto.gxflytomode = flytodict['flyToMode']




                        if cameradict['longitude'] and cameradict['latitude']:
                            if cameradict['longitude_off'] or cameradict['latitude_off']: # If there is an offset

                                crsSrc = QgsCoordinateReferenceSystem(4326)    # WGS 84
                                crsDest = QgsCoordinateReferenceSystem(self.utmzone)  # WGS 84 / UTM zone
                                xform = QgsCoordinateTransform(crsSrc, crsDest)
                                xform2 = QgsCoordinateTransform(crsDest, crsSrc)

                                utmpt = xform.transform(QgsPoint(float(cameradict['longitude']),float(cameradict['latitude'])))
                                utmptlist = [utmpt[0], utmpt[1]]
                                # now add the utm point to the new feature
                                if cameradict['longitude_off']:
                                    utmptlist[0] = float(utmpt[0]) + float(cameradict['longitude_off'])
                                if cameradict['latitude_off']:
                                    utmptlist[1] = float(utmpt[1]) + float(cameradict['latitude_off'])

                                offsetpt = xform2.transform(QgsPoint(utmptlist[0],utmptlist[1]))

                                #firstcam_pnt.camera.longitude = offsetpt[0]
                                #firstcam_pnt.camera.latitude = offsetpt[1]

                                flyto.camera.longitude = offsetpt[0]
                                flyto.camera.latitude = offsetpt[1]

                            elif cameradict['range'] and cameradict['heading'] and cameradict['altitude']:
                                import math
                                crsSrc = QgsCoordinateReferenceSystem(4326)    # WGS 84
                                crsDest = QgsCoordinateReferenceSystem(self.utmzone)  # WGS 84 / UTM zone
                                xform = QgsCoordinateTransform(crsSrc, crsDest)
                                xform2 = QgsCoordinateTransform(crsDest, crsSrc)

                                utmpt = xform.transform(QgsPoint(float(cameradict['longitude']),float(cameradict['latitude'])))
                                utmptlist = [utmpt[0], utmpt[1]]  # x,y utm

                                if cameradict['follow_angle']:
                                    follow_angle = math.radians(float(cameradict['follow_angle']))
                                    # now you need to change heading. It should be rotated
                                else:
                                    follow_angle = math.pi
                                opp_rad = (math.radians(float(cameradict['heading'])) + follow_angle) % (2*math.pi) #opposite angle in radians
                                #leg_distance = float(cameradict['range']) * sin(float(cameradict['tilt']))

                                if cameradict['altitudemode'] == 'relativeToModel':
                                    modeldict = eval(currentatt[self.fields['model']])
                                    camaltitude = float(cameradict['altitude']) - float(modeldict['altitude'])
                                else:
                                    camaltitude = float(cameradict['altitude'])

                                leg_distance = math.sqrt( float(cameradict['range'])**2 - camaltitude**2 ) # horizontal distance between the camera at altiduce and the range
                                heading_rad = math.radians(float(cameradict['heading']))
                                x_dist = math.sin(opp_rad) * leg_distance
                                y_dist = math.cos(opp_rad) * leg_distance


##                                self.logger.info('opp_rad {0}'.format(math.degrees(opp_rad)))
##                                self.logger.info('heading_rad {0}'.format(math.degrees(heading_rad)))
##                                self.logger.info('range {0}'.format(cameradict['range']))
##                                self.logger.info('altitude {0}'.format(cameradict['altitude']))
##                                self.logger.info('xdist {0}'.format(x_dist))
##                                self.logger.info('ydist {0}'.format(y_dist))

                                utm_camera = ((utmpt[0] + x_dist), (utmpt[1] + y_dist))
                                wgs_camera = xform2.transform(QgsPoint(utm_camera[0], utm_camera[1]))

                                flyto.camera.longitude = wgs_camera[0]
                                flyto.camera.latitude = wgs_camera[1]

                                # camera tilt


                            else:
                                flyto.camera.longitude = cameradict['longitude']
                                flyto.camera.latitude = cameradict['latitude']
##                        if cameradict['latitude']:
##                            ifcameradict['latitude_off']:
##                                pass
##                            else:
##                                flyto.camera.latitude = cameradict['latitude']
                        if cameradict['altitude']:
                            flyto.camera.altitude = cameradict['altitude']
                        if cameradict['altitudemode']:
                            if cameradict['altitudemode'] == 'absolute':
                                flyto.camera.altitudemode = simplekml.AltitudeMode.absolute
                            if cameradict['altitudemode'] == 'clampToGround':
                                flyto.camera.altitudemode = simplekml.AltitudeMode.clamptoground
                            if cameradict['altitudemode'] == 'relativeToGround':
                                flyto.camera.altitudemode = simplekml.AltitudeMode.relativetoground
                            if cameradict['altitudemode'] == 'relativeToPoint':
                                flyto.camera.altitudemode = simplekml.AltitudeMode.relativetoground
                            if cameradict['altitudemode'] == 'relativeToModel':
                                flyto.camera.altitudemode = simplekml.AltitudeMode.relativetoground

##                        if cameradict['altitude']:
##                            if cameradict['altitudemode'] == 'relativeToPoint':
##                                flyto.camera.altitude = cameradict['altitude'] +
##                            if cameradict['altitudemode'] == 'relativeToModel':
##
##                                flyto.camera.altitude = cameradict['altitude'] +
##
##                                loc.altitude = currentatt[self.fields['Descriptio']].split(",")[4].split(': ')[1]  #u'-3.756733'

                        if cameradict['gxaltitudemode']:
                            if cameradict['gxaltitudemode'] == 'clampToSeaFloor':
                                flyto.camera.gxaltitudemode = simplekml.GxAltitudeMode.clampToSeaFloor
                            if cameradict['gxaltitudemode'] == 'relativeToSeaFloor':
                                flyto.camera.gxaltitudemode = simplekml.GxAltitudeMode.relativetoseafloor
                        if cameradict['gxhoriz']:
                            flyto.camera.gxhoriz = cameradict['gxhoriz']
                        if cameradict['heading']:
                            if cameradict['follow_angle']:
                                newhead = math.degrees((math.radians(float(cameradict['heading'])) + follow_angle + math.pi) % (2 * math.pi))
                                flyto.camera.heading = newhead
                            else:
                                flyto.camera.heading = cameradict['heading']
                        if cameradict['roll']:
                            flyto.camera.roll = cameradict['roll']
                        if cameradict['tilt']:
                            flyto.camera.tilt = cameradict['tilt']

                        # Time Span
                        flyto.camera.gxtimespan.begin = CamStartTime
                        flyto.camera.gxtimespan.end = camendtime


                        #firstcam_pnt.camera = flyto.camera
                        kml.document.camera = flyto.camera

                        cc += 1

                    else:  # everything after zero camera
                        cameradict = eval(currentatt[self.fields['camera']])
                        flytodict = eval(currentatt[self.fields['flyto']])

                        # Start time. Will be used for TimeSpan tags
                        pointdate = currentatt[self.fields['datetime']].split(" ")[0]  #2014/06/06
                        pointtime = currentatt[self.fields['datetime']].split(" ")[1] #10:38:48
                        current_dt_end = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))# + datetime.timedelta(seconds=5)
                        camendtime = current_dt_end.strftime('%Y-%m-%dT%XZ')

                        if flytodict['duration']:
                            flyto = playlist.newgxflyto(gxduration=float(flytodict['duration']))
                        else:
                            flyto = playlist.newgxflyto()
                        if flytodict['flyToMode']:
                            flyto.gxflytomode = flytodict['flyToMode']

                        if cameradict['longitude'] and cameradict['latitude']:
                            if cameradict['longitude_off'] or cameradict['latitude_off']: # If there is an offset

                                crsSrc = QgsCoordinateReferenceSystem(4326)    # WGS 84
                                crsDest = QgsCoordinateReferenceSystem(self.utmzone)  # WGS 84 / UTM zone
                                xform = QgsCoordinateTransform(crsSrc, crsDest)
                                xform2 = QgsCoordinateTransform(crsDest, crsSrc)

                                utmpt = xform.transform(QgsPoint(float(cameradict['longitude']),float(cameradict['latitude'])))
                                utmptlist = [utmpt[0], utmpt[1]]
                                # now add the utm point to the new feature
                                if cameradict['longitude_off']:
                                    utmptlist[0] = float(utmpt[0]) + float(cameradict['longitude_off'])
                                if cameradict['latitude_off']:
                                    utmptlist[1] = float(utmpt[1]) + float(cameradict['latitude_off'])

                                offsetpt = xform2.transform(QgsPoint(utmptlist[0],utmptlist[1]))

                                flyto.camera.longitude = offsetpt[0]
                                flyto.camera.latitude = offsetpt[1]

                            elif cameradict['range'] and cameradict['heading'] and cameradict['altitude']:
                                import math
                                crsSrc = QgsCoordinateReferenceSystem(4326)    # WGS 84
                                crsDest = QgsCoordinateReferenceSystem(self.utmzone)  # WGS 84 / UTM zone
                                xform = QgsCoordinateTransform(crsSrc, crsDest)
                                xform2 = QgsCoordinateTransform(crsDest, crsSrc)

                                utmpt = xform.transform(QgsPoint(float(cameradict['longitude']),float(cameradict['latitude'])))
                                utmptlist = [utmpt[0], utmpt[1]]  # x,y utm

                                if cameradict['follow_angle']:
                                    follow_angle = math.radians(float(cameradict['follow_angle']))
                                else:
                                    follow_angle = math.pi
                                opp_rad = (math.radians(float(cameradict['heading'])) + follow_angle) % (2*math.pi) #opposite angle in radians from the heading. So you can calculate the direction whre the camerea should be placed

                                if cameradict['altitudemode'] == 'relativeToModel':
                                    modeldict = eval(currentatt[self.fields['model']])
                                    camaltitude = float(cameradict['altitude']) - float(modeldict['altitude'])
                                else:
                                    camaltitude = float(cameradict['altitude'])
                                leg_distance = math.sqrt( float(cameradict['range'])**2 - camaltitude**2 ) # horizontal distance between the camera at altiduce and the range


                                #leg_distance = math.sqrt( float(cameradict['range'])**2 - float(cameradict['altitude'])**2 ) # horizontal distance between the camera at altiduce and the range
                                heading_rad = math.radians(float(cameradict['heading']))
                                x_dist = math.sin(opp_rad) * leg_distance
                                y_dist = math.cos(opp_rad) * leg_distance

##                                self.logger.info('-----------------------')
##                                self.logger.info('model xy {0}'.format((float(cameradict['longitude']),float(cameradict['latitude']))))
##                                self.logger.info('utmptlist {0}'.format(utmptlist))
##                                self.logger.info('opp_rad {0}'.format(math.degrees(opp_rad)))
##                                self.logger.info('heading_rad {0}'.format(math.degrees(heading_rad)))
##                                self.logger.info('range {0}'.format(cameradict['range']))
##                                self.logger.info('altitude {0}'.format(cameradict['altitude']))
##                                self.logger.info('xdist {0}'.format(x_dist))
##                                self.logger.info('ydist {0}'.format(y_dist))
##                                self.logger.info('utm_camera {0}'.format(utm_camera))

                                utm_camera = ((utmpt[0] + x_dist), (utmpt[1] + y_dist))
                                wgs_camera = xform2.transform(QgsPoint(utm_camera[0], utm_camera[1]))

                                #self.logger.info('wgs xy {0}'.format(wgs_camera))
                                flyto.camera.longitude = wgs_camera[0]
                                flyto.camera.latitude = wgs_camera[1]

                                # camera tilt


                            else:
                                flyto.camera.longitude = cameradict['longitude']
                                flyto.camera.latitude = cameradict['latitude']
                        if cameradict['altitude']:
                            flyto.camera.altitude = cameradict['altitude']
                        if cameradict['altitudemode']:
                            if cameradict['altitudemode'] == 'absolute':
                                flyto.camera.altitudemode = simplekml.AltitudeMode.absolute
                            if cameradict['altitudemode'] == 'clampToGround':
                                flyto.camera.altitudemode = simplekml.AltitudeMode.clamptoground
                            if cameradict['altitudemode'] == 'relativeToGround':
                                flyto.camera.altitudemode = simplekml.AltitudeMode.relativetoground
                            if cameradict['altitudemode'] == 'relativeToPoint':
                                flyto.camera.altitudemode = simplekml.AltitudeMode.relativetoground
                            if cameradict['altitudemode'] == 'relativeToModel':
                                flyto.camera.altitudemode = simplekml.AltitudeMode.relativetoground
                        if cameradict['gxaltitudemode']:
                            if cameradict['gxaltitudemode'] == 'clampToSeaFloor':
                                flyto.camera.gxaltitudemode = simplekml.GxAltitudeMode.clampToSeaFloor
                            if cameradict['gxaltitudemode'] == 'relativeToSeaFloor':
                                flyto.camera.gxaltitudemode = simplekml.GxAltitudeMode.relativetoseafloor
                        if cameradict['gxhoriz']:
                            flyto.camera.gxhoriz = cameradict['gxhoriz']
                        if cameradict['heading']:
                            if cameradict['follow_angle']:
                                newhead = math.degrees((math.radians(float(cameradict['heading'])) + follow_angle + math.pi) % (2 * math.pi))
                                flyto.camera.heading = newhead
                            else:
                                flyto.camera.heading = float(cameradict['heading'])
                        if cameradict['roll']:
                            flyto.camera.roll = float(cameradict['roll'])
                        if cameradict['tilt']:
                            flyto.camera.tilt = float(cameradict['tilt'])

                        # Time Span
                        flyto.camera.gxtimespan.begin = CamStartTime
                        flyto.camera.gxtimespan.end = camendtime

                        cc += 1

                    #kml.document.camera = simplekml.Camera()
                    #kml.document.camera = flyto.camera
            ###############################3
            ## Points
            cc = 0
            folder = kml.newfolder(name='Points')
            for f in self.ActiveLayer.getFeatures(): #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
                geom = f.geometry()
                coords = geom.asPoint() #(-75.1722,39.9659)
                currentatt = f.attributes()

                if currentatt[self.fields['iconstyle']]:

                    pointdate = currentatt[self.fields['datetime']].split(" ")[0]  #2014/06/06
                    pointtime = currentatt[self.fields['datetime']].split(" ")[1] #10:38:48
                    current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))

                    pnt = folder.newpoint(name=str(cc), coords=[(coords[0], coords[1])], description=str(currentatt[1]))
                    pnt.timestamp.when = current_dt.strftime('%Y-%m-%dT%XZ')

                    def transtokmlhex(trans):
                        dec = int(float(icondict['transparency']) * 2.55)
                        if dec < 10:
                            return '0' + str(dec)
                        else:
                            return str(hex(dec)[2:4])

                # Icon Style
                # icon = {'color': None, 'colormode': None,'scale' : None, 'heading': None,'icon' : None ,'hotspot' : None}
                #if currentatt[self.fields['iconstyle']]:
                    icondict = eval(currentatt[self.fields['iconstyle']])

                    if icondict['color']:
                        pnt.style.iconstyle.color = simplekml.Color.__dict__[icondict['color']]
                    if icondict['color'] and icondict['transparency']:
                        transvalue = transtokmlhex(icondict['transparency'])
                        colorpick = simplekml.Color.__dict__[icondict['color']]
                        pnt.style.iconstyle.color = transvalue + colorpick[2:8]
                    if icondict['colormode']:
                        pnt.style.iconstyle.colormode = icondict['colormode']
                    if icondict['scale']:
                        pnt.style.iconstyle.scale = icondict['scale']
                    if icondict['heading']:
                        pnt.style.iconstyle.heading = icondict['heading']
                    if icondict['icon']:
                        pnt.style.iconstyle.icon.href = icondict['icon']


                    # Label Style
                    # label = {'color': None, 'colormode': None,'scale' : None}
                    if currentatt[self.fields['labelstyle']]:
                        labeldict = eval(currentatt[self.fields['labelstyle']])
                        if labeldict['color']:
                            pnt.style.labelstyle.color = simplekml.Color.__dict__[labeldict['color']]
                        if labeldict['colormode']:
                            pnt.style.labelstyle.colormode = labeldict['colormode']
                        if labeldict['scale']:
                            pnt.style.labelstyle.scale = labeldict['scale']

                cc += 1

            ###############################3
            ## Models
            cc = 0
            mfolder = kml.newfolder(name='Models')
            for f in self.ActiveLayer.getFeatures(): #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
                geom = f.geometry()
                coords = geom.asPoint() #(-75.1722,39.9659)
                currentatt = f.attributes()

                if currentatt[self.fields['model']]:

                    mdl = mfolder.newmodel()

                    pointdate = currentatt[self.fields['datetime']].split(" ")[0]  #2014/06/06
                    pointtime = currentatt[self.fields['datetime']].split(" ")[1] #10:38:48
                    current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))

                    #pnt = folder.newpoint(name=str(cc), coords=[(coords[0], coords[1])], description=str(currentatt[1]))
                    #pnt.timestamp.when = current_dt.strftime('%Y-%m-%dT%XZ')


                # Model
                #model = {'link': None, 'longitude': None, 'latitude': None, 'altitude' : None, 'scale': None}
                #class simplekml.Model(altitudemode=None, gxaltitudemode=None, location=None, orientation=None, scale=None, link=None, resourcemap=None, **kwargs)
                #if currentatt[self.fields['model']]:
                    modeldict = eval(currentatt[self.fields['model']])

                    if modeldict['link']:
                        mdl.link = simplekml.Link(href = modeldict['link'])

                        loc = simplekml.Location()
                        if modeldict['longitude']:
                            loc.longitude = modeldict['longitude']
                        else:
                            loc.longitude = coords[0]

                        if modeldict['latitude']:
                            loc.latitude = modeldict['latitude']
                        else:
                            loc.latitude = coords[1]

                        if modeldict['altitude']:
                            if modeldict['altitude'] == 'altitude':  # get the altitude from the gps  [u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']

                                try:
                                    loc.altitude = currentatt[self.fields['descriptio']].split(",")[4].split(': ')[1]
                                except:
                                    try:
                                        loc.altitude = currentatt[self.fields['Descriptio']].split(",")[4].split(': ')[1]
                                    except:
                                        self.logger.error('export function error')
                                        self.logger.info('self.fields keys {0}'.format(self.fields.keys))
                                        self.logger.exception(traceback.format_exc())
                                        self.iface.messageBar().pushMessage("Error", "exportToFile error. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


                            else:
                                loc.altitude = modeldict['altitude']
                            mdl.altitudemode = 'relativeToGround'
                        mdl.location = loc
                        mdl.timestamp = simplekml.TimeStamp(when=current_dt.strftime('%Y-%m-%dT%XZ'))



                    scl = simplekml.Scale()
                    if modeldict['scale']:
                        scl.x = modeldict['scale']; scl.y = modeldict['scale']; scl.z = modeldict['scale']
                        mdl.scale = scl


                cc += 1

#            if self.dlg.ui.lineEdit_export_audio.currentText():  # there is a wav file to attach. So only offer kmz

            exportpath = QFileDialog.getSaveFileName(None, "Save Track", self.lastdirectory, "(*.kml *.kmz *.gpx *.shp *.geojson *.csv)")
            if exportpath:
                self.lastdirectory = os.path.dirname(exportpath)
            if exportpath:
                if exportpath.split('.')[1] == 'kml':
                    kml.save(exportpath)
                    self.iface.messageBar().pushMessage("Success", "kml file exported to: {0}".format(exportpath), level=QgsMessageBar.INFO, duration=5)
                if exportpath.split('.')[1] == 'kmz':
                    kml.savekmz(exportpath)
                    self.iface.messageBar().pushMessage("Success", "kmz file exported to: {0}".format(exportpath), level=QgsMessageBar.INFO, duration=5)
                if exportpath.split('.')[1] == 'gpx':
                    QgsVectorFileWriter.writeAsVectorFormat(self.ActiveLayer, exportpath, "utf-8", None, "GPX")
                    self.iface.messageBar().pushMessage("Success", "gpx file exported to: {0}".format(exportpath), level=QgsMessageBar.INFO, duration=5)
                if exportpath.split('.')[1] == 'shp':
                    QgsVectorFileWriter.writeAsVectorFormat(self.ActiveLayer, exportpath, "utf-8", None, "ESRI Shapefile")
                    self.iface.messageBar().pushMessage("Success", "ESRI shapefile exported to: {0}".format(exportpath), level=QgsMessageBar.INFO, duration=5)
                if exportpath.split('.')[1] == 'geojson':
                    QgsVectorFileWriter.writeAsVectorFormat(self.ActiveLayer, exportpath, "utf-8", None, "GeoJSON")
                    self.iface.messageBar().pushMessage("Success", "GeoJson file exported to: {0}".format(exportpath), level=QgsMessageBar.INFO, duration=5)
                if exportpath.split('.')[1] == 'csv':
                    QgsVectorFileWriter.writeAsVectorFormat(self.ActiveLayer, exportpath, "utf-8", None, "CSV")
                    self.iface.messageBar().pushMessage("Success", "GeoJson file exported to: {0}".format(exportpath), level=QgsMessageBar.INFO, duration=5)

#QgsVectorFileWriter.ogrDriverList()
#{u'ESRI Shapefile': u'ESRI Shapefile', u'AutoCAD DXF': u'DXF', u'Geography Markup Language [GML]': u'GML', u'GPS eXchange Format [GPX]': u'GPX', u'Generic Mapping Tools [GMT]': u'GMT', u'GeoJSON': u'GeoJSON', u'GeoRSS': u'GeoRSS', u'Mapinfo TAB': u'MapInfo File', u'Mapinfo MIF': u'MapInfo MIF', u'SpatiaLite': u'SpatiaLite', u'Geoconcept': u'Geoconcept', u'DBF file': u'DBF file', u'S-57 Base file': u'S57', u'Atlas BNA': u'BNA', u'Microstation DGN': u'DGN', u'Keyhole Markup Language [KML]': u'KML', u'Comma Separated Value': u'CSV', u'SQLite': u'SQLite'}

        except:
            self.logger.error('export function error')
            self.logger.exception(traceback.format_exc())
            self.iface.messageBar().pushMessage("Error", "exportToFile error. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


    def trackdetails(self):
        try:

            rectangle = self.ActiveLayer.extent() #QgsRectange,  returns string representation of form xmin,ymin xmax,ymax,   u'-75.17254,39.96574 : -75.17047,39.96658'
            self.extent = {'xmin' : rectangle.xMinimum(), 'xmax' : rectangle.xMaximum(), 'ymin' : rectangle.yMinimum(), 'ymax' : rectangle.yMaximum()}
            featcount = self.ActiveLayer.featureCount()

            # create layer

            utmpts = QgsVectorLayer("Point?crs=EPSG:26918", 'utmpts', "memory")
            pr = utmpts.dataProvider()
            # add a feature
            fet = QgsFeature()


            crsSrc = QgsCoordinateReferenceSystem(4326)    # WGS 84
            crsDest = QgsCoordinateReferenceSystem(26918)  # WGS 84 / UTM zone 33N
            xform = QgsCoordinateTransform(crsSrc, crsDest)

            speedlist = []; altitudelist = []; ptlist = []; i = 0
            for f in self.ActiveLayer.getFeatures(): #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
                currentatt = f.attributes()
                geom = f.geometry().asPoint()
                utmpt = xform.transform(QgsPoint(geom[0], geom[1]))
                ptlist.append(utmpt)

                # now add the utm 18n point to the new feature
                fet.setGeometry( QgsGeometry.fromPoint(QgsPoint(utmpt[0],utmpt[1])) )
                pr.addFeatures([fet])


                if i == 0:
                    pointdate = currentatt[0].split(" ")[0]; pointtime = currentatt[0].split(" ")[1]
                    start_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
                else:
                    pointdate = currentatt[0].split(" ")[0]; pointtime = currentatt[0].split(" ")[1]
                    end_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))

                speedlist.append(float(f.attributes()[1].split(',')[3].split(':')[1]))
                altitudelist.append(float(f.attributes()[1].split(',')[4].split(':')[1]))
                i += 1

            dura = end_dt - start_dt # duration

            d = QgsDistanceArea()  # create an instance of the distance area class
            d.setEllipsoidalMode(True)
            d.setSourceCrs(26918)
            distancekm = d.measureLine(ptlist)/1000
            distancemi = distancekm * 0.621371


            featmess = 'Features:\t\t{0}\n'.format(featcount)
            elevmess = 'Elevation (min, max):\t{0}, {1}\n'.format("%.2f" % min(altitudelist),"%.2f" %  max(altitudelist))
            speedmess = 'Speed (min, max):\t{0}, {1}\n'.format("%.2f" % min(speedlist), "%.2f" % max(speedlist))
            duramess = 'Duration:\t\t{0}\n'.format(dura)
            lenmess = 'Distance (km, mi):\t{0}, {1}\n'.format("%.2f" % distancekm, "%.2f" % distancemi)

            bmessage = 'Bounding Box:\n\n\t{0}\n{1}\t\t{2}\n\t{3}'.format(self.extent['ymax'], self.extent['xmin'], self.extent['xmax'], self.extent['ymin'])

            message = featmess + elevmess + speedmess + duramess + lenmess + bmessage

            QMessageBox.information( self.iface.mainWindow(),"Track Details", message )

            #QgsMapLayerRegistry.instance().addMapLayer(utmpts)

        except:
            if self.logging == True:
                self.logger.error('track function error')
                self.logger.exception(traceback.format_exc())
            self.iface.messageBar().pushMessage("Error", "trackdetails error. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)








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
        self.dlg.ui.comboBox_flyto_mode.clear()
        flytomodelist = [None, 'smooth', 'bounce']
        for hh in flytomodelist:
            self.dlg.ui.comboBox_flyto_mode.addItem(hh)

        self.dlg.ui.comboBox_altitudemode.clear()
        altitudemode = [None, 'absolute', 'clampToGround', 'relativeToGround', 'relativeToModel']
        for alt in altitudemode:
            self.dlg.ui.comboBox_altitudemode.addItem(alt)

        self.dlg.ui.comboBox_gxaltitudemode.clear()
        gxaltitudemode = [None, 'clampToSeaFloor', 'relativeToSeaFloor']
        for gxalt in gxaltitudemode:
            self.dlg.ui.comboBox_gxaltitudemode.addItem(gxalt)

        # Follow Behind Combo Boxes
        self.dlg.ui.comboBox_follow_altitudemode.clear()
        for alt in altitudemode:
            self.dlg.ui.comboBox_follow_altitudemode.addItem(alt)

        self.dlg.ui.comboBox_follow_gxaltitudemode.clear()
        for gxalt in gxaltitudemode:
            self.dlg.ui.comboBox_follow_gxaltitudemode.addItem(gxalt)


        # Populate the Rendering Combo Box
        self.dlg.ui.comboBox_rendering_icon_color.clear()
        colors = simplekml.Color.__dict__.keys()
        colors.append('')
        colors.sort()
        for c in colors:
            if not c:
                self.dlg.ui.comboBox_rendering_icon_color.addItem(c)
                self.dlg.ui.comboBox_rendering_label_color.addItem(c)
            elif c[0] == '_':
                pass
            else:
                self.dlg.ui.comboBox_rendering_icon_color.addItem(c)
                self.dlg.ui.comboBox_rendering_label_color.addItem(c)


        self.dlg.ui.comboBox_rendering_label_colormode.clear()
        self.dlg.ui.comboBox_rendering_icon_colormode.clear()
        colormode = [None, 'normal', 'random']
        for c in colormode:
            self.dlg.ui.comboBox_rendering_label_colormode.addItem(c)
            self.dlg.ui.comboBox_rendering_icon_colormode.addItem(c)


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
        self.dlg.ui.lineEdit_export_audio.setText(None)
        self.audio_delay = None

        # Viz
        self.dlg.ui.lineEdit_visualization_active.setText(None)
        try: self.ActiveLayer_name = None
        except: pass
        try: self.ActiveLayer = None
        except: pass


        self.dlg.ui.lineEdit_visualization_active.setText(None)
        self.dlg.ui.checkBox_visualization_edit.setEnabled(False)

        # Tour
        self.dlg.ui.lineEdit_tourname.setText(None)
        # FlyTo
        self.dlg.ui.lineEdit_flyto_duration.setText(None)
        # Camera
        self.dlg.ui.lineEdit_visualization_camera_longitude.setText(None)
        self.dlg.ui.lineEdit_visualization_camera_latitude.setText(None)
        self.dlg.ui.lineEdit_visualization_camera_altitude.setText(None)
        self.dlg.ui.lineEdit__visualization_camera_gxhoriz.setText(None)
        self.dlg.ui.lineEdit__visualization_camera_heading.setText(None)
        self.dlg.ui.lineEdit__visualization_camera_roll.setText(None)
        self.dlg.ui.lineEdit__visualization_camera_tilt.setText(None)
        self.dlg.ui.lineEdit_visualization_camera_longitude_off.setText(None)
        self.dlg.ui.lineEdit_visualization_camera_latitude_off.setText(None)

        # Follow Behind
        self.dlg.ui.lineEdit_visualization_follow_altitude.setText(None)
        self.dlg.ui.lineEdit__visualization_follow_gxhoriz.setText(None)
        self.dlg.ui.lineEdit__visualization_follow_tilt.setText(None)
        self.dlg.ui.lineEdit__visualization_follow_range.setText(None)


        # Tour
        self.dlg.ui.lineEdit_tourname.setEnabled(False)
        # FlyTo
        self.dlg.ui.comboBox_flyto_mode.setEnabled(False)
        self.dlg.ui.lineEdit_flyto_duration.setEnabled(False)
        # Camera
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
        self.dlg.ui.pushButton_visualization_camera_xy.setEnabled(False)
        self.dlg.ui.lineEdit_visualization_camera_longitude_off.setEnabled(False)
        self.dlg.ui.lineEdit_visualization_camera_latitude_off.setEnabled(False)

        # Follow Behind
        self.dlg.ui.lineEdit_visualization_follow_altitude.setEnabled(False)
        self.dlg.ui.comboBox_follow_altitudemode.setEnabled(False)
        self.dlg.ui.comboBox_follow_gxaltitudemode.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_follow_gxhoriz.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_follow_tilt.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_follow_range.setEnabled(False)
        self.dlg.ui.pushButton_follow_apply.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_follow_follow_angle.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_follow_smoother.setEnabled(False)

        # Placemarks/Rendering

        self.dlg.ui.checkBox_rendering_edit.setChecked(False)
        # Clear the text
        # Label style
        self.dlg.ui.lineEdit_rendering_label_scale.setText('0')

        # Icon Style
        self.dlg.ui.lineEdit_rendering_icon_transparency.setText('100')
        self.dlg.ui.lineEdit_rendering_icon_scale.setText('1')
        self.dlg.ui.lineEdit_rendering_icon_heading.setText('0')
        self.dlg.ui.lineEdit_rendering_icon_icon.setText(None)
        self.dlg.ui.lineEdit_rendering_icon_hotspot.setText(None)

        # Model
        self.dlg.ui.lineEdit_rendering_model_link.setText(None)
        self.dlg.ui.lineEdit_rendering_model_longitude.setText(None)
        self.dlg.ui.lineEdit_rendering_model_latitude.setText(None)
        self.dlg.ui.lineEdit_rendering_model_altitude.setText('altitude')
        self.dlg.ui.lineEdit_rendering_model_scale.setText('1')

        #Disble

        # Label style
        self.dlg.ui.comboBox_rendering_label_color.setEnabled(False)
        self.dlg.ui.comboBox_rendering_label_colormode.setEnabled(False)
        self.dlg.ui.lineEdit_rendering_label_scale.setEnabled(False)

        # Icon Style
        self.dlg.ui.comboBox_rendering_icon_color.setEnabled(False)
        self.dlg.ui.lineEdit_rendering_icon_transparency.setEnabled(False)
        self.dlg.ui.comboBox_rendering_icon_colormode.setEnabled(False)
        self.dlg.ui.lineEdit_rendering_icon_scale.setEnabled(False)
        self.dlg.ui.lineEdit_rendering_icon_heading.setEnabled(False)
        self.dlg.ui.lineEdit_rendering_icon_icon.setEnabled(False)
        self.dlg.ui.lineEdit_rendering_icon_hotspot.setEnabled(False)

        # Model
        self.dlg.ui.lineEdit_rendering_model_link.setEnabled(False)
        self.dlg.ui.lineEdit_rendering_model_longitude.setEnabled(False)
        self.dlg.ui.lineEdit_rendering_model_latitude.setEnabled(False)
        self.dlg.ui.lineEdit_rendering_model_altitude.setEnabled(False)
        self.dlg.ui.lineEdit_rendering_model_scale.setEnabled(False)
        self.dlg.ui.pushButton_rendering_model_file.setEnabled(False)
        self.dlg.ui.pushButton_rendering_model_xy.setEnabled(False)
        self.dlg.ui.checkBox_rendering_model_z.setEnabled(False)

        ###################
        # Time
        # Clear out
        self.dlg.ui.checkBox_time_edit.setChecked(False)
        self.dlg.ui.checkBox_time_before.setChecked(False)
        self.dlg.ui.checkBox_time_after.setChecked(False)
        # Disable
        self.dlg.ui.checkBox_time_before.setEnabled(False)
        self.dlg.ui.dateTimeEdit_start.setEnabled(False)
        self.dlg.ui.dateTimeEdit_end.setEnabled(False)
        self.dlg.ui.checkBox_time_after.setEnabled(False)

        # Apply Buttons
        self.dlg.ui.pushButton_time_apply_startend.setEnabled(False)