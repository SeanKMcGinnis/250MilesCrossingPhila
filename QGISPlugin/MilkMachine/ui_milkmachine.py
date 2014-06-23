# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Users\Edward\.qgis2\python\plugins\MilkMachine\ui_milkmachine.ui'
#
# Created: Sun Jun 22 17:42:19 2014
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
        MilkMachine.resize(463, 331)
        self.buttonboxOkCancel = QtGui.QDialogButtonBox(MilkMachine)
        self.buttonboxOkCancel.setGeometry(QtCore.QRect(260, 290, 171, 32))
        self.buttonboxOkCancel.setOrientation(QtCore.Qt.Horizontal)
        self.buttonboxOkCancel.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonboxOkCancel.setObjectName(_fromUtf8("buttonboxOkCancel"))
        self.txtFeedback = QtGui.QTextEdit(MilkMachine)
        self.txtFeedback.setGeometry(QtCore.QRect(160, 230, 171, 31))
        self.txtFeedback.setObjectName(_fromUtf8("txtFeedback"))
        self.chkActivate = QtGui.QCheckBox(MilkMachine)
        self.chkActivate.setGeometry(QtCore.QRect(360, 230, 171, 31))
        self.chkActivate.setObjectName(_fromUtf8("chkActivate"))
        self.lineEdit_ImportGPS = QtGui.QLineEdit(MilkMachine)
        self.lineEdit_ImportGPS.setGeometry(QtCore.QRect(160, 40, 271, 31))
        self.lineEdit_ImportGPS.setAutoFillBackground(False)
        self.lineEdit_ImportGPS.setDragEnabled(True)
        self.lineEdit_ImportGPS.setObjectName(_fromUtf8("lineEdit_ImportGPS"))
        self.line = QtGui.QFrame(MilkMachine)
        self.line.setGeometry(QtCore.QRect(30, 160, 411, 16))
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
        self.buttonExportTrack.setGeometry(QtCore.QRect(40, 180, 101, 31))
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(_fromUtf8(":/plugins/milkmachine/Export.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.buttonExportTrack.setIcon(icon2)
        self.buttonExportTrack.setObjectName(_fromUtf8("buttonExportTrack"))
        self.comboBox_export = QtGui.QComboBox(MilkMachine)
        self.comboBox_export.setGeometry(QtCore.QRect(160, 180, 271, 31))
        self.comboBox_export.setObjectName(_fromUtf8("comboBox_export"))
        self.buttonImport_audio = QtGui.QPushButton(MilkMachine)
        self.buttonImport_audio.setGeometry(QtCore.QRect(40, 120, 101, 31))
        self.buttonImport_audio.setIcon(icon)
        self.buttonImport_audio.setObjectName(_fromUtf8("buttonImport_audio"))

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
        self.buttonImport_audio.setText(_translate("MilkMachine", "Import Audio", None))

import resources_rc
