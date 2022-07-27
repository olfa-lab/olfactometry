from PyQt5 import QtCore, QtWidgets
import time
import logging


class DirectSerialInterface(QtWidgets.QWidget):  # todo: implement direct serial interface for troubleshooting MFC behavior.
    def __init__(self):
        pass


class MFC(QtWidgets.QGroupBox):

    def __init__(self, parent_device, mfc_config, flow_units='SCCM', setflow=-1):
        """

        :param parent_device: Parent Olfactometer, Dilutor, or DirectSerialInterface.
        :param MFC_type: ie 'Alicat_digital'
        :param capacity: Unit flow capacity in SCCM.
        :param gas: Name of gas.
        :param address: This is only necessary for digital communication with multiple Alicats so far (ie dilutor).
        :param mfcindex: the index for addressing within a teensy olfactometer.
        :return:
        """
        super(MFC, self).__init__()

        self.parent_device = parent_device
        self.mfc_type = mfc_config['MFC_type']
        self.capacity = int(mfc_config['capacity'])
        self.units = flow_units
        self.gas = mfc_config['gas']
        if self.mfc_type.startswith('alicat_digital'):
            self.address = mfc_config['address']
        if 'arduino_port_num' in list(mfc_config.keys()):  # this is only needed for Teensy olfactometers. This is the device ID
            self.arduino_port = int(mfc_config['arduino_port_num'])

        mfclayout = QtWidgets.QGridLayout()
        self.mfcslider = QtWidgets.QSlider(QtCore.Qt.Vertical)
        self.mfcslider.setMaximum(int(self.capacity))
        self.mfcslider.setStatusTip('Adjusts flow set rate.')
        self.mfcslider.setTickPosition(3)
        self.mfctextbox = QtWidgets.QLineEdit()
        self.mfctextbox.setMaxLength(4)
        self.mfctextbox.setAlignment(QtCore.Qt.AlignCenter)
        self.mfctextbox.setPlaceholderText("Set value")
        self.mfctextbox.setStatusTip('Type to set flow rate.')
        self.lcd = QtWidgets.QLCDNumber()
        self.lcd.setMinimumSize(50, 50)
        self.lcd.setDigitCount(5)  # this allows 4 digits and a decimal.
        self.lcd.setStatusTip('Current flow reading.')
        self.lcd.setMaximumHeight(50)
        mfclayout.addWidget(self.mfcslider, 0, 0, 2, 1)
        mfclayout.addWidget(self.mfctextbox, 0, 1, 1, 2)
        mfclayout.addWidget(self.lcd, 1, 1, 1, 2)
        self.setLayout(mfclayout)
        ui_name = "{0} {1:0.1f}{2}".format(self.gas, self.capacity, self.units)
        self.setTitle(ui_name)
        self.setMaximumWidth(120)

        self.mfcslider.valueChanged.connect(self._updatetext)
        self.mfcslider.sliderReleased.connect(self._slider_changed)
        self.mfcslider.sliderPressed.connect(self.parent_device.stop_mfc_polling)
        self.mfctextbox.editingFinished.connect(self._textchanged)

        self.last_poll_time = 0.
        self.flow = 0.

        if setflow < 0 or setflow > self.capacity:
            flow = self.get_flowrate()
            if flow is not None:
                self.mfcslider.setValue(flow * self.capacity)
                self.last_poll_time = time.time()
        else:
            self.set_flowrate(setflow)
            self.last_poll_time = 0.

    def poll(self):
        flow = self.get_flowrate()
        if flow is not None:
            self.flow = flow
            self.lcd.display(flow*self.capacity)
            self.last_poll_time = time.time()
            return True
        else:
            if hasattr(self.parent_device, 'polling_interval'):
                if time.time() - self.last_poll_time > self.parent_device.polling_interval * 2:
                    horror = True
                else:
                    horror = False
            else:
                horror = True
            return not horror  # this will return false if there is a reportable error and true otherwise.

    @QtCore.pyqtSlot(int)
    def _updatetext(self, i):
        self.mfctextbox.setText(str(i))
        return

    @QtCore.pyqtSlot()
    def _slider_changed(self):
        val = self.mfcslider.value()
        if abs(val - self.flow) >= 0:
            self.set_flowrate(val)
        self.parent_device.restart_mfc_polling()
        return

    @QtCore.pyqtSlot()
    def _slider_pressed(self):
        self.parent_device.stop_mfc_polling()
        return

    @QtCore.pyqtSlot()
    def _textchanged(self):
        """ Text of the line edit has changed. Sets the new MFC value """
        try:
            value = float(self.mfctextbox.text())
            self.set_flowrate(value)
            self.mfcslider.setValue(value)
        except ValueError:
            pass
        return

    def set_flowrate(self, flowrate):
        pass

    def get_flowrate(self):
        pass


