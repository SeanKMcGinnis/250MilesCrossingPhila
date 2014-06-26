# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Edward\.qgis2\python\plugins\MilkMachine\ui_milkmachine.ui'
#
# Created: Wed Jun 25 22:06:39 2014
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MilkMachine(object):
    def setupUi(self, MilkMachine):
        MilkMachine.setObjectName(_fromUtf8("MilkMachine"))
        MilkMachine.resize(674, 433)
        self.buttonboxOkCancel = QtGui.QDialogButtonBox(MilkMachine)
        self.buttonboxOkCancel.setGeometry(QtCore.QRect(260, 380, 171, 32))
        self.buttonboxOkCancel.setOrientation(QtCore.Qt.Horizontal)
        self.buttonboxOkCancel.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonboxOkCancel.setObjectName(_fromUtf8("buttonboxOkCancel"))
        self.txtFeedback = QtGui.QTextEdit(MilkMachine)
        self.txtFeedback.setGeometry(QtCore.QRect(160, 320, 171, 31))
        self.txtFeedback.setObjectName(_fromUtf8("txtFeedback"))
        self.chkActivate = QtGui.QCheckBox(MilkMachine)
        self.chkActivate.setGeometry(QtCore.QRect(360, 320, 171, 31))
        self.chkActivate.setObjectName(_fromUtf8("chkActivate"))
        self.lineEdit_ImportGPS = QtGui.QLineEdit(MilkMachine)
        self.lineEdit_ImportGPS.setGeometry(QtCore.QRect(160, 40, 271, 31))
        self.lineEdit_ImportGPS.setAutoFillBackground(False)
        self.lineEdit_ImportGPS.setDragEnabled(True)
        self.lineEdit_ImportGPS.setObjectName(_fromUtf8("lineEdit_ImportGPS"))
        self.line = QtGui.QFrame(MilkMachine)
        self.line.setGeometry(QtCore.QRect(50, 220, 431, 16))
        self.line.setFrameShape(QtGui.QFrame.HLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.line.setObjectName(_fromUtf8("line"))
        self.buttonImportGPS = QtGui.QPushButton(MilkMachine)
        self.buttonImportGPS.setGeometry(QtCore.QRect(40, 40, 101, 31))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/plugins/milkmachine/Import.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.buttonImportGPS.setIcon(icon)
        self.buttonImportGPS.setObjectName(_fromUtf8("buttonImportGPS"))
        self.buttonDrawTrack = QtGui.QPushButton(MilkMachine)
        self.buttonDrawTrack.setGeometry(QtCore.QRect(40, 80, 101, 31))
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(_fromUtf8(":/plugins/milkmachine/pencil.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.buttonDrawTrack.setIcon(icon1)
        self.buttonDrawTrack.setObjectName(_fromUtf8("buttonDrawTrack"))
        self.buttonExportTrack = QtGui.QPushButton(MilkMachine)
        self.buttonExportTrack.setGeometry(QtCore.QRect(40, 270, 101, 31))
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(_fromUtf8(":/plugins/milkmachine/Export.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.buttonExportTrack.setIcon(icon2)
        self.buttonExportTrack.setObjectName(_fromUtf8("buttonExportTrack"))
        self.comboBox_export = QtGui.QComboBox(MilkMachine)
        self.comboBox_export.setGeometry(QtCore.QRect(160, 270, 271, 31))
        self.comboBox_export.setObjectName(_fromUtf8("comboBox_export"))
        self.buttonImport_audio = QtGui.QPushButton(MilkMachine)
        self.buttonImport_audio.setGeometry(QtCore.QRect(40, 120, 101, 31))
        self.buttonImport_audio.setIcon(icon)
        self.buttonImport_audio.setObjectName(_fromUtf8("buttonImport_audio"))
        self.lineEdit_InAudio1 = QtGui.QLineEdit(MilkMachine)
        self.lineEdit_InAudio1.setGeometry(QtCore.QRect(160, 119, 271, 31))
        self.lineEdit_InAudio1.setObjectName(_fromUtf8("lineEdit_InAudio1"))
        self.pushButton_clearAudio1 = QtGui.QPushButton(MilkMachine)
        self.pushButton_clearAudio1.setGeometry(QtCore.QRect(440, 120, 31, 31))
        self.pushButton_clearAudio1.setText(_fromUtf8(""))
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(_fromUtf8(":/plugins/milkmachine/delete.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pushButton_clearAudio1.setIcon(icon3)
        self.pushButton_clearAudio1.setObjectName(_fromUtf8("pushButton_clearAudio1"))
        self.pushButton_Audio1 = QtGui.QPushButton(MilkMachine)
        self.pushButton_Audio1.setGeometry(QtCore.QRect(480, 120, 31, 31))
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap(_fromUtf8(":/plugins/milkmachine/play.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pushButton_Audio1.setIcon(icon4)
        self.pushButton_Audio1.setObjectName(_fromUtf8("pushButton_Audio1"))
        self.lcdNumber_Audio1_C = QtGui.QLCDNumber(MilkMachine)
        self.lcdNumber_Audio1_C.setGeometry(QtCore.QRect(160, 170, 131, 31))
        self.lcdNumber_Audio1_C.setSmallDecimalPoint(False)
        self.lcdNumber_Audio1_C.setDigitCount(8)
        self.lcdNumber_Audio1_C.setObjectName(_fromUtf8("lcdNumber_Audio1_C"))
        self.lcdNumber_Audio1_P = QtGui.QLCDNumber(MilkMachine)
        self.lcdNumber_Audio1_P.setGeometry(QtCore.QRect(440, 170, 81, 31))
        self.lcdNumber_Audio1_P.setObjectName(_fromUtf8("lcdNumber_Audio1_P"))
        self.lcdNumber_Audio1_D = QtGui.QLCDNumber(MilkMachine)
        self.lcdNumber_Audio1_D.setGeometry(QtCore.QRect(300, 170, 131, 31))
        self.lcdNumber_Audio1_D.setDigitCount(8)
        self.lcdNumber_Audio1_D.setObjectName(_fromUtf8("lcdNumber_Audio1_D"))
        self.label = QtGui.QLabel(MilkMachine)
        self.label.setGeometry(QtCore.QRect(200, 153, 61, 16))
        self.label.setObjectName(_fromUtf8("label"))
        self.label_2 = QtGui.QLabel(MilkMachine)
        self.label_2.setGeometry(QtCore.QRect(460, 153, 61, 16))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.label_3 = QtGui.QLabel(MilkMachine)
        self.label_3.setGeometry(QtCore.QRect(340, 153, 51, 16))
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.pushButton_stop1 = QtGui.QPushButton(MilkMachine)
        self.pushButton_stop1.setGeometry(QtCore.QRect(520, 120, 31, 31))
        self.pushButton_stop1.setText(_fromUtf8(""))
        icon5 = QtGui.QIcon()
        icon5.addPixmap(QtGui.QPixmap(_fromUtf8(":/plugins/milkmachine/stop.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pushButton_stop1.setIcon(icon5)
        self.pushButton_stop1.setObjectName(_fromUtf8("pushButton_stop1"))

        self.retranslateUi(MilkMachine)
        QtCore.QObject.connect(self.buttonboxOkCancel, QtCore.SIGNAL(_fromUtf8("accepted()")), MilkMachine.accept)
        QtCore.QObject.connect(self.buttonboxOkCancel, QtCore.SIGNAL(_fromUtf8("rejected()")), MilkMachine.reject)
        QtCore.QMetaObject.connectSlotsByName(MilkMachine)

    def retranslateUi(self, MilkMachine):
        MilkMachine.setWindowTitle(_translate("MilkMachine", "MilkMachine", None))
        self.chkActivate.setText(_translate("MilkMachine", "Activate\n"
"(check)", None))
        self.lineEdit_ImportGPS.setToolTip(_translate("MilkMachine", "Raw GPS input file (from GPS unit)", None))
        self.buttonImportGPS.setToolTip(_translate("MilkMachine", "<html><head/><body><p>Browse to .gpx file. This will convert the .gpx to a .kml, then import the kml.</p></body></html>", None))
        self.buttonImportGPS.setText(_translate("MilkMachine", "Import GPS", None))
        self.buttonDrawTrack.setToolTip(_translate("MilkMachine", "Draw the imported GPS track on the map", None))
        self.buttonDrawTrack.setText(_translate("MilkMachine", "Draw Track", None))
        self.buttonExportTrack.setToolTip(_translate("MilkMachine", "Export the selected track to any supported format", None))
        self.buttonExportTrack.setText(_translate("MilkMachine", "Export Track", None))
        self.buttonImport_audio.setToolTip(_translate("MilkMachine", "<html><head/><body><p>Browse to .gpx file. This will convert the .gpx to a .kml, then import the kml.</p></body></html>", None))
        self.buttonImport_audio.setText(_translate("MilkMachine", "Import Audio 1", None))
        self.label.setText(_translate("MilkMachine", "Clock Time", None))
        self.label_2.setText(_translate("MilkMachine", "Position", None))
        self.label_3.setText(_translate("MilkMachine", "Duration", None))

import resources_rc
