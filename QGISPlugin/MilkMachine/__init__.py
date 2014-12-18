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
 This script initializes the plugin, making it known to QGIS.
"""

def classFactory(iface):
    # load MilkMachine class from file MilkMachine
    from milkmachine import MilkMachine
    return MilkMachine(iface)