class MFCAnalog(MFC):
    def get_flowrate(self, *args, **kwargs):
        """ get MFC flow rate measure as a percentage of total capacity (0.0 to 100.0)"""

        command = "MFC " + str(self.parent_device.slaveindex) + " " + str(self.arduino_port)
        rate = self.parent_device.send_command(command)
        if (rate < b'\x00'):
            print("Couldn't get MFC flow rate measure")
            print("mfc index: " + str(self.arduino_port), "error code: ", rate)
            return None
        else:
            return float(rate)

    def set_flowrate(self, flowrate, *args, **kwargs):
        """ sets the value of the MFC flow rate setting as a % from 0.0 to 100.0
            argument is the absolute flow rate """

        if flowrate > self.capacity or flowrate < 0:
            return  # warn about setting the wrong value here
        # if the rate is already what it should be don't do anything
        if abs(flowrate - self.flow) < 0.0005:
            return  # floating points have inherent imprecision when using comparisons
        command = "MFC " + str(self.parent_device.slaveindex) + " " + str(self.arduino_port) + " " + str(flowrate * 1.0 / self.capacity)
        set = self.parent_device.send_command(command)
        if(set != "MFC set\r\n"):
            print("Error setting MFC: ", set)
            return False
        return True

class MFCAlicatDigArduino(MFC):
    def set_flowrate(self, flowrate):
        """

        :param flowrate: flowrate in units of self.capacity (usually ml/min)
        :param args:
        :param kwargs:
        :return:
        """
        success = False
        start_time = time.time()
        # print "Setting rate of: ", flowrate
        if flowrate > self.capacity or flowrate < 0:
            return success
        flownum = (flowrate * 1. / self.capacity) * 64000.
        flownum = int(flownum)
        command = "DMFC {0:d} {1:d} A{2:d}".format(self.parent_device.slaveindex, self.arduino_port, flownum)
        confirmation = self.parent_device.send_command(command)
        if(confirmation != "MFC set\r\n"):
            print("Error setting MFC: ", confirmation)
        else:
            # Attempt to read back
            success = True
            command = "DMFC {0:d} {1:d}".format(self.parent_device.slaveindex, self.arduino_port)
            returnstring = self.parent_device.send_command(command)
            while (returnstring is None or returnstring.startswith('Error -2')) and time.time() - start_time < .2:
                returnstring = self.parent_device.send_command(command)
        return success

    def get_flowrate(self):
        """

        :param args:
        :param kwargs:
        :return: float flowrate normalized to max flowrate.
        """
        start_time = time.time()
        if self.parent_device is None:
            return

        command = "DMFC {0:d} {1:d} A".format(self.parent_device.slaveindex, self.arduino_port)
        command_get = "DMFC {0:d} {1:d}".format(self.parent_device.slaveindex, self.arduino_port)

        # first, flush the buffer on the Teensy:
        _ = self.parent_device.send_command(command_get)
        # stick around querying the olfactometer until it gets the command.
        confirmation = self.parent_device.send_command(command)
        while (confirmation is None or not confirmation.startswith(b"MFC set")) and time.time() - start_time < .2:
            confirmation = self.parent_device.send_command(command)
        # stick around querying the olfactometer until it gets the flow data from the alicat.
        returnstring = self.parent_device.send_command(command_get)
        while (returnstring is None or returnstring.startswith(b"Error -2")) and time.time() - start_time < .2:
            returnstring = self.parent_device.send_command(command_get)
        # once it returns a good string, parse the string and return the flow.
        li = returnstring.split(b' ')
        if len(li) > 4:
            r_str = li[4]  # 5th column is mass flow, so index 4.
            try:
                flow = float(r_str)
                if self.capacity > 1000:
                    flow *= 1000.
                flow = flow / self.capacity  # normalize as per analog api.
                self.lcd.setStyleSheet("background-color: None")
            except ValueError:
                self.lcd.setStyleSheet("background-color: Grey")
                flow = None
            if (flow < 0):
                self.lcd.setStyleSheet("background-color: Red")
                logging.error('MFC reporting negative flow.')
                logging.error(returnstring)
        else:
            self.lcd.setStyleSheet("background-color: Grey")
            flow = None
            # Failure

        return flow


class MFCAlicatDigRaw(MFC):
    def __init__(self, parent_device, *args, **kwargs):
        parent_device._eol = '\r'  # Alicats use this EOL, so we have to catch it.
        super(MFCAlicatDigRaw, self).__init__(parent_device, *args, **kwargs)

    def set_flowrate(self, flowrate):
        if flowrate > self.capacity or flowrate < 0.:
            raise ValueError('Flow rate supplied ({0}) is above capacity ({1}) or below 0.'.format(flowrate, self.capacity))
        flownum = (flowrate * 1. / self.capacity) * 64000.
        flownum = int(flownum)
        command = "{0}{1}\r".format(self.address, flownum)
        confirmation = self.parent_device.send_command(command)
        return True

    def get_flowrate(self):
        start_time = time.time()
        command = "{0}\r".format(self.address)
        returnstring = self.parent_device.send_command(command)
        # if no returnstring, wait for < 200 ms to get a returnstring.
        while not returnstring and time.time() - start_time < .2:
            returnstring = self.parent_device.read_line()
        li = returnstring.split(b' ')
        if len(li) > 4:
            r_str = li[4]  # 5th column is mass flow, so index 4.
            flow = float(r_str)
            if self.capacity > 1000:
                flow *= 1000.
            flow = flow / self.capacity  # normalize as per analog api.
            if (flow < 0):
                print("Couldn't get MFC flow rate measure")
                print("mfc index: " + str(self.address), "error code: ", flow)
                return None
        else:
            flow = None
            # Failure
        return flow

        pass


MFCclasses = {'analog': MFCAnalog,
              'alicat_digital': MFCAlicatDigArduino,
              'alicat_digital_raw': MFCAlicatDigRaw}

