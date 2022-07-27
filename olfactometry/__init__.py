from PyQt5 import sip  # these lines are necessary because of a Traits dependancy on use of V2 of these APIs.
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
from PyQt5 import QtWidgets
from .main import *
# from .cleaning import *
from .utils import *
import sys


qApp = QtWidgets.QApplication.instance()
if qApp is None:
    qApp = QtWidgets.QApplication(sys.argv)
