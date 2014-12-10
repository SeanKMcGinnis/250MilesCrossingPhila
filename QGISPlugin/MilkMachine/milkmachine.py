# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MilkMachine
                                 A QGIS plugin
 Process, edit, and scyncronize GPS and audio tracks with KML output
                              -------------------
        begin                : 2014-06-11
        copyright            : (C) 2014 by polakvanbekkum & Ed Farrell
        email                : eddief77@yahoo.com
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
from mutagen.mp3 import MP3
import time, datetime, wave
import TeatDip
import subprocess
import logging
import platform
import re, os, StringIO
import math

from scipy import interpolate
from scipy import stats
import numpy as np
#import matplotlib.pyplot as plt
from numpy import linspace,exp
from numpy.random import randn
from scipy.interpolate import UnivariateSpline
#from pylab import *

UserOs = platform.platform()
WindOs = re.search('Windows', UserOs, re.I)



#--------------------------------------------------------------------------------
NOW = None
pointid = None
ClockDateTime = None
Scratch = None
AllList = []
pause = 0

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

        if WindOs:
            if WindOs.group() == 'Windows':
                self.os = 'Windows'
            else:
                self.os = 'other'
        else:
            self.os = 'other'


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

        # for the selected point
        self.selectedCamera = None

        QObject.connect(self.dlg.ui.chkActivate,SIGNAL("stateChanged(int)"),self.changeActive)
        QObject.connect(self.dlg.ui.buttonImportGPS, SIGNAL("clicked()"), self.browseOpen)
        QObject.connect(self.dlg.ui.buttonDrawTrack, SIGNAL("clicked()"), self.drawtrack)
        QObject.connect(self.dlg.ui.buttonExportTrack, SIGNAL("clicked()"), self.exportToFile)
        #QObject.connect(self.iface.legendInterface(), SIGNAL("itemRemoved()"), self.removeCombo)  #currentIndexChanged(int)
        #QObject.connect(self.iface.legendInterface(), SIGNAL("itemAdded(QModelIndex)"), self.addedCombo)
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
        QObject.connect(self.dlg.ui.pushButton_lookat_apply, SIGNAL("clicked()"), self.lookat_apply)
        QObject.connect(self.dlg.ui.pushButton_circle_apply, SIGNAL("clicked()"), self.circle_apply)
        QObject.connect(self.dlg.ui.checkBox_filtering_edit,SIGNAL("stateChanged(int)"),self.filtercheck)
        QObject.connect(self.dlg.ui.pushButton_filtering_apply, SIGNAL("clicked()"), self.filtering_apply)
        QObject.connect(self.dlg.ui.lineEdit__visualization_circle_tilt,SIGNAL("editingFinished()"),self.durationpopulate)
        QObject.connect(self.dlg.ui.lineEdit__visualization_circle_range,SIGNAL("editingFinished()"),self.durationpopulate)
        QObject.connect(self.dlg.ui.lineEdit__visualization_circle_start_heading,SIGNAL("editingFinished()"),self.durationpopulate)
        QObject.connect(self.dlg.ui.lineEdit__visualization_circle_rotations,SIGNAL("editingFinished()"),self.durationpopulate)

        QObject.connect(self.dlg.ui.pushButton_visualization_camera_symbolize, SIGNAL("clicked()"), self.camera_symbolize)
        QObject.connect(self.dlg.ui.pushButton_visualization_camera_tofollow, SIGNAL("clicked()"), self.tofollow)
        QObject.connect(self.dlg.ui.pushButton_visualization_camera_tocustom, SIGNAL("clicked()"), self.tocustom)
        QObject.connect(self.dlg.ui.radioButton_filtering_xy,SIGNAL("toggled(bool)"),self.xycheck)
        QObject.connect(self.dlg.ui.radioButton_filtering_z,SIGNAL("toggled(bool)"),self.zcheck)

        # Fonts
        if self.os == 'other':
            font = QFont()
            font.setPointSize(9)
            self.dlg.ui.tabWidget.setFont(font)

    ############################################################################
    ## SLOTS


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

    def tiltpopulate(self):
        if self.dlg.ui.lineEdit_visualization_follow_altitude.text() and self.dlg.ui.lineEdit__visualization_follow_range.text() and not self.dlg.ui.lineEdit__visualization_follow_tilt.text():
            try:
                altitude = float(self.dlg.ui.lineEdit_visualization_follow_altitude.text())
                ranger = float(self.dlg.ui.lineEdit__visualization_follow_range.text())
                angle = round(math.degrees(math.acos(altitude/ranger)),1)
                self.dlg.ui.lineEdit__visualization_follow_tilt.setText(str(angle))
            except:
                if self.logging == True:
                    self.logger.exception(traceback.format_exc())

    def durationpopulate(self):
        if self.dlg.ui.lineEdit_visualization_circle_altitude.text():
            self.ActiveLayer = self.iface.activeLayer()
            self.fields = self.field_indices(self.ActiveLayer)
            features = self.ActiveLayer.selectedFeatures()
            selected = []
            for f in features:
                selected.append([f.id(), f.attributes()[self.fields['datetime']]])

            def getKey(item):
                return item[0]
            selected = sorted(selected, key=getKey)  #[[id, (x,y), altitude]]
            first = selected[0][1]; last = selected[-1][1]

            sel_start_dt = self.to_dt(first)
            sel_end_dt = self.to_dt(last)
            diff = sel_end_dt - sel_start_dt
            self.dlg.ui.lineEdit__visualization_circle_duration.setText(str(diff.seconds+1))


    def google_earth(self):
        pass

    ############################################################################
    ############################################################################
    ## Filtering
    ############################################################################
    def filtering_apply(self):
        try:
            self.ActiveLayer = self.iface.activeLayer()
            self.fields = self.field_indices(self.ActiveLayer)
            if self.os == 'Windows':
                import matplotlib.pyplot as plt
            selectList = []  #[[id, (x,y), altitude]]
            for f in self.ActiveLayer.selectedFeatures():
                geom = f.geometry()
                alt = f.attributes()[self.fields['altitude']]
                selectList.append([f.id(), geom.asPoint(), alt])
            # sort self.selectList by fid
            def getKey(item):
                return item[0]
            selectList = sorted(selectList, key=getKey)  #[[id, (x,y), altitude]]
            # turn the coordinates into numpy arrays
            xarr = []; yarr = []; zarr = []
            for val in selectList:
                xarr.append(val[1][0]);yarr.append(val[1][1]);zarr.append(val[2])
            ptx = np.array(xarr); pty = np.array(yarr); ptz = np.array(zarr)


            if self.dlg.ui.radioButton_filtering_moving.isChecked():  # rolling mean
                window = self.dlg.ui.spinBox_filtering_moving.value() # this needs to be odd or throw an error.
                if (window % 2 == 0): #even
                    self.iface.messageBar().pushMessage("Error", "Window size must be an odd integer", level=QgsMessageBar.CRITICAL, duration=7)
                else: #odd

                    # If XY filtering
                    if self.dlg.ui.radioButton_filtering_xy.isChecked():
                        xroll = TeatDip.rolling_window(ptx, window); yroll = TeatDip.rolling_window(pty, window)
                        xmean = []; ymean = []
                        pad = (window - 1)/2
                        counter = 0
                        for i in range(pad):
                            xmean.append(ptx[i])
                            counter += 1
                        for xx in xroll:
                            xmean.append(np.mean(xx))
                            counter += 1
                        lastx = ptx[-pad:]
                        for l in lastx:
                            xmean.append(l)

                        counter = 0
                        for i in range(pad):
                            ymean.append(pty[i])
                            counter += 1
                        for yy in yroll:
                            ymean.append(np.mean(yy))
                            counter += 1
                        lasty = pty[-pad:]
                        for l in lasty:
                            ymean.append(l)

                        if self.dlg.ui.checkBox_filtering_showplot.isChecked() and self.os == 'Windows':
                            plt.plot(ptx,pty, 'b.', markersize=15)
                            plt.plot(xmean,ymean,'r-',linewidth=2)
                            plt.plot(xmean,ymean,'r.',markersize=15)
                            plt.xlabel('Longitude', size=10); plt.ylabel('Latitude', size=10); plt.axis('equal')
                            plt.title("Filtering: Blue = Original, Red = Filtered", size=20)
                            plt.show()

                        self.ActiveLayer.startEditing()
                        self.ActiveLayer.beginEditCommand('Moving Average Filter')
                        for i,f in enumerate(selectList):    #[[id, (x,y), altitude]]
                            fet = QgsGeometry.fromPoint(QgsPoint(xmean[i],ymean[i]))
                            self.ActiveLayer.changeGeometry(f[0],fet)
                        self.ActiveLayer.endEditCommand()
                        self.canvas.refresh()

                        self.iface.messageBar().pushMessage("Success", "Applied interpolation to XY points", level=QgsMessageBar.INFO, duration=5)

                    # z filtering
                    if self.dlg.ui.radioButton_filtering_z.isChecked():
                        zroll = TeatDip.rolling_window(ptz, window)
                        zmean = []
                        pad = (window - 1)/2
                        counter = 0
                        for i in range(pad):
                            zmean.append(ptz[i])
                            counter += 1
                        for zz in zroll:
                            zmean.append(np.mean(zz))
                            counter += 1
                        lastz = ptz[-pad:]
                        for l in lastz:
                            zmean.append(l)

                        self.ActiveLayer.startEditing()
                        self.ActiveLayer.beginEditCommand('Moving Average Filter')
                        for i,f in enumerate(selectList):    #[[id, (x,y), altitude]]
                            self.ActiveLayer.changeAttributeValue(f[0], self.fields['altitude'], round(float(zmean[i]),2))
                        self.ActiveLayer.endEditCommand()
                        self.canvas.refresh()

                        self.iface.messageBar().pushMessage("Success", "Applied interpolation to Z points", level=QgsMessageBar.INFO, duration=5)

            # Linear Regression ------------------
            if self.dlg.ui.radioButton_filtering_linear.isChecked() and self.dlg.ui.radioButton_filtering_xy.isChecked():
                xweight = float(self.dlg.ui.doubleSpinBox_filtering_xweight.value())
                yweight = float(self.dlg.ui.doubleSpinBox_filtering_yweight.value())

                #slope, intercept, r_value, p_value, std_err = stats.linregress(ptx,pty)
                (m,b) = np.polyfit(ptx,pty,1)
                yp = np.polyval([m,b],ptx)  # ptx, yp

                (m2,b2) = np.polyfit(pty,ptx,1)
                xp = np.polyval([m2,b2],pty)  #xp, pty

                xdiff = (xp - ptx) / float(2)
                ydiff = (yp - pty) / float(2)
                xgeo = ptx + (xdiff * xweight)
                ygeo = pty + (ydiff * yweight)


                if self.dlg.ui.checkBox_filtering_showplot.isChecked() and self.os == 'Windows':
                    plt.plot(ptx,pty, 'b.', markersize=15)
                    plt.plot(ptx,yp,'r-',linewidth=2)
                    plt.plot(ptx,yp,'r.', markersize=15)
                    plt.plot(xp,pty,'g-',linewidth=2)
                    plt.plot(xp,pty,'g.', markersize=15)
                    plt.plot(xgeo,ygeo,'m.', markersize=15)
                    plt.xlabel('Longitude', size=10); plt.ylabel('Latitude', size=10); plt.axis('equal')
                    plt.title("Filtering: Blue = Original, Red = Filtered", size=20)
                    plt.show()

                self.ActiveLayer.startEditing()
                self.ActiveLayer.beginEditCommand('Linear Filter')
                for i,f in enumerate(selectList):    #[[id, (x,y), altitude]]
                    fet = QgsGeometry.fromPoint(QgsPoint(xgeo[i],ygeo[i]))  #fet = QgsGeometry.fromPoint(QgsPoint(ptx[i],yp[i]))
                    self.ActiveLayer.changeGeometry(f[0],fet)
                self.ActiveLayer.endEditCommand()
                self.canvas.refresh()

                self.iface.messageBar().pushMessage("Success", "Applied interpolation to points", level=QgsMessageBar.INFO, duration=5)

            elif self.dlg.ui.radioButton_filtering_linear.isChecked() and self.dlg.ui.radioButton_filtering_z.isChecked():
                self.iface.messageBar().pushMessage("Error", "Linear can only be used for X,Y filtering", level=QgsMessageBar.CRITICAL, duration=7)

            # Centering ------------------
            if self.dlg.ui.radioButton_filtering_center.isChecked() and self.dlg.ui.radioButton_filtering_xy.isChecked():
                weight = float(self.dlg.ui.doubleSpinBox_filtering_center_weight.value())

                # calculate the centroid.
                ptx_mean = np.mean(ptx); pty_mean = np.mean(pty)
                xdist = ptx_mean - ptx; ydist = pty_mean - pty
                xnew = ptx + (xdist * weight); ynew = pty + (ydist * weight)

                self.ActiveLayer.startEditing()
                self.ActiveLayer.beginEditCommand('Moving Average Filter')
                for i,f in enumerate(selectList):    #[[id, (x,y), altitude]]
                    fet = QgsGeometry.fromPoint(QgsPoint(xnew[i],ynew[i]))
                    self.ActiveLayer.changeGeometry(f[0],fet)
                self.ActiveLayer.endEditCommand()
                self.canvas.refresh()

                if self.dlg.ui.checkBox_filtering_showplot.isChecked() and self.os == 'Windows':
                    plt.plot(ptx,pty, 'b.', markersize=15)
                    plt.plot(xnew, ynew,'r.', markersize=15)
                    plt.xlabel('Longitude', size=10); plt.ylabel('Latitude', size=10); plt.axis('equal')
                    plt.title("Filtering: Blue = Original, Red = Filtered, Weight = {0}".format(weight), size=20)
                    plt.show()

            # Spline Regression ------------------
            if self.dlg.ui.radioButton_filtering_quad.isChecked() and self.dlg.ui.radioButton_filtering_xy.isChecked():
                #slope, intercept, r_value, p_value, std_err = stats.linregress(ptx,pty)
                method = self.dlg.ui.comboBox_filtering_spline.currentText()
                sweight = float(self.dlg.ui.doubleSpinBox_filtering_spline_weight.value())
                methdict = {'Quadratic': 2, 'Cubic': 3, '4th Order': 4, '5th Order': 5}
                meth = methdict[method]

                # resort selectList by x. x has to be increasing!
                def getKeyX(item):
                    return item[1][0]
                selectListX = selectList
                selectListX = sorted(selectListX, key=getKeyX)  #[[id, (x,y), altitude]]
                # turn the coordinates into numpy arrays
                xarr = []; yarr = [];
                for val in selectListX:
                    xarr.append(val[1][0]);yarr.append(val[1][1])
                ptx = np.array(xarr); pty = np.array(yarr)

                s = UnivariateSpline(ptx,pty, k=meth, s=5e8)
                #s = interpolate.interp1d(ptx,pty, kind=meth, assume_sorted=False)
                ys = s(ptx)
                diff = ys - pty
                ynew = pty + (diff * sweight)
                # get rid of nan
                for i,v in enumerate(ynew):
                    if np.isnan(v):
                        ynew[i] = pty[i]

