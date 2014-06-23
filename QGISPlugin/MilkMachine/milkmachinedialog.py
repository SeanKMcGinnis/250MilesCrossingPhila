# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MilkMachineDialog
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

from PyQt4 import QtCore, QtGui
from ui_milkmachine import Ui_MilkMachine
# create the dialog for zoom to point


class MilkMachineDialog(QtGui.QDialog):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.ui = Ui_MilkMachine()
        self.ui.setupUi(self)

    def setTextBrowser(self, output):
        self.ui.txtFeedback.setText(output)

    def clearTextBrowser(self):
        self.ui.txtFeedback.clear()