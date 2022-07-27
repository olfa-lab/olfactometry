# Script to calibrate flow meters
import sys

import serial
from serial.tools import list_ports
import time
import numpy as np
import csv
from flow_sensors_calibration import MFCAlicatDigArduino, FlowSensorCalibration 
import matplotlib
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import (
    QApplication, QDialog, QMainWindow, QMessageBox, QFileDialog
)
from PyQt5.uic import loadUi

from main_gui import Ui_MainWindow

class Window(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.connectSignalsSlots()
        self.setDefaultParams()
        self.connectDevices()
        


    def setDefaultParams(self):
        self.COM_settings_mfc = dict()
        self.COM_settings_mfc['baudrate'] = 115200
        self.COM_settings_mfc['com_port'] = 25
        self.MFC_settings = dict()
        self.MFC_settings['MFC_type'] = 'alicat_digital'
        self.MFC_settings['address'] = 'A'
        self.MFC_settings['arduino_port_num'] = 2
        self.MFC_settings['capacity'] = 1000
        self.MFC_settings['gas'] = "Air"
        self.MFC_settings["slave_index"] = 1 # this in full honestly is a teensy 
    

        self.COM_settings_flowmeter = dict()
        self.COM_settings_flowmeter['baudrate'] = 9600
        self.COM_settings_flowmeter['com_port'] = 7

        self.spinBox_Sensor_com.setValue(7)
        self.spinBox_MFC_com.setValue(25)
        self.spinBox_minflow.setValue(10)
        self.spinBox_maxflow.setValue(100)
        self.spinBox_ndatapoints.setValue(9)

        self.lineEdit_filename.setText('test')
        self.lineEdit_datafolder.setText('R:/rinberglabspace/Users/Bea/olfactometry/flow_sensor_calibration/calibration_files')
        
        self.filepath = 'R:/rinberglabspace/Users/Bea/olfactometry/flow_sensor_calibration/calibration_files/test.csv'
        self.folderpath = 'R:/rinberglabspace/Users/Bea/olfactometry/flow_sensor_calibration/calibration_files'

    def connectSignalsSlots(self):

        self.pushButton_openfolder.clicked.connect(self.selectFolder)
        self.lineEdit_filename.editingFinished.connect(self.fileSelected)
        self.button_start.clicked.connect(self.runCalibration)
        self.spinBox_MFC_com.valueChanged.connect(self.set_MFC_com)
        self.spinBox_Sensor_com.valueChanged.connect(self.set_flowsensor_com)
    
    def closeEvent(self, event):
        print("User has clicked the red x on the main window. Disconnecting serial")
        self.calibration.serial.close()
        self.mfc.serial.close()


    def connectDevices(self):
        # Initialize MFC
        self.mfc = MFCAlicatDigArduino( self.MFC_settings, self.COM_settings_mfc)

        # Initialize Flow Sensor communication
        self.calibration = FlowSensorCalibration(self.COM_settings_flowmeter)

    def selectFolder(self):
        self.folderpath = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        self.lineEdit_datafolder.setText(self.folderpath) 

    def fileSelected(self):
        self.filename = self.lineEdit_filename.text()
        self.filepath = self.folderpath + '/' + self.filename + '.csv'
    
    def set_MFC_com(self):
        value = self.spinBox_MFC_com.value()
        self.COM_settings_mfc['com_port'] = value
    
    def set_flowsensor_com(self):
        value = self.spinBox_Sensor_com.value()
        self.COM_settings_flowmeter['com_port'] = value


    def runCalibration(self):
        minflow = int(self.spinBox_minflow.value())
        maxflow = int(self.spinBox_maxflow.value())
        ndatapoints = int(self.spinBox_ndatapoints.value())
        flows = np.linspace(minflow, maxflow, ndatapoints)
        flow_sensor_reading = []
        csv_file = open(self.filepath, 'w')
        writer = csv.writer(csv_file)
        for iflow, flow in enumerate(flows):
            print('Setting flow ', flow)
            self.mfc.set_flowrate(flow*10)
            time.sleep(5)
            sensor_value = self.calibration.read_value()
            flow_sensor_reading.append(float(sensor_value))
            writer.writerow([flow, int(sensor_value), float(sensor_value)])
        csv_file.close()
        print('Calibration finished, File Closed')
        print('Saving Figure')
        plt.figure
        plt.plot(flows, flow_sensor_reading, '-o')
        plt.xlabel('Flow [scc/min]')
        plt.xlabel('Sensory reading [au]')
        plt.savefig(self.filepath[0:-4]+'.png')



if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())