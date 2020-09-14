import os

QMLDIR = os.path.join(os.path.dirname(__file__), "qml")

from pioneer.das.view.apps import dasview
from PyQt5.QtQml import qmlRegisterType
from . import QtWrappers

qmlRegisterType(QtWrappers.Platform, "Das", 1, 0, "Platform")
qmlRegisterType(QtWrappers.Synchronized, "Das", 1, 0, "Synchronized")
qmlRegisterType(QtWrappers.Selector, "Das", 1, 0, "Selector")
qmlRegisterType(QtWrappers.ExtractImage, "Das", 1, 0, "ExtractImage")

qmlRegisterType(QtWrappers.DasSampleToCloud, "Das", 1, 0, "DasSampleToCloud")

qmlRegisterType(QtWrappers.ROSCalibratorFilter, "Das", 1, 0, "ROSCalibratorFilter")
qmlRegisterType(QtWrappers.Undistort, "Das", 1, 0, "Undistort")