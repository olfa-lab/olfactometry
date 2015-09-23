__author__ = 'chris'
import sip  # these lines are necessary because of a Traits dependancy on use of V2 of these APIs.
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
from PyQt4 import QtGui
from main import *
import cleaning
from utils import *
import sys


qapp = QtGui.QApplication.instance()
if qapp is None:
    qapp = QtGui.QApplication(sys.argv)
