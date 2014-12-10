#250MilesCrossingPhila

Code and components developed to support the 250 Miles Crossing Philadelphia project

http://www.250miles.net/

##Milk Machine QGIS Python Plugin

The plugin can be found in the QGISPlugin folder. It is being developed in Python 2.7.5 64 bit, which is the native Python distribution for Quantum GIS (QGIS). The plugin was developed under QGIS 2.4, and has had minimal testing on QGIS 2.6. The plugin is compatible with Windows, Mac OSX, and Linux.

###QGIS

####Windows
To get QGIS For Windows, go to http://www.qgis.org/en/site/forusers/download.html and download the OSGeo4W Network Installer (64-bit), since it has the most comprehensive package list. Make sure to install the Python package `SciPy`.

####Linux
For Linux, get the latest stable build. 

`sudo apt-get install python-software-properties
sudo add-apt-repository ppa:ubuntugis/ubuntugis-unstable
sudo apt-get update
sudo apt-get install qgis python-qgis qgis-plugin-grass`

####Mac
http://www.kyngchaos.com/

###Install the Milk Machine Plugin

Copy the "MilkMachine" folder in the QGISPlugin folder to your ~\.qgis2\python\plugins\MilkMachine folder. This can be found in the
user directory under windows. In QGIS go to Plugins > Manage and Install Plugins... > Installed. Select the MilkMachine Plugin for
it to appear in the QGIS toolbar.

###Dependencies

###Credits/Funding Sources

University City Science Center
Wexford Science + Technology
Philadelphia Redevelopment Authority
Drexel University


