# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'main.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 302)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.spinBox_maxflow = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBox_maxflow.setGeometry(QtCore.QRect(120, 180, 33, 20))
        self.spinBox_maxflow.setObjectName("spinBox_maxflow")
        self.spinBox_ndatapoints = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBox_ndatapoints.setGeometry(QtCore.QRect(200, 180, 33, 20))
        self.spinBox_ndatapoints.setObjectName("spinBox_ndatapoints")
        self.button_start = QtWidgets.QPushButton(self.centralwidget)
        self.button_start.setGeometry(QtCore.QRect(580, 130, 131, 23))
        self.button_start.setObjectName("button_start")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(30, 160, 61, 20))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(110, 160, 61, 20))
        self.label_2.setObjectName("label_2")
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(190, 160, 61, 20))
        self.label_3.setObjectName("label_3")
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setGeometry(QtCore.QRect(66, 43, 101, 20))
        self.label_4.setObjectName("label_4")
        self.label_5 = QtWidgets.QLabel(self.centralwidget)
        self.label_5.setGeometry(QtCore.QRect(180, 40, 121, 20))
        self.label_5.setObjectName("label_5")
        self.spinBox_MFC_com = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBox_MFC_com.setGeometry(QtCore.QRect(70, 70, 42, 22))
        self.spinBox_MFC_com.setObjectName("spinBox_MFC_com")
        self.spinBox_Sensor_com = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBox_Sensor_com.setGeometry(QtCore.QRect(200, 70, 42, 22))
        self.spinBox_Sensor_com.setObjectName("spinBox_Sensor_com")
        self.spinBox_minflow = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBox_minflow.setGeometry(QtCore.QRect(50, 180, 33, 20))
        self.spinBox_minflow.setObjectName("spinBox_minflow")
        self.label_6 = QtWidgets.QLabel(self.centralwidget)
        self.label_6.setGeometry(QtCore.QRect(20, 10, 101, 20))
        self.label_6.setObjectName("label_6")
        self.label_7 = QtWidgets.QLabel(self.centralwidget)
        self.label_7.setGeometry(QtCore.QRect(20, 130, 101, 20))
        self.label_7.setObjectName("label_7")
        self.label_8 = QtWidgets.QLabel(self.centralwidget)
        self.label_8.setGeometry(QtCore.QRect(390, 10, 101, 20))
        self.label_8.setObjectName("label_8")
        self.label_9 = QtWidgets.QLabel(self.centralwidget)
        self.label_9.setGeometry(QtCore.QRect(370, 40, 121, 20))
        self.label_9.setObjectName("label_9")
        self.lineEdit_datafolder = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_datafolder.setGeometry(QtCore.QRect(370, 70, 391, 20))
        self.lineEdit_datafolder.setObjectName("lineEdit_datafolder")
        self.pushButton_openfolder = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_openfolder.setGeometry(QtCore.QRect(440, 40, 75, 23))
        self.pushButton_openfolder.setObjectName("pushButton_openfolder")
        self.lineEdit_filename = QtWidgets.QLineEdit(self.centralwidget)
        self.lineEdit_filename.setGeometry(QtCore.QRect(370, 130, 111, 20))
        self.lineEdit_filename.setObjectName("lineEdit_filename")
        self.label_10 = QtWidgets.QLabel(self.centralwidget)
        self.label_10.setGeometry(QtCore.QRect(370, 100, 121, 20))
        self.label_10.setObjectName("label_10")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 21))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.button_start.setText(_translate("MainWindow", "Start Calibration"))
        self.label.setText(_translate("MainWindow", "Min Flow"))
        self.label_2.setText(_translate("MainWindow", "Max Flow"))
        self.label_3.setText(_translate("MainWindow", "# datapoints"))
        self.label_4.setText(_translate("MainWindow", "COM Port MFC"))
        self.label_5.setText(_translate("MainWindow", "COM Port Flow Sensor"))
        self.label_6.setText(_translate("MainWindow", "Hardware settings"))
        self.label_7.setText(_translate("MainWindow", "Calibration settings"))
        self.label_8.setText(_translate("MainWindow", "File settings"))
        self.label_9.setText(_translate("MainWindow", "Save folder"))
        self.pushButton_openfolder.setText(_translate("MainWindow", "Open folder"))
        self.label_10.setText(_translate("MainWindow", "File name (no extension)"))