##                self.logger.info('pty: {0}'.format(pty))
##                self.logger.info('ys: {0}'.format(ys))
##                self.logger.info('ynew: {0}'.format(ynew))
##                self.logger.info('ptx: {0}'.format(ptx))
##                self.logger.info('selectListX: {0}'.format(selectListX))
##                (a,b,c) = np.polyfit(ptx,pty,2)
##                yp = np.polyval([a,b,c],ptx)

                if self.dlg.ui.checkBox_filtering_showplot.isChecked() and self.os == 'Windows':
                    plt.plot(ptx,pty, 'b.', markersize=15)
                    #plt.plot(ptx,ys, 'g.', markersize=15)
                    plt.plot(ptx,ynew,'r-',linewidth=2)
                    plt.plot(ptx,ynew,'r.', markersize=15)
                    plt.xlabel('Longitude', size=10); plt.ylabel('Latitude', size=10); plt.axis('equal')
                    plt.title("Filtering: Blue = Original, Red = Filtered", size=20)
                    plt.show()

                self.ActiveLayer.startEditing()
                self.ActiveLayer.beginEditCommand('Quadratic Filter')
                for i,f in enumerate(selectListX):    #[[id, (x,y), altitude]]
                    fet = QgsGeometry.fromPoint(QgsPoint(ptx[i],ynew[i]))
                    self.ActiveLayer.changeGeometry(f[0],fet)
                self.ActiveLayer.endEditCommand()
                self.canvas.refresh()

                self.iface.messageBar().pushMessage("Success", "Applied spline interpolation to points", level=QgsMessageBar.INFO, duration=5)

            elif self.dlg.ui.radioButton_filtering_quad.isChecked() and self.dlg.ui.radioButton_filtering_z.isChecked():
                self.iface.messageBar().pushMessage("Error", "Quadratic can only be used for X,Y filtering", level=QgsMessageBar.CRITICAL, duration=7)

            # Z Scaling ------------------
            if self.dlg.ui.radioButton_filtering_zscale.isChecked() and self.dlg.ui.radioButton_filtering_z.isChecked():
                zmin = np.min(ptz)
                zmax = np.max(ptz)
                zmintext = self.dlg.ui.lineEdit_filtering_min.text()
                zmaxtext = self.dlg.ui.lineEdit_filtering_max.text()
                if not zmintext and not zmaxtext:
                    self.iface.messageBar().pushMessage("Error", "No values specified for Z Range", level=QgsMessageBar.CRITICAL, duration=7)
                elif zmintext or zmaxtext:
                    if zmintext:
                        zmin2 = float(zmintext)
                    else:
                        zmin2 = zmin
                    if zmaxtext:
                        zmax2 = float(zmaxtext)
                    else:
                        zmax2 = zmax
                    curr_range = abs(zmin - zmax)
                    new_range = abs(zmin2 - zmax2)

                    # center the range on 0
                    ptz_centered = ptz - (zmax - zmin)*0.5
                    # calculate the scale factor
                    scaleX = new_range/curr_range
                    # scale the centered data
                    ptz_scaled = ptz_centered * scaleX
                    # recenter the data using the middle of the range
                    new_mid = zmax2 - (abs(zmin2 - zmax2)/2)
                    ptz_new = (zmax2 - np.max(ptz_scaled)) + ptz_scaled

                    if self.dlg.ui.checkBox_filtering_showplot.isChecked() and self.os == 'Windows':
                        plt.plot(ptz,'b-',linewidth=2, label="Orginal")
                        plt.plot(ptz, 'b.', markersize=15)
                        plt.plot(ptz_new,'r-',linewidth=2, label="Scaled")
                        plt.plot(ptz_new,'r.', markersize=15)
                        plt.xlabel('Time', size=10); plt.ylabel('Altitude', size=10); plt.axis('equal')
                        plt.title("Original; Min: {0}, Max: {1}, Range: {2}\nScaled; Min: {3}, Max: {4}, Range: {5}".format(np.min(ptz), np.max(ptz), curr_range, np.min(ptz_new), np.max(ptz_new), abs(np.min(ptz_new)-np.max(ptz_new))), size=12)
                        plt.legend()
                        plt.show()


                    self.ActiveLayer.startEditing()
                    self.ActiveLayer.beginEditCommand('Z Scaling')
                    for i,f in enumerate(selectList):    #[[id, (x,y), altitude]]
                        self.ActiveLayer.changeAttributeValue(f[0], self.fields['altitude'], round(float(ptz_new[i]),2))
                    self.ActiveLayer.endEditCommand()
                    self.canvas.refresh()

                    self.iface.messageBar().pushMessage("Success", "Applied Z Scaling to points.", level=QgsMessageBar.INFO, duration=5)


        except:
            self.dlg.ui.checkBox_filtering_edit.setChecked(False)
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('filtering function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Filtering function error. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

    def xycheck(self,checked):
        try:
            if self.dlg.ui.radioButton_filtering_xy.isChecked():
                self.dlg.ui.radioButton_filtering_linear.setEnabled(True)
                self.dlg.ui.label_46.setEnabled(True)
                self.dlg.ui.doubleSpinBox_filtering_xweight.setEnabled(True)
                self.dlg.ui.label_47.setEnabled(True)
                self.dlg.ui.label_66.setEnabled(True)
                self.dlg.ui.doubleSpinBox_filtering_yweight.setEnabled(True)
                self.dlg.ui.label_64.setEnabled(True)
                self.dlg.ui.comboBox_filtering_spline.setEnabled(True)
                self.dlg.ui.label_65.setEnabled(True)
                self.dlg.ui.doubleSpinBox_filtering_spline_weight.setEnabled(True)
                self.dlg.ui.radioButton_filtering_center.setEnabled(True)
                self.dlg.ui.label_63.setEnabled(True)
                self.dlg.ui.doubleSpinBox_filtering_center_weight.setEnabled(True)
                self.dlg.ui.radioButton_filtering_quad.setEnabled(True)
                self.dlg.ui.radioButton_filtering_moving.setEnabled(True)
                self.dlg.ui.spinBox_filtering_moving.setEnabled(True)

                self.dlg.ui.radioButton_filtering_zscale.setEnabled(False)
                self.dlg.ui.label_48.setEnabled(False)
                self.dlg.ui.lineEdit_filtering_min.setEnabled(False)
                self.dlg.ui.label_52.setEnabled(False)
                self.dlg.ui.lineEdit_filtering_max.setEnabled(False)
        except:
            self.dlg.ui.checkBox_filtering_edit.setChecked(False)
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            if self.logging == True:
                self.logger.error('filtering zcheck error')
                self.logger.exception(traceback.format_exc())
            self.iface.messageBar().pushMessage("Error", "Failed to turn on filtering fields. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

    def zcheck(self,checked):
        try:
            if self.dlg.ui.radioButton_filtering_z.isChecked():
                # filters
                self.dlg.ui.radioButton_filtering_linear.setEnabled(False)
                self.dlg.ui.label_46.setEnabled(False)
                self.dlg.ui.doubleSpinBox_filtering_xweight.setEnabled(False)
                self.dlg.ui.label_47.setEnabled(False)
                self.dlg.ui.label_66.setEnabled(False)
                self.dlg.ui.doubleSpinBox_filtering_yweight.setEnabled(False)
                self.dlg.ui.label_64.setEnabled(False)
                self.dlg.ui.comboBox_filtering_spline.setEnabled(False)
                self.dlg.ui.label_65.setEnabled(False)
                self.dlg.ui.doubleSpinBox_filtering_spline_weight.setEnabled(False)
                self.dlg.ui.radioButton_filtering_center.setEnabled(False)
                self.dlg.ui.label_63.setEnabled(False)
                self.dlg.ui.doubleSpinBox_filtering_center_weight.setEnabled(False)
                self.dlg.ui.radioButton_filtering_quad.setEnabled(False)
                self.dlg.ui.radioButton_filtering_moving.setEnabled(True)
                self.dlg.ui.spinBox_filtering_moving.setEnabled(True)
                self.dlg.ui.radioButton_filtering_zscale.setEnabled(True)
                self.dlg.ui.label_48.setEnabled(True)
                self.dlg.ui.lineEdit_filtering_min.setEnabled(True)
                self.dlg.ui.label_52.setEnabled(True)
                self.dlg.ui.lineEdit_filtering_max.setEnabled(True)
        except:
            self.dlg.ui.checkBox_filtering_edit.setChecked(False)
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            if self.logging == True:
                self.logger.error('filtering zcheck error')
                self.logger.exception(traceback.format_exc())
            self.iface.messageBar().pushMessage("Error", "Failed to turn on filtering fields. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


    def filtercheck(self,state):  # the checkbox is checked or unchecked for vis Editing
        try:

            if self.dlg.ui.checkBox_filtering_edit.isChecked():  # the checkbox is check for vis Editing

                self.ActiveLayer = self.iface.activeLayer()
                if self.ActiveLayer:
                    self.fields = self.field_indices(self.ActiveLayer)
                    if not self.ActiveLayer.isEditable():  # the layer is not editable
                        QMessageBox.information(self.iface.mainWindow(),"Filtering Error", 'The currently active layer is not in an "Edit Session".' )
                        self.dlg.ui.checkBox_time_edit.setChecked(False)
                    else:  # cleared for editing...

                        # Get the curretly selected feature
                        self.cLayer = self.iface.mapCanvas().currentLayer()
                        self.selectList = []
                        features = self.cLayer.selectedFeatures()
                        for f in features:
                            self.selectList.append(f.id())  #[u'689',u'2014-06-06 13:30:54']  #[u'2014/06/06 10:30:10', u'Time:10:30:10, Latitude: 39.966531, Longitude: -75.172003, Speed: 3.382047, Altitude: 1.596764']
                        if len(self.selectList) >= 1:

                            # filters
                            self.dlg.ui.radioButton_filtering_xy.setEnabled(True)
                            self.dlg.ui.radioButton_filtering_z.setEnabled(True)
                            self.dlg.ui.radioButton_filtering_linear.setEnabled(True)
                            self.dlg.ui.label_46.setEnabled(True)
                            self.dlg.ui.doubleSpinBox_filtering_xweight.setEnabled(True)
                            self.dlg.ui.label_47.setEnabled(True)
                            self.dlg.ui.label_66.setEnabled(True)
                            self.dlg.ui.doubleSpinBox_filtering_yweight.setEnabled(True)
                            self.dlg.ui.label_64.setEnabled(True)
                            self.dlg.ui.comboBox_filtering_spline.setEnabled(True)
                            self.dlg.ui.label_65.setEnabled(True)
                            self.dlg.ui.doubleSpinBox_filtering_spline_weight.setEnabled(True)
                            self.dlg.ui.radioButton_filtering_center.setEnabled(True)
                            self.dlg.ui.label_63.setEnabled(True)
                            self.dlg.ui.doubleSpinBox_filtering_center_weight.setEnabled(True)
                            self.dlg.ui.radioButton_filtering_quad.setEnabled(True)
                            self.dlg.ui.radioButton_filtering_moving.setEnabled(True)
                            self.dlg.ui.spinBox_filtering_moving.setEnabled(True)

                            if self.dlg.ui.radioButton_filtering_z.isChecked():
                                self.dlg.ui.radioButton_filtering_zscale.setEnabled(True)
                                self.dlg.ui.label_48.setEnabled(True)
                                self.dlg.ui.lineEdit_filtering_min.setEnabled(True)
                                self.dlg.ui.label_52.setEnabled(True)
                                self.dlg.ui.lineEdit_filtering_max.setEnabled(True)
                            # Apply Button
                            self.dlg.ui.pushButton_filtering_apply.setEnabled(True)
                            if self.os == 'Windows':
                                self.dlg.ui.checkBox_filtering_showplot.setEnabled(True)

                        else:
                            QMessageBox.warning( self.iface.mainWindow(),"Active Layer Warning", "Please select points in the active layer to be edited." )

            else:  # checkbox is false, clear shit out

                # filters
                self.dlg.ui.radioButton_filtering_xy.setEnabled(False)
                self.dlg.ui.radioButton_filtering_z.setEnabled(False)
                self.dlg.ui.radioButton_filtering_linear.setEnabled(False)
                self.dlg.ui.label_46.setEnabled(False)
                self.dlg.ui.doubleSpinBox_filtering_xweight.setEnabled(False)
                self.dlg.ui.label_47.setEnabled(False)
                self.dlg.ui.label_66.setEnabled(False)
                self.dlg.ui.doubleSpinBox_filtering_yweight.setEnabled(False)
                self.dlg.ui.label_64.setEnabled(False)
                self.dlg.ui.comboBox_filtering_spline.setEnabled(False)
                self.dlg.ui.label_65.setEnabled(False)
                self.dlg.ui.doubleSpinBox_filtering_spline_weight.setEnabled(False)
                self.dlg.ui.radioButton_filtering_center.setEnabled(False)
                self.dlg.ui.label_63.setEnabled(False)
                self.dlg.ui.doubleSpinBox_filtering_center_weight.setEnabled(False)
                self.dlg.ui.radioButton_filtering_quad.setEnabled(False)
                self.dlg.ui.radioButton_filtering_moving.setEnabled(False)
                self.dlg.ui.spinBox_filtering_moving.setEnabled(False)
                self.dlg.ui.radioButton_filtering_zscale.setEnabled(False)
                self.dlg.ui.label_48.setEnabled(False)
                self.dlg.ui.lineEdit_filtering_min.setEnabled(False)
                self.dlg.ui.label_52.setEnabled(False)
                self.dlg.ui.lineEdit_filtering_max.setEnabled(False)
                # Apply Button
                self.dlg.ui.pushButton_filtering_apply.setEnabled(False)
                self.dlg.ui.checkBox_filtering_showplot.setEnabled(False)

        except:
            self.dlg.ui.checkBox_filtering_edit.setChecked(False)
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('filtering function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to turn on filtering fields. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)



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

##            self.logger.info(layer_start)
##            self.logger.info(layer_end)
##            self.logger.info(sel_start)
##            self.logger.info(sel_end)

            seldiff = sel_end_dt - sel_start_dt
            newdiff = dt_end - dt_start

            currentinterval = round(float(len(selectfids)) / seldiff.seconds, 3) # how many pts per time
            newinterval = round(newdiff.seconds / float((len(selectfids)-1)),3)

            newtimelist = [dt_start]
            for i in range(len(selectfids)-1):
                ct = newtimelist[i]
                newtimelist.append(ct + datetime.timedelta(milliseconds = newinterval)) # add miliseconds to the time

            newtimelistround = [dt_start]
            for i,t in enumerate(newtimelist):
                if i > 0:
                    estime = newtimelist[i]
                    calcsec = int(round(float(estime.microsecond) /1000))
                    rtime = dt_start + datetime.timedelta(seconds = calcsec)
                    #rtime = datetime.datetime(estime.year, estime.month, estime.day, estime.hour, estime.minute, calcsec)
                    newtimelistround.append(rtime)

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

                    newtimelistround = [dt_start]
                    for i,t in enumerate(newtimelist):
                        if i > 0:
                            estime = newtimelist[i]
                            calcsec = int(round(float(estime.microsecond) /1000))
                            rtime = dt_start - datetime.timedelta(seconds = calcsec)
                            newtimelistround.append(rtime)

                    newtimelistround.reverse() # revese the list
                    newtimelistround.pop()

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
                    for i in range(difflen):
                        ct = newtimelist[i]
                        newtimelist.append(ct + datetime.timedelta(milliseconds = newinterval)) # add miliseconds to the time

                    newtimelistround = [dt_end]
                    for i,t in enumerate(newtimelist):
                        if i > 0:
                            estime = newtimelist[i]
                            calcsec = int(round(float(estime.microsecond) /1000))
                            rtime = dt_end + datetime.timedelta(seconds = calcsec)
                            newtimelistround.append(rtime)

                    newtimelistround.reverse() # revese the list
                    newtimelistround.pop()
                    newtimelistround.reverse()

                    self.ActiveLayer.startEditing()
                    self.ActiveLayer.beginEditCommand('datetime edit after')
                    for i,v in enumerate(newtimelistround):
                        valstr = v.strftime("%Y/%m/%d %X")
                        fid = i+selectfids[-1]+1
                        self.ActiveLayer.changeAttributeValue(allfids[fid], self.fields['datetime'], valstr)
                    self.ActiveLayer.endEditCommand()
##                    self.ActiveLayer.endEditCommand()

            self.iface.messageBar().pushMessage("Success", "Time modification applied.", level=QgsMessageBar.INFO, duration=5)


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
                model_altitude.append(f.attributes()[self.fields['altitude']])
##                try:
##                    model_altitude.append(f.attributes()[self.fields['descriptio']].split(",")[4].split(': ')[1])
##                except:
##                    try:
##                        model_altitude.append(f.attributes()[self.fields['Descriptio']].split(",")[4].split(': ')[1])
##                    except:
##                        self.logger.error('model_apply destroy edit session')
##                        self.logger.exception(traceback.format_exc())
##                        self.logger.info('self.fields keys {0}'.format(self.fields.keys))
##                        self.iface.messageBar().pushMessage("Error", "Failed to apply model style parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

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

            self.iface.messageBar().pushMessage("Success", "Model applied to selected points.", level=QgsMessageBar.INFO, duration=5)

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

            self.iface.messageBar().pushMessage("Success", "Icon applied.", level=QgsMessageBar.INFO, duration=5)
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

            self.iface.messageBar().pushMessage("Success", "Label applied.", level=QgsMessageBar.INFO, duration=5)

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

    def tofollow(self):
##            cameraBack = {'a': 'longitude', 'b': 'longitude_off','c': 'latitude','d': 'latitude_off','e': 'altitude' ,'f': 'altitudemode', 'g': 'gxaltitudemode' ,'h': 'gxhoriz' ,'i': 'heading' ,'j': 'roll' ,'k': 'tilt' ,'l': 'range','m': 'follow_angle'}
        try:

            if self.selectedCamera:
                if self.selectedCamera['e']:
                    self.dlg.ui.lineEdit_visualization_follow_altitude.setText(str(self.selectedCamera['e']))
                if self.selectedCamera['f']:
                    altitudemode = [None, 'absolute', 'clampToGround', 'relativeToGround', 'relativeToModel']
                    c = 0
                    for alt in altitudemode:
                        if self.selectedCamera['f'] == alt:
                            self.dlg.ui.comboBox_follow_altitudemode.setCurrentIndex(c)
                        c += 1
                if self.selectedCamera['g']:
                    gxaltitudemode = [None, 'clampToSeaFloor', 'relativeToSeaFloor']
                    c = 0
                    for alt in gxaltitudemode:
                        if self.selectedCamera['g'] == alt:
                            self.dlg.ui.comboBox_follow_gxaltitudemode.setCurrentIndex(c)
                        c += 1

                if self.selectedCamera['h']:
                    self.dlg.ui.lineEdit__visualization_follow_gxhoriz.setText(str(self.selectedCamera['h']))
                if self.selectedCamera['k']:
                    self.dlg.ui.lineEdit__visualization_follow_tilt.setText(str(self.selectedCamera['k']))
                if self.selectedCamera['l']:
                    self.dlg.ui.lineEdit__visualization_follow_range.setText(str(self.selectedCamera['l']))
                if self.selectedCamera['m']:
                    self.dlg.ui.lineEdit__visualization_follow_follow_angle.setText(str(self.selectedCamera['m']))
                self.iface.messageBar().pushMessage("Success", "Applied the camera settings to the follow tab fields", level=QgsMessageBar.INFO, duration=5)

        except:
            if self.logging == True:
                self.logger.error('tofollow')
                self.logger.exception(traceback.format_exc())
            self.iface.messageBar().pushMessage("Error", "Failed to create tofollow. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)



    def tocustom(self):
##            cameraBack = {'a': 'longitude', 'b': 'longitude_off','c': 'latitude','d': 'latitude_off','e': 'altitude' ,'f': 'altitudemode', 'g': 'gxaltitudemode' ,'h': 'gxhoriz' ,'i': 'heading' ,'j': 'roll' ,'k': 'tilt' ,'l': 'range','m': 'follow_angle'}
        try:

            if self.selectedCamera:
                if self.selectedCamera['a']:
                    self.dlg.ui.lineEdit_visualization_camera_longitude.setText(str(self.selectedCamera['a']))
                if self.selectedCamera['b']:
                    self.dlg.ui.lineEdit_visualization_camera_longitude_off.setText(str(self.selectedCamera['b']))
                if self.selectedCamera['c']:
                    self.dlg.ui.lineEdit_visualization_camera_latitude.setText(str(self.selectedCamera['c']))
                if self.selectedCamera['d']:
                    self.dlg.ui.lineEdit_visualization_camera_latitude_off.setText(str(self.selectedCamera['d']))
                if self.selectedCamera['e']:
                    self.dlg.ui.lineEdit_visualization_camera_altitude.setText(str(self.selectedCamera['e']))
                if self.selectedCamera['f']:
                    altitudemode = [None, 'absolute', 'clampToGround', 'relativeToGround', 'relativeToModel']
                    c = 0
                    for alt in altitudemode:
                        if self.selectedCamera['f'] == alt:
                            self.dlg.ui.comboBox_altitudemode.setCurrentIndex(c)
                        c += 1
                if self.selectedCamera['g']:
                    gxaltitudemode = [None, 'clampToSeaFloor', 'relativeToSeaFloor']
                    c = 0
                    for alt in gxaltitudemode:
                        if self.selectedCamera['g'] == alt:
                            self.dlg.ui.comboBox_gxaltitudemode.setCurrentIndex(c)
                        c += 1

                if self.selectedCamera['h']:
                    self.dlg.ui.lineEdit__visualization_camera_gxhoriz.setText(str(self.selectedCamera['h']))
                if self.selectedCamera['i']:
                    self.dlg.ui.lineEdit__visualization_camera_heading.setText(str(self.selectedCamera['i']))
                if self.selectedCamera['j']:
                    self.dlg.ui.lineEdit__visualization_camera_roll.setText(str(self.selectedCamera['j']))
                if self.selectedCamera['k']:
                    self.dlg.ui.lineEdit__visualization_camera_tilt.setText(str(self.selectedCamera['k']))

                self.iface.messageBar().pushMessage("Success", "Applied the camera settings to the custom tab fields", level=QgsMessageBar.INFO, duration=5)

        except:
            if self.logging == True:
                self.logger.error('tofollow')
                self.logger.exception(traceback.format_exc())
            self.iface.messageBar().pushMessage("Error", "Failed to create tofollow. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


    def camera_symbolize(self):

#            cameraBack = {'e': 'altitude' ,'f': 'altitudemode', 'g': 'gxaltitudemode' ,'h': 'gxhoriz' ,'i': 'heading' ,'j': 'roll' ,'k': 'tilt' ,'l': 'range','m': 'follow_angle'}

        try:
            self.fields = self.field_indices(self.ActiveLayer)   #symbcamera
            allfids = self.ActiveLayer.allFeatureIds()

##                shaper.startEditing()
##                shaper.beginEditCommand('datetime')
##                for i,v in enumerate(fid_dt):
##                    shaper.changeAttributeValue(i, idx, v)
##                shaper.endEditCommand()
##                shaper.commitChanges()



            allfeats1 = self.ActiveLayer.getFeatures()

            featlist = []
            for feat1 in allfeats1:
                featlist.append([feat1.attributes(),feat1.id()])
            allfeats = self.ActiveLayer.getFeatures()
            cnt = 0; cntatt = 0;
            for feat in allfeats:
                if cnt > 0:
                    currentatt = feat.attributes(); lastatt = featlist[cnt-1][0]
                    if currentatt:
                        if currentatt[self.fields['flyto']] and currentatt[self.fields['camera']]:
                            #self.logger.info('here@@@@@@ {0}, {1}'.format(currentatt[self.fields['flyto']],currentatt[self.fields['camera']]))
                            flytodict = eval(currentatt[self.fields['flyto']])
                            cameradict = eval(currentatt[self.fields['camera']])
                            flytodict.pop('a',None);flytodict.pop('b',None);flytodict.pop('c',None);flytodict.pop('d',None);
                            cameradict.pop('a',None);cameradict.pop('b',None);cameradict.pop('c',None);cameradict.pop('d',None);cameradict.pop('i',None);
                            # not look at the last row
                            if lastatt:

                                if lastatt[self.fields['flyto']] and lastatt[self.fields['camera']]:
                                    flytodict2 = eval(lastatt[self.fields['flyto']])
                                    cameradict2 = eval(lastatt[self.fields['camera']])
                                    flytodict2.pop('a',None);flytodict2.pop('b',None);flytodict2.pop('c',None);flytodict2.pop('d',None);
                                    cameradict2.pop('a',None);cameradict2.pop('b',None);cameradict2.pop('c',None);cameradict2.pop('d',None);cameradict2.pop('i',None);
                                    if cmp(cameradict,cameradict2) == 0: # they are the same
                                        pass
                                    else:
                                        cntatt += 1

                            if flytodict and cameradict:
                                name = flytodict['name'] + "_" + str(cntatt)
                                if name:
                                    self.ActiveLayer.changeAttributeValue(feat.id(), self.fields['symbtour'], str(name))
                cnt += 1

            self.iface.messageBar().pushMessage("Success", "Applied tour name to the 'symbcamera' field. Use these categories for symbolization.", level=QgsMessageBar.INFO, duration=5)
        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('camera_symbolize')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to create symbolization for the camera tour(s). Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)



    def lookat_apply(self):
        try:
            self.fields = self.field_indices(self.ActiveLayer)
            # make a dictionary of all of the camera parameters
            flyto = {'name': None, 'flyToMode': None, 'duration': None}
            lookat = {'longitude': None, 'latitude': None, 'altitude' : None, 'altitudemode': None,'gxaltitudemode' : None,'heading' : None,'tilt' : None, 'range': None, 'duration': None, 'startheading': None, 'rotations': None, 'direction': None}
            lookatAlpha = {'longitude': 'a', 'latitude': 'b', 'altitude' : 'c', 'altitudemode': 'd','gxaltitudemode' : 'e','heading' : 'f','tilt' : 'g', 'range': 'h', 'duration': 'i', 'startheading': 'j', 'rotations': 'k', 'l': 'direction'}
            lookattemp = {}

            flyto['name'] = self.dlg.ui.lineEdit_tourname.text()
            flyto['flyToMode'] = self.dlg.ui.comboBox_flyto_mode.currentText()
            flyto['duration'] = self.dlg.ui.lineEdit_flyto_duration.text()

            lookat['altitude'] = self.dlg.ui.lineEdit_visualization_lookat_altitude.text()
            lookat['altitudemode'] = self.dlg.ui.comboBox_lookat_altitudemode.currentText()
            lookat['gxaltitudemode'] = self.dlg.ui.comboBox_lookat_gxaltitudemode.currentText()
            lookat['range'] = self.dlg.ui.lineEdit__visualization_lookat_range.text()
            lookat['heading'] = self.dlg.ui.lineEdit__visualization_lookat_heading.text()
            lookat['tilt'] = self.dlg.ui.lineEdit__visualization_lookat_tilt.text()


            # calculate heading
            cordslist = []  # alist of tuples. [(x,y), (x,y)]
            altitudelist = []
            self.selectList = []  #[[id, (x,y), altitude]]
            selectflyto = []

            try:
                for f in self.ActiveLayer.selectedFeatures():          #getFeatures():
                    geom = f.geometry()
                    if lookat['altitudemode'] == 'relativeToModel':
                        modelfield = eval(f.attributes()[self.fields['model']])
                        if not lookat['altitude']:
                            alt = 0
                        else:
                            alt = float(lookat['altitude'])
                        altitudelist.append(float(modelfield['altitude']) + alt)
                        altinum = float(modelfield['altitude']) + alt
                        self.selectList.append([f.id(), geom.asPoint(), round(altinum,2)])
                    else:
                        self.selectList.append([f.id(), geom.asPoint()])
                # sort self.selectList by fid
                def getKey(item):
                    return item[0]
                self.selectList = sorted(self.selectList, key=getKey)  #[[id, (x,y), altitude]]
            except:
                self.logger.exception(traceback.format_exc())
                self.iface.messageBar().pushMessage("Error", "Failed to apply lookat view parameters for Follow Tour. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

            try:
                self.ActiveLayer.beginEditCommand("LookAt Editing")
                if len(self.selectList) >= 1:
                    self.ActiveLayer.beginEditCommand("LookAt Editing")
                    for i,f in enumerate(self.selectList):
                        if len(f) == 3:
                            lookat['altitude'] = f[2]
                        lookat['longitude'] = f[1][0]; lookat['latitude'] = f[1][1]
                        for key,value in lookat.iteritems():
                            lookattemp[lookatAlpha[key]] = value
                        self.ActiveLayer.changeAttributeValue(f[0], self.fields['lookat'], str(lookattemp))
                        self.ActiveLayer.changeAttributeValue(f[0], self.fields['flyto'], str(flyto))
                        self.ActiveLayer.changeAttributeValue(f[0], self.fields['camera'], '')
                    self.ActiveLayer.endEditCommand()
                else:
                    QMessageBox.warning( self.iface.mainWindow(),"Active Layer Warning", "Please select points in the active layer to be edited." )
            except:
                self.ActiveLayer.destroyEditCommand()
                self.logger.error('lookat_apply destroy edit session')
                self.logger.exception(traceback.format_exc())
                self.iface.messageBar().pushMessage("Error", "Failed to apply lookat view parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

            self.iface.messageBar().pushMessage("Success", "LookAt applied, any conflicting Camera removed.", level=QgsMessageBar.INFO, duration=5)

        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('lookat_apply function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to apply lookat view parameters for Follow Tour. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


    def circle_apply(self):

        try:

            self.durationpopulate()
            self.fields = self.field_indices(self.ActiveLayer)
            # make a dictionary of all of the camera parameters
            flyto = {'name': None, 'flyToMode': None, 'duration': None}
            lookat = {'longitude': None, 'latitude': None, 'altitude' : None, 'altitudemode': None,'gxaltitudemode' : None,'heading' : None,'tilt' : None, 'range': None, 'duration': None, 'startheading': None, 'rotations': None, 'direction': None}
            lookatAlpha = {'longitude': 'a', 'latitude': 'b', 'altitude' : 'c', 'altitudemode': 'd','gxaltitudemode' : 'e','heading' : 'f','tilt' : 'g', 'range': 'h', 'duration': 'i', 'startheading': 'j', 'rotations': 'k', 'direction': 'l'}
            lookattemp = {}

            flyto['name'] = self.dlg.ui.lineEdit_tourname.text()
            flyto['flyToMode'] = self.dlg.ui.comboBox_flyto_mode.currentText()
            flyto['duration'] = self.dlg.ui.lineEdit_flyto_duration.text()

            lookat['altitude'] = self.dlg.ui.lineEdit_visualization_circle_altitude.text()
            lookat['altitudemode'] = self.dlg.ui.comboBox_circle_altitudemode.currentText()
            lookat['gxaltitudemode'] = self.dlg.ui.comboBox_circle_gxaltitudemode.currentText()
            lookat['range'] = self.dlg.ui.lineEdit__visualization_circle_range.text()
            lookat['tilt'] = self.dlg.ui.lineEdit__visualization_circle_tilt.text()
            lookat['duration'] = self.dlg.ui.lineEdit__visualization_circle_duration.text()
            lookat['startheading'] = self.dlg.ui.lineEdit__visualization_circle_start_heading.text()
            lookat['rotations'] = self.dlg.ui.lineEdit__visualization_circle_rotations.text()
            lookat['direction'] = self.dlg.ui.comboBox_visualization_direction.currentText()

            # calculate heading
            cordslist = []  # alist of tuples. [(x,y), (x,y)]
            altitudelist = []
            self.selectList = []  #[[id, (x,y), altitude]]
            selectflyto = []
            xlist = []
            ylist = []

            conflict = (False, None) # is there a conflict with an existing circle around???
            try:
                for f in self.ActiveLayer.selectedFeatures():          #getFeatures():
                    geom = f.geometry()
                    clookat = f.attributes()[self.fields['lookat']]
                    if clookat == 'circlearound':
                        conflict = (True, f.id())
                    if lookat['altitudemode'] == 'relativeToModel':
                        modelfield = eval(f.attributes()[self.fields['model']])
                        if not lookat['altitude']:
                            alt = 0
                        else:
                            alt = float(lookat['altitude'])
                        altitudelist.append(float(modelfield['altitude']) + alt)
                        altinum = float(modelfield['altitude']) + alt
                        self.selectList.append([f.id(), geom.asPoint(), round(altinum,2)])
                        xlist.append(geom.asPoint()[0]); ylist.append(geom.asPoint()[1])
                    else:
                        self.selectList.append([f.id(), geom.asPoint()])
                        xlist.append(geom.asPoint()[0]); ylist.append(geom.asPoint()[1])
                # sort self.selectList by fid
                def getKey(item):
                    return item[0]
                self.selectList = sorted(self.selectList, key=getKey)  #[[id, (x,y), altitude]]

                #calculate the centroid
                BigXY = (round(np.mean(xlist),5),round(np.mean(ylist),5))


            except:
                self.logger.exception(traceback.format_exc())
                self.iface.messageBar().pushMessage("Error", "Failed to apply lookat view parameters for Follow Tour. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

            if conflict[0]:

                # find the indices of the last lookat flyto
                self.cLayer = self.iface.mapCanvas().currentLayer()
                AllList = []
                allfeats = self.cLayer.getFeatures()
                for feat in allfeats:
                    cff = feat.attributes()[self.fields['lookat']]
                    AllList.append([feat.id(), cff])
                # sort self.selectList by fid
                def getKey(item):
                    return item[0]
                AllList = sorted(AllList, key=getKey)

                circleList = []
                for ii,vv in enumerate(AllList):
                    if vv[1]:
                        if vv[1][0] == '{' or vv[1] == 'circlearound':
                            circleList.append(vv[0])

                #self.logger.info('circleList {0}'.format(circleList))

                circArr = []
                lenc = len(circleList)-1
                for dd,gg in enumerate(circleList):
                    try:
                        if dd == lenc:
                            diff = int(gg) - int(circleList[dd-1])
                        else:
                            diff = int(circleList[dd+1]) - int(gg)
                        if diff == 1:
                            if not 'seq' in locals():
                                seq = []
                            if dd == lenc:
                                seq.append(gg)
                            else:
                                seq.append(gg); seq.append(circleList[dd+1])
                                #self.logger.info('seq {0}'.format(seq))
                        else:
                            try:
                                circArr.append(seq)
                                del seq
                            except:
                                #self.logger.info(traceback.format_exc())
                                del seq
                        if diff == 1 and dd == lenc:
                            try:
                                circArr.append(seq)
                            except:
                                pass


                    except:
                        self.logger.info(traceback.format_exc())

                #self.logger.info('circArr {0}'.format(circArr))

                # check wich ones will be reset
                for val in circArr:
                    for v in val:
                        if conflict[1] == v:
                            BadOnes = val

                circleMsg = QMessageBox(self.iface.mainWindow())
                circleMsg.setWindowTitle('Circle Around Conflict')
                circleMsg.setText('A circle around already exists. Overwriting will delete the conflicting circle around. Overwrite or cancel?')
                circleMsg.addButton(QPushButton('Overwrite'), QMessageBox.YesRole)
                #circleMsg.addButton(QPushButton('Reject'), QMessageBox.NoRole)
                circleMsg.addButton(QPushButton('Cancel'), QMessageBox.RejectRole)
                ret = circleMsg.exec_();
                circleMsgCB = circleMsg.clickedButton()

                if ret == 0:
                    #erase the conflict
                    self.ActiveLayer.beginEditCommand("LookAt Editing Remove Conflict")
                    for i,f in enumerate(BadOnes):
                        self.ActiveLayer.changeAttributeValue(f, self.fields['flyto'], '')
                        self.ActiveLayer.changeAttributeValue(f, self.fields['camera'], '')
                        self.ActiveLayer.changeAttributeValue(f, self.fields['lookat'], '')
                    self.ActiveLayer.endEditCommand()

            else:
                ret = 0

            if ret == 0:

                try:
                    self.ActiveLayer.beginEditCommand("LookAt Editing")
                    if len(self.selectList) >= 1:
                        self.ActiveLayer.beginEditCommand("LookAt Editing")
                        for i,f in enumerate(self.selectList):
                            if i == 0:
                                if len(f) == 3:
                                    lookat['altitude'] = f[2]
                                lookat['longitude'] = BigXY[0]; lookat['latitude'] = BigXY[1]
                                for key,value in lookat.iteritems():
                                    lookattemp[lookatAlpha[key]] = value
                                self.ActiveLayer.changeAttributeValue(f[0], self.fields['lookat'], str(lookattemp))
                                self.ActiveLayer.changeAttributeValue(f[0], self.fields['flyto'], str(flyto))
                                self.ActiveLayer.changeAttributeValue(f[0], self.fields['camera'], '')
                            else: # clear out the opposing cameras and flyto's
                                self.ActiveLayer.changeAttributeValue(f[0], self.fields['flyto'], '')
                                self.ActiveLayer.changeAttributeValue(f[0], self.fields['camera'], '')
                                self.ActiveLayer.changeAttributeValue(f[0], self.fields['lookat'], 'circlearound')
                        self.ActiveLayer.endEditCommand()
                    else:
                        QMessageBox.warning( self.iface.mainWindow(),"Active Layer Warning", "Please select points in the active layer to be edited." )
                except:
                    self.ActiveLayer.destroyEditCommand()
                    self.logger.error('lookat_apply destroy edit session')
                    self.logger.exception(traceback.format_exc())
                    self.iface.messageBar().pushMessage("Error", "Failed to apply lookat view parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

                self.iface.messageBar().pushMessage("Success", "Circle Around applied, any conflicting Camera removed.", level=QgsMessageBar.INFO, duration=5)

            else:
                self.iface.messageBar().pushMessage("Canceled", "Circle Around Canceled.", level=QgsMessageBar.INFO, duration=5)


        except:
            global NOW, pointid, ClockDateTime
            NOW = None; pointid = None; ClockDateTime = None
            trace = traceback.format_exc()
            if self.logging == True:
                self.logger.error('lookat_apply function error')
                self.logger.exception(trace)
            self.iface.messageBar().pushMessage("Error", "Failed to apply lookat view parameters for Follow Tour. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


    def follow_apply(self):
        try:
            self.fields = self.field_indices(self.ActiveLayer)
            # make a dictionary of all of the camera parameters
            camera = {'longitude': None, 'longitude_off': None, 'latitude': None, 'latitude_off': None, 'altitude' : None, 'altitudemode': None,'gxaltitudemode' : None,'gxhoriz' : None,'heading' : None,'roll' : None,'tilt' : None, 'range': None, 'follow_angle': None, 'streetview': None}
            cameraAlpha = {'longitude': 'a', 'longitude_off': 'b', 'latitude': 'c', 'latitude_off': 'd', 'altitude' : 'e', 'altitudemode': 'f','gxaltitudemode' : 'g','gxhoriz' : 'h','heading' : 'i','roll' : 'j','tilt' : 'k', 'range': 'l', 'follow_angle': 'm', 'streetview': 'n'}
            cameraBack = {'a': 'longitude', 'b': 'longitude_off','c': 'latitude','d': 'latitude_off','e': 'altitude' ,'f': 'altitudemode', 'g': 'gxaltitudemode' ,'h': 'gxhoriz' ,'i': 'heading' ,'j': 'roll' ,'k': 'tilt' ,'l': 'range','m': 'follow_angle', 'n': 'streetview'}

            cameratemp = {}
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
            #if self.dlg.ui.checkBox_visualization_follow_streetview.isChecked():
                #camera['streetview'] = True

            # Calculate Heading !! Select All Features in the Current Layer !!
            forward_int = int(self.dlg.ui.lineEdit__visualization_follow_smoother.text())  # default to 1
            hoffset = float(self.dlg.ui.lineEdit__visualization_follow_hoffset.text())
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

                    try:
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
                    except:
                        QMessageBox.warning( self.iface.mainWindow(),"Follow Behind Error", "Models have not been added. Please add models ('Placemarks' tab), and try again." )

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

##                for bb in newlistwithflyto:
##                    self.logger.info(bb)

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
                    headinglist.append((TeatDip.mean_angle(forwardlist) + hoffset) % 360)
                    #headinglist.append(TeatDip.compass_bearing((cordslist[i-1][1] , cordslist[i-1][0]), (v[1],v[0])) )
                else:
                    headinglist.append(headinglist[i-1])
            self.logger.info('HEADINGLIST: {0}'.format(headinglist))

            try:
                if len(self.selectList) >= 1:
                    self.ActiveLayer.startEditing()
                    self.ActiveLayer.beginEditCommand("Camera Editing")
                    for i,f in enumerate(self.selectList):   #[[id, (x,y), altitude]]
                        #self.logger.info('enum {0} {1}'.format(i,f))
                        if len(f) == 3:
                            camera['altitude'] = f[2]
                        camera['heading'] = round(headinglist[i],1)
                        camera['longitude'] = f[1][0]; camera['latitude'] = f[1][1]

                        #convert to cameratemp
                        for key,value in camera.iteritems():
                            cameratemp[cameraAlpha[key]] = value

                        self.ActiveLayer.changeAttributeValue(f[0], self.fields['camera'], str(cameratemp))
                        self.ActiveLayer.changeAttributeValue(f[0], self.fields['flyto'], str(newlistwithflyto[i]))
                        self.ActiveLayer.changeAttributeValue(f[0], self.fields['lookat'], '') # get rid of lookats
                    self.ActiveLayer.endEditCommand()
                else:
                    QMessageBox.warning( self.iface.mainWindow(),"Active Layer Warning", "Please select points in the active layer to be edited." )
            except:
                self.ActiveLayer.destroyEditCommand()
                self.logger.error('follow_apply error.')
                self.logger.exception(traceback.format_exc())
                self.iface.messageBar().pushMessage("Error", "Failed to apply camera view parameters for Follow Tour. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

            self.iface.messageBar().pushMessage("Success", "Follow Behind applied, any conflicting Lookat removed", level=QgsMessageBar.INFO, duration=5)


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
                self.dlg.ui.lineEdit__visualization_follow_hoffset.setEnabled(True)

                # LookAt
                self.dlg.ui.lineEdit_visualization_lookat_altitude.setEnabled(True)
                self.dlg.ui.comboBox_lookat_altitudemode.setEnabled(True)
                self.dlg.ui.comboBox_lookat_gxaltitudemode.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_lookat_range.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_lookat_heading.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_lookat_tilt.setEnabled(True)
                self.dlg.ui.pushButton_lookat_apply.setEnabled(True)

                # Circle Around
                #self.dlg.ui.lineEdit_visualization_circle_altitude.setEnabled(True)
                self.dlg.ui.comboBox_circle_altitudemode.setEnabled(True)
                self.dlg.ui.comboBox_circle_gxaltitudemode.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_circle_tilt.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_circle_range.setEnabled(True)
                #self.dlg.ui.lineEdit__visualization_circle_duration.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_circle_start_heading.setEnabled(True)
                self.dlg.ui.lineEdit__visualization_circle_rotations.setEnabled(True)
                self.dlg.ui.pushButton_circle_apply.setEnabled(True)
                self.dlg.ui.comboBox_visualization_direction.setEnabled(True)

                # Symbolize Select
                self.dlg.ui.pushButton_visualization_camera_symbolize.setEnabled(True)
                self.dlg.ui.pushButton_visualization_camera_tofollow.setEnabled(True)
                self.dlg.ui.pushButton_visualization_camera_tocustom.setEnabled(True)


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
            self.dlg.ui.lineEdit__visualization_follow_hoffset.setEnabled(False)

            # LookAt
            self.dlg.ui.lineEdit_visualization_lookat_altitude.setEnabled(False)
            self.dlg.ui.comboBox_lookat_altitudemode.setEnabled(False)
            self.dlg.ui.comboBox_lookat_gxaltitudemode.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_lookat_range.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_lookat_heading.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_lookat_tilt.setEnabled(False)
            self.dlg.ui.pushButton_lookat_apply.setEnabled(False)

            # Circle Around
            self.dlg.ui.lineEdit_visualization_circle_altitude.setEnabled(False)
            self.dlg.ui.comboBox_circle_altitudemode.setEnabled(False)
            self.dlg.ui.comboBox_circle_gxaltitudemode.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_circle_tilt.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_circle_range.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_circle_duration.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_circle_start_heading.setEnabled(False)
            self.dlg.ui.lineEdit__visualization_circle_rotations.setEnabled(False)
            self.dlg.ui.pushButton_circle_apply.setEnabled(False)
            self.dlg.ui.comboBox_visualization_direction.setEnabled(False)

            # Symbolize Select
            self.dlg.ui.pushButton_visualization_camera_symbolize.setEnabled(False)
            self.dlg.ui.pushButton_visualization_camera_tofollow.setEnabled(False)
            self.dlg.ui.pushButton_visualization_camera_tocustom.setEnabled(False)



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
            flyto = {'name': None, 'flyToMode': None, 'duration': None}
            camera = {'longitude': None, 'longitude_off': None, 'latitude': None, 'latitude_off': None, 'altitude' : None, 'altitudemode': None,'gxaltitudemode' : None,'gxhoriz' : None,'heading' : None,'roll' : None,'tilt' : None, 'range': None, 'follow_angle': None}
            cameraAlpha = {'longitude': 'a', 'longitude_off': 'b', 'latitude': 'c', 'latitude_off': 'd', 'altitude' : 'e', 'altitudemode': 'f','gxaltitudemode' : 'g','gxhoriz' : 'h','heading' : 'i','roll' : 'j','tilt' : 'k', 'range': 'l', 'follow_angle': 'm', 'streetview': 'n'}


            cameratemp = {}

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

##            camera['a'] = self.dlg.ui.lineEdit_visualization_camera_longitude.text()
##            camera['b'] = self.dlg.ui.lineEdit_visualization_camera_longitude_off.text()
##            camera['c'] = self.dlg.ui.lineEdit_visualization_camera_latitude.text()
##            camera['d'] = self.dlg.ui.lineEdit_visualization_camera_latitude_off.text()
##            camera['e'] = self.dlg.ui.lineEdit_visualization_camera_altitude.text()
##            camera['f'] = self.dlg.ui.comboBox_altitudemode.currentText()
##            camera['g'] = self.dlg.ui.comboBox_gxaltitudemode.currentText()
##            camera['h'] = self.dlg.ui.lineEdit__visualization_camera_gxhoriz.text()
##            camera['i'] = self.dlg.ui.lineEdit__visualization_camera_heading.text()
##            camera['j'] = self.dlg.ui.lineEdit__visualization_camera_roll.text()
##            camera['k'] = self.dlg.ui.lineEdit__visualization_camera_tilt.text()

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
                        #convert to cameratemp
                        for key,value in camera.iteritems():
                            cameratemp[cameraAlpha[key]] = value

                        self.ActiveLayer.changeAttributeValue(f, self.fields['camera'], str(cameratemp))
                        self.ActiveLayer.changeAttributeValue(f, self.fields['flyto'], str(flyto))
                        self.ActiveLayer.changeAttributeValue(f, self.fields['lookat'], '') # get rid of lookats
                    #self.ActiveLayer.updateFields()
                    self.ActiveLayer.endEditCommand()
                else:
                    QMessageBox.warning( self.iface.mainWindow(),"Active Layer Warning", "Please select points in the active layer to be edited." )
            except:
                self.ActiveLayer.destroyEditCommand()
                self.logger.error('camera_apply destroy edit session')
                self.logger.exception(traceback.format_exc())
                self.iface.messageBar().pushMessage("Error", "Failed to apply camera view parameters. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)

            self.iface.messageBar().pushMessage("Success", "Camera applied, any conflicting LookAt removed.", level=QgsMessageBar.INFO, duration=5)

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
                shaper.dataProvider().addAttributes( [QgsField("datetime",QVariant.String), QgsField("audio",QVariant.String), QgsField("camera",QVariant.String), QgsField("flyto",QVariant.String), QgsField("iconstyle", QVariant.String), QgsField("labelstyle", QVariant.String), QgsField("model", QVariant.String), QgsField("lookat", QVariant.String) , QgsField("symbtour", QVariant.String), QgsField("altitude",QVariant.Double)])
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
                model_altitude = []
                cc = 0
                for f in shaper.getFeatures():
                    currentatt = f.attributes()[0]  # this should be self.fields['Name']
                    pointdate = currentatt.split(" ")[0]  #2014/06/06
                    pointtime = currentatt.split(" ")[1]
                    current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
                    fid_dt.append(current_dt.strftime("%Y/%m/%d %X"))
                    try:
                        model_altitude.append([f.id(), round(float(f.attributes()[self.fields['descriptio']].split(",")[4].split(': ')[1]),2) ])
                    except:
                        try:
                            model_altitude.append([f.id(), round(float(f.attributes()[self.fields['Descriptio']].split(",")[4].split(': ')[1]),2)])
                        except:
                            model_altitude.append([f.id(),None])

                    cc += 1


                shaper.startEditing()
                shaper.beginEditCommand('datetime')
                for i,v in enumerate(fid_dt):
                    shaper.changeAttributeValue(i, idx, v)
                shaper.endEditCommand()
                shaper.commitChanges()

                shaper.startEditing()
                shaper.beginEditCommand('altitude')
                for i,v in enumerate(model_altitude):
                    shaper.changeAttributeValue(v[0], self.fields['altitude'], v[1])
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
        self.audiopath = QFileDialog.getOpenFileName(None, "Import Audio File",self.lastdirectory, "(*.wav *.mp3)")
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
                self.dlg.ui.checkBox_sync_point.setEnabled(True)

                self.line_audiopath = self.dlg.ui.lineEdit_InAudio1.text()
                audioname_ext = self.line_audiopath.split('/')[-1]
                audioname = audioname_ext.split('.')[0]
                file_ext = audioname_ext.split('.')[1]
                # Audio start date and time

                if file_ext.lower() == "wav":
                    w = wave.open(self.line_audiopath)
                    framerate = w.getframerate()
                    frames = w.getnframes()
                    length = frames/framerate # seconds
                if file_ext.lower() == "mp3":
                    mp3 = MP3(self.line_audiopath)
                    length = round(mp3.info.length) # seconds

                self.audio_start = datetime.datetime(int(audioname[0:4]), int(audioname[4:6]), int(audioname[6:8]), int(audioname[8:10]), int(audioname[10:12]), int(audioname[12:14]))
                # Audio end time. Add seconds to the start time
                self.audio_end = self.audio_start + datetime.timedelta(seconds=length)
                self.iface.messageBar().pushMessage("Success", "Audio file imported and ready to play: {0}".format(self.audiopath), level=QgsMessageBar.INFO, duration=5)
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
                self.dlg.ui.checkBox_sync_point.setEnabled(False)
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
        global NOW, pointid, ClockDateTime, AllList, pause  # [[fid, dt],...]

        if NOW and pointid >=0 and ClockDateTime:
            try:

                # check if the time difference is larger than 1 between points
                if pointid <= (len(AllList)-2):
                    allDT = AllList[pointid][1]
                    allDTnext = AllList[pointid+1][1]
                    diff = allDTnext - allDT
                    diffsec = diff.seconds
                else:
                    diffsec = 1

                # Clock Time and Duration
                ClockTime_delta = ClockDateTime + datetime.timedelta(seconds=1)
                diff_sec = ClockDateTime - self.audio_start
                faker = datetime.datetime(2014,1,1,0,0,0) + datetime.timedelta(seconds=diff_sec.seconds)
                self.lcd1_C.display(ClockTime_delta.strftime("%H:%M:%S"))
                self.lcd1_D.display(faker.strftime("%H:%M:%S"))
                ClockDateTime = ClockTime_delta

                pauseBreak = diff.seconds

                if diffsec == 1:

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
                    pause = 0

                elif diffsec > 1 and pause == pauseBreak:
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
                    pause = 0

                else:
                    pause += 1

                #self.logger.info('pause: {0}, pauseBreak {1}, diffseconds: {2}'.format(pause, pauseBreak, diff.seconds))

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
        global AllList
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

                # get all the features and make a list of [[fid, datetime]]
                AllList = []
                allfeats = self.cLayer.getFeatures()
                for feat in allfeats:
                    currentatt = feat.attributes()
                    pointdate = currentatt[self.fields['datetime']].split(" ")[0]  #2014/06/06
                    pointtime = currentatt[self.fields['datetime']].split(" ")[1]
                    current_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
                    AllList.append([feat.id(), current_dt])
                # sort self.selectList by fid
                def getKey(item):
                    return item[0]
                AllList = sorted(AllList, key=getKey)

                try:
                    features = self.cLayer.selectedFeatures()
                    for f in features:
                        selectList.append(f.attributes())   #[u'2014/06/06 10:30:10', u'Time:10:30:10, Latitude: 39.966531, Longitude: -75.172003, Speed: 3.382047, Altitude: 1.596764']
                        fid = f.id()
                except AttributeError:
                    QMessageBox.warning( self.iface.mainWindow(),"Selected Layer Warning", "Please select the layer and starting point where you would like the audio to start." )

                if len(selectList) == 1:
                    pointid = fid
                    pointdate = selectList[0][self.fields['datetime']].split(" ")[0]  #2014/06/06
                    pointtime = selectList[0][self.fields['datetime']].split(" ")[1]  #10:30:10

                    # global date and time for the selected point
                    ClockDateTime = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))
                    # local date and time for the selected point
                    selected_dt = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]))

                    # Start the video using VLC Media player. Start the video at the specified time
                    # in the video file...

                    file_ext = self.line_audiopath.split('.')[1]
                    # Audio start date and time

                    if file_ext.lower() == "wav":
                        w = wave.open(self.line_audiopath)
                        framerate = w.getframerate()
                        frames = w.getnframes()
                        length = frames/framerate # seconds
                    if file_ext.lower() == "mp3":
                        mp3 = MP3(self.line_audiopath)
                        length = round(mp3.info.length) # seconds

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
                    #self.logger.info('jumptime: {0}, ClockDateTime'.format(jumptime, ClockDateTime))
                else:
                    pass
                    #self.logger.info('Out selectList: {0}'.format(selectList))

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
                            matchrow = []
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
                                matchrow = cc
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

                        at_time = None
                        if matchrow == 0:
                            at_time = True
                        else:
                            at_time = False

                        QMessageBox.information(self.iface.mainWindow(),"Audio File Sync Info", 'Audio Start: {0}\nTrack Start: {1}\nStart point in track is FID: {2}, Row #: {3}\nCoordinates: {4}\n\nAudio & Track Start Time Match: {5}'.format(self.audio_start.strftime("%x %X"),track_start_dt.strftime("%x %X"), matchdict['fid'],matchrow, str(matchdict['coordinates']),at_time ) )

                        if self.dlg.ui.checkBox_sync_point.isChecked():
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

                            # define the layer properties as a dict
                            size2 = float(symbol_layerq.size()) * 2
                            properties = {'size': str(size2), 'color': '0,0,255,255'}

                            # initalise a new symbol layer with those properties
                            symbol_layer = QgsSimpleMarkerSymbolLayerV2.create(properties)

                            # replace the default symbol layer with the new symbol layer
                            vl.rendererV2().symbols()[0].changeSymbolLayer(0, symbol_layer)
                            vl.setLayerTransparency(30)
                            vl.commitChanges()
                            # update layer's extent when new features have been added  # because change of extent in provider is not propagated to the layer
                            vl.updateExtents()
                            #starting_point_marker = self.iface.addVectorLayer('memory/' + vl)     #self.iface.QgsMapLayerRegistry.instance().addMapLayer(vl)
                            #starting_point_marker = self.iface.addVectorLayer(vl, 'layername', "ogr")
                            QgsMapLayerRegistry.instance().addMapLayer(vl)
                        self.iface.setActiveLayer(self.aLayer)

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
                self.audio_export = QFileDialog.getOpenFileName(None, "Choose audio file for .kmz export", self.lastdirectory, "(*.wav *.mp3")  #C:\Users\Edward\Documents\Philly250\Scratch
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



    def exportToFile(self):

        try:
            self.utmzone = 26918 #UTM 18N
            cc = 0
            kml = simplekml.Kml()

            self.fields = self.field_indices(self.ActiveLayer)
            #################################
            ## Tour and Camera

            for f in self.ActiveLayer.getFeatures(): #  QgsFeatureIterator #[u'2014/06/06 10:38:48', u'Time:10:38:48, Latitude: 39.965949, Longitude: -75.172239, Speed: 0.102851, Altitude: -3.756733']
                currentatt = f.attributes()

                if currentatt[self.fields['lookat']] and currentatt[self.fields['lookat']] != 'circlearound':
                    lookatBack = {'a':'longitude','b' :'latitude','c' :'altitude','d' :'altitudemode','e':'gxaltitudemode','f':'heading','g':'tilt','h' :'range','i' :'duration','j' :'startheading', 'k': 'rotations', 'l': 'direction'}
                    lookat = eval(currentatt[self.fields['lookat']])
                    #convert back to full format
                    newlookat = {}
                    for kk,vv in lookat.iteritems():
                        newlookat[lookatBack[kk]] = vv
                    lookatdict = newlookat

                    flytodict = eval(currentatt[self.fields['flyto']])

                    if cc == 0:

                        # First, put in a <Camera> that matches the same <Camera> at the beginning of the tour, that
                        # there is no strange camera movement at the beginning.

                        #firstcam_pnt = kml.newpoint()
                        kml.document.lookat = simplekml.LookAt()


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
                        self.CamStartTime = current_dt.strftime('%Y-%m-%dT%XZ')

                        # Attach a gx:SoundCue to the playlist and delay playing by 2 second (sound clip is about 4 seconds long)
                        if self.dlg.ui.lineEdit_export_audio.text():
                            soundcue = playlist.newgxsoundcue()
                            soundcue.href = self.dlg.ui.lineEdit_export_audio.text()
                            soundcue.gxdelayedstart = self.audio_offset(self.dlg.ui.lineEdit_export_audio.text())


                        cc += 1


                    ##########################################
                    ##########################################

                    # Start time. Will be used for TimeSpan tags
                    pointdate = currentatt[self.fields['datetime']].split(" ")[0]  #2014/06/06
                    pointtime = currentatt[self.fields['datetime']].split(" ")[1] #10:38:48
                    current_dt_end = datetime.datetime(int(pointdate.split('/')[0]), int(pointdate.split('/')[1]), int(pointdate.split('/')[2]), int(pointtime.split(':')[0]), int(pointtime.split(':')[1]), int(pointtime.split(':')[2]) ) #+ datetime.timedelta(seconds=5)
                    camendtime = current_dt_end.strftime('%Y-%m-%dT%XZ')

                    if lookatdict['startheading'] and lookatdict['rotations']:  # lookatdict['duration']  this is for a circle around
                        if lookatdict['longitude'] and lookatdict['latitude'] and lookatdict['altitude'] and lookatdict['tilt'] and lookatdict['range']:
                            circle_count = int(float(lookatdict['rotations']))
                            if circle_count > 1:
                                divisor = 36  #36
                                bottomnum = (divisor+1) + ((circle_count-1)*divisor)
                                duration = (float(lookatdict['duration']))/bottomnum
                                timsspanDur = (float(lookatdict['duration']))/(circle_count * divisor)
                                #duration = (float(lookatdict['duration']))/(circle_count * divisor)
                            else:
                                divisor = 36
                                duration = (float(lookatdict['duration']))/(circle_count * (divisor+1))
                                timsspanDur = (float(lookatdict['duration']))/(circle_count * divisor)
                            timekeeper = current_dt_end

                            # Loop through Circle Count
                            for x in range(circle_count):
                                # Define the initial heading based on current heading
                                if x == 0:
                                    heading = float(lookatdict['startheading'])
                                    divisor = 37
                                else:
                                    divisor = 36
                                # 360 Degrees/10 = 36 intervals to iterate through
##                                if x == range(circle_count)[-1]:
##                                    divisor = 37
                                for y in range(divisor):
                                    # New Fly To
                                    flyto = playlist.newgxflyto(gxduration=duration)
                                    if flytodict['flyToMode']:
                                        flyto.gxflytomode = flytodict['flyToMode']
                                    flyto.lookat.latitude = lookatdict['latitude']
                                    flyto.lookat.longitude = lookatdict['longitude']
                                    flyto.lookat.altitude =  lookatdict['altitude']
                                    if lookatdict['altitudemode'] == 'absolute':
                                        flyto.lookat.altitudemode = simplekml.AltitudeMode.absolute
                                    if lookatdict['altitudemode'] == 'clampToGround':
                                        flyto.lookat.altitudemode = simplekml.AltitudeMode.clamptoground
                                    if lookatdict['altitudemode'] == 'relativeToGround':
                                        flyto.lookat.altitudemode = simplekml.AltitudeMode.relativetoground
                                    if lookatdict['altitudemode'] == 'relativeToPoint':
                                        flyto.lookat.altitudemode = simplekml.AltitudeMode.relativetoground
                                    if lookatdict['altitudemode'] == 'relativeToModel':
                                        flyto.lookat.altitudemode = simplekml.AltitudeMode.relativetoground
                                    flyto.lookat.tilt = lookatdict['tilt']
                                    flyto.lookat.range = lookatdict['range']
                                    flyto.lookat.heading = heading

                                    # Time Span
                                    flyto.lookat.gxtimespan.begin = self.CamStartTime
                                    flyto.lookat.gxtimespan.end = timekeeper.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

                                    timekeeper = timekeeper + datetime.timedelta(seconds = timsspanDur)

                                    # adjust the heading by 10 degrees
                                    if lookatdict['direction'] == 'clockwise':
                                        heading = (heading + 10) % 360
                                    if lookatdict['direction'] == 'counterclockwise':
                                        heading = (heading - 10) % 360

                    else:  # non circle around, just custom
                        if lookatdict['longitude'] and lookatdict['latitude'] and lookatdict['altitude'] and lookatdict['heading'] and lookatdict['tilt'] and lookatdict['range']:
                            if flytodict['duration']:
                                flyto = playlist.newgxflyto(gxduration=float(flytodict['duration']))
                            else:
                                flyto = playlist.newgxflyto()
                            if flytodict['flyToMode']:
                                flyto.gxflytomode = flytodict['flyToMode']
                            flyto.lookat.longitude = lookatdict['longitude']
                            flyto.lookat.latitude = lookatdict['latitude']
                            flyto.lookat.altitude = lookatdict['altitude']
                            if lookatdict['altitudemode'] == 'absolute':
                                flyto.lookat.altitudemode = simplekml.AltitudeMode.absolute
                            if lookatdict['altitudemode'] == 'clampToGround':
                                flyto.lookat.altitudemode = simplekml.AltitudeMode.clamptoground
                            if lookatdict['altitudemode'] == 'relativeToGround':
                                flyto.lookat.altitudemode = simplekml.AltitudeMode.relativetoground
                            if lookatdict['altitudemode'] == 'relativeToPoint':
                                flyto.lookat.altitudemode = simplekml.AltitudeMode.relativetoground
                            if lookatdict['altitudemode'] == 'relativeToModel':
                                flyto.lookat.altitudemode = simplekml.AltitudeMode.relativetoground
                            flyto.lookat.heading = lookatdict['heading']
                            flyto.lookat.tilt = lookatdict['tilt']
                            flyto.lookat.range = lookatdict['range']
                            if lookatdict['gxaltitudemode']:
                                flyto.lookat.gxaltitudemode = lookatdict['gxaltitudemode']
                            # Time Span
                            flyto.lookat.gxtimespan.begin = self.CamStartTime
                            flyto.lookat.gxtimespan.end = camendtime

                    if cc == 1:  # this is the first thing, not camera
                        kml.document.lookat = flyto.lookat


                    cc+=1


                if currentatt[self.fields['camera']]:
                        # camera = {'longitude': None, 'longitude_off': None, 'latitude': None, 'latitude_off': None,
                        # 'altitude' : None, 'altitudemode': None,'gxaltitudemode' : None,'gxhoriz' : None,
                        # 'heading' : None,'roll' : None,'tilt' : None}

                    if cc == 0:  # establish this as the start of the tour
                        camera = eval(currentatt[self.fields['camera']])
                        cameraBack = {'a': 'longitude', 'b': 'longitude_off','c': 'latitude','d': 'latitude_off','e': 'altitude' ,'f': 'altitudemode', 'g': 'gxaltitudemode' ,'h': 'gxhoriz' ,'i': 'heading' ,'j': 'roll' ,'k': 'tilt' ,'l': 'range','m': 'follow_angle', 'n': 'streetview'}
                        #convert back to full format
                        newcam = {}
                        for kk,vv in camera.iteritems():
                            newcam[cameraBack[kk]] = vv
                        cameradict = newcam

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
                        self.CamStartTime = current_dt.strftime('%Y-%m-%dT%XZ')
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
                        flyto.camera.gxtimespan.begin = self.CamStartTime
                        flyto.camera.gxtimespan.end = camendtime


                        #firstcam_pnt.camera = flyto.camera
                        kml.document.camera = flyto.camera

                        cc += 1

                    else:  # everything after zero camera
                        camera = eval(currentatt[self.fields['camera']])
                        cameraBack = {'a': 'longitude', 'b': 'longitude_off','c': 'latitude','d': 'latitude_off','e': 'altitude' ,'f': 'altitudemode', 'g': 'gxaltitudemode' ,'h': 'gxhoriz' ,'i': 'heading' ,'j': 'roll' ,'k': 'tilt' ,'l': 'range','m': 'follow_angle', 'n': 'streetview'}
                        #convert back to full format
                        newcam = {}
                        for kk,vv in camera.iteritems():
                            newcam[cameraBack[kk]] = vv
                        cameradict = newcam
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
                        flyto.camera.gxtimespan.begin = self.CamStartTime
                        flyto.camera.gxtimespan.end = camendtime

                        # Gx Viewer Options
##                        if cameradict['streetview']:
##                            gxview = simplekml.GxViewerOptions(name=simplekml.GxOption.streetview, enabled = True)


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
                                        #self.logger.info('self.fields keys {0}'.format(self.fields.keys))
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
        self.dlg.ui.txtFeedback.clear()

    def selectFeature(self, point, button):

        try:
            self.fields = self.field_indices(self.ActiveLayer)
            #QMessageBox.information( self.iface.mainWindow(),"Info", "in selectFeature function ININ" )
            # setup the provider select to filter results based on a rectangle
            pntGeom = QgsGeometry.fromPoint(point)
            # scale-dependent buffer of 2 pixels-worth of map units
            pntBuff = pntGeom.buffer( (self.canvas.mapUnitsPerPixel() * 2),0)
            rect = pntBuff.boundingBox()
            # get currentLayer and dataProvider
            cLayer = self.canvas.currentLayer()
            self.ActiveLayer.removeSelection()
            self.ActiveLayer.select(rect,False)

            cameraBack = {'a': 'longitude', 'b': 'longitude_off','c': 'latitude','d': 'latitude_off','e': 'altitude' ,'f': 'altitudemode', 'g': 'gxaltitudemode' ,'h': 'gxhoriz' ,'i': 'heading' ,'j': 'roll' ,'k': 'tilt' ,'l': 'range','m': 'follow_angle', 'n': 'streetview'}
            for f in self.ActiveLayer.selectedFeatures():
                currentatt = f.attributes()
                if currentatt:
                    if currentatt[self.fields['camera']]:
                        cameradict = eval(currentatt[self.fields['camera']])
                        display = ''
                        for key,val in cameradict.iteritems():
                            display = display + str(cameraBack[key]) + ": " + str(val) + "\n"
                        display = display + "Raw: " + currentatt[self.fields['camera']]
                        self.dlg.ui.txtFeedback.setText(display)
                        self.selectedCamera = cameradict


        except:
            if self.logging == True:
                self.logger.error('selectFeature')
                self.logger.exception(traceback.format_exc())
            self.iface.messageBar().pushMessage("Error", "selectFeature error. Please see error log at: {0}".format(self.loggerpath), level=QgsMessageBar.CRITICAL, duration=5)


##


##        layerlist = []
##        layerdatasource = []
##        for layer in self.iface.legendInterface().layers():
##            layerlist.append(layer.name())
##            layerdatasource.append(layer.source())

        #QMessageBox.information( self.iface.mainWindow(),"Info", str(layerlist) + str(layerdatasource) )


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


        # Populate the Visualization Camera Combo boxes
        self.dlg.ui.comboBox_flyto_mode.clear()
        flytomodelist = ['smooth', 'bounce']
        for hh in flytomodelist:
            self.dlg.ui.comboBox_flyto_mode.addItem(hh)

        self.dlg.ui.comboBox_altitudemode.clear()
        self.dlg.ui.comboBox_lookat_altitudemode.clear()
        self.dlg.ui.comboBox_circle_altitudemode.clear()
        altitudemode = ['relativeToModel', 'absolute', 'clampToGround', 'relativeToGround']
        for alt in altitudemode:
            self.dlg.ui.comboBox_altitudemode.addItem(alt)
            self.dlg.ui.comboBox_lookat_altitudemode.addItem(alt)
            self.dlg.ui.comboBox_circle_altitudemode.addItem(alt)

        self.dlg.ui.comboBox_gxaltitudemode.clear()
        self.dlg.ui.comboBox_circle_gxaltitudemode.clear()
        self.dlg.ui.comboBox_lookat_gxaltitudemode.clear()
        gxaltitudemode = [None, 'clampToSeaFloor', 'relativeToSeaFloor']
        for gxalt in gxaltitudemode:
            self.dlg.ui.comboBox_gxaltitudemode.addItem(gxalt)
            self.dlg.ui.comboBox_circle_gxaltitudemode.addItem(gxalt)
            self.dlg.ui.comboBox_lookat_gxaltitudemode.addItem(gxalt)

        # Filtering
        splinelist = ['Quadratic', 'Cubic', '4th Order', '5th Order']
        for spline in splinelist:
            self.dlg.ui.comboBox_filtering_spline.addItem(spline)

        # Follow Behind Combo Boxes
        self.dlg.ui.comboBox_follow_altitudemode.clear()
        for alt in altitudemode:
            self.dlg.ui.comboBox_follow_altitudemode.addItem(alt)

        self.dlg.ui.comboBox_follow_gxaltitudemode.clear()
        for gxalt in gxaltitudemode:
            self.dlg.ui.comboBox_follow_gxaltitudemode.addItem(gxalt)

        # circle around direction combo box
        self.dlg.ui.comboBox_visualization_direction.clear()
        direction = ['clockwise', 'counterclockwise']
        for dir in direction:
            self.dlg.ui.comboBox_visualization_direction.addItem(dir)

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

        # LookAt
        self.dlg.ui.lineEdit_visualization_lookat_altitude.setText(None)
        self.dlg.ui.lineEdit__visualization_lookat_range.setText(None)
        self.dlg.ui.lineEdit__visualization_lookat_heading.setText(None)
        self.dlg.ui.lineEdit__visualization_lookat_tilt.setText(None)

        # Circle Around
        self.dlg.ui.lineEdit_visualization_circle_altitude.setText(None)
        self.dlg.ui.lineEdit__visualization_circle_tilt.setText(None)
        self.dlg.ui.lineEdit__visualization_circle_range.setText(None)
        self.dlg.ui.lineEdit__visualization_circle_duration.setText(None)
        self.dlg.ui.lineEdit__visualization_circle_start_heading.setText(None)
        self.dlg.ui.lineEdit__visualization_circle_rotations.setText(None)

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
        self.dlg.ui.lineEdit__visualization_follow_hoffset.setEnabled(False)

        # LookAt
        self.dlg.ui.lineEdit_visualization_lookat_altitude.setEnabled(False)
        self.dlg.ui.comboBox_lookat_altitudemode.setEnabled(False)
        self.dlg.ui.comboBox_lookat_gxaltitudemode.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_lookat_range.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_lookat_heading.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_lookat_tilt.setEnabled(False)
        self.dlg.ui.pushButton_lookat_apply.setEnabled(False)

        # Circle Around
        self.dlg.ui.lineEdit_visualization_circle_altitude.setEnabled(False)
        self.dlg.ui.comboBox_circle_altitudemode.setEnabled(False)
        self.dlg.ui.comboBox_circle_gxaltitudemode.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_circle_tilt.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_circle_range.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_circle_duration.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_circle_start_heading.setEnabled(False)
        self.dlg.ui.lineEdit__visualization_circle_rotations.setEnabled(False)
        self.dlg.ui.pushButton_circle_apply.setEnabled(False)
        self.dlg.ui.comboBox_visualization_direction.setEnabled(False)

        # Symbolize Select
        self.dlg.ui.pushButton_visualization_camera_symbolize.setEnabled(False)
        self.dlg.ui.pushButton_visualization_camera_tofollow.setEnabled(False)
        self.dlg.ui.pushButton_visualization_camera_tocustom.setEnabled(False)

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

        ###################
        # Filtering
        # filters
        self.dlg.ui.radioButton_filtering_xy.setEnabled(False)
        self.dlg.ui.radioButton_filtering_z.setEnabled(False)
        self.dlg.ui.radioButton_filtering_linear.setEnabled(False)
        self.dlg.ui.label_46.setEnabled(False)
        self.dlg.ui.doubleSpinBox_filtering_xweight.setEnabled(False)
        self.dlg.ui.label_47.setEnabled(False)
        self.dlg.ui.label_66.setEnabled(False)
        self.dlg.ui.doubleSpinBox_filtering_yweight.setEnabled(False)
        self.dlg.ui.label_64.setEnabled(False)
        self.dlg.ui.comboBox_filtering_spline.setEnabled(False)
        self.dlg.ui.label_65.setEnabled(False)
        self.dlg.ui.doubleSpinBox_filtering_spline_weight.setEnabled(False)
        self.dlg.ui.radioButton_filtering_center.setEnabled(False)
        self.dlg.ui.label_63.setEnabled(False)
        self.dlg.ui.doubleSpinBox_filtering_center_weight.setEnabled(False)
        self.dlg.ui.radioButton_filtering_quad.setEnabled(False)
        self.dlg.ui.radioButton_filtering_moving.setEnabled(False)
        self.dlg.ui.spinBox_filtering_moving.setEnabled(False)
        self.dlg.ui.radioButton_filtering_zscale.setEnabled(False)
        self.dlg.ui.label_48.setEnabled(False)
        self.dlg.ui.lineEdit_filtering_min.setEnabled(False)
        self.dlg.ui.label_52.setEnabled(False)
        self.dlg.ui.lineEdit_filtering_max.setEnabled(False)
        # Apply Button
        self.dlg.ui.pushButton_filtering_apply.setEnabled(False)
        self.dlg.ui.checkBox_filtering_showplot.setEnabled(False)
