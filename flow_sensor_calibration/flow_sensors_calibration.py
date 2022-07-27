# Script to calibrate flow meters
import serial
from serial.tools import list_portsk
import time
import numpy as np
import csv
from main_gui import Ui_MainWindow

class FlowSensorCalibration():
    def __init__(self, com_settings):

        self.sensor = []
       
        self.serial = self.connect_serial(com_settings['com_port'], baudrate=com_settings['baudrate'], timeout=1)
       
    def connect_serial(self, port, baudrate, timeout=1, writeTimeout=1):
        """
        Return Serial object after making sure that the port is accessible and that the port is expressed as a string.

        :param port: str or int (ie "COM4" or 4 for Windows).
        :param baudrate: baudrate.
        :param timeout: read timeout in seconds, default 1 sec.
        :param writeTimeout: write timeout in seconds, default 1 sec.
        :return: serial port object.
        :rtype: serial.Serial
        """
        print(baudrate)
        if isinstance(port, int):
            port = "COM{0}".format(port)
        names_list = list()
        for i in list_ports.comports():
            names_list.append(i[0])
        if port not in names_list:
            print(("Serial not found on {0}.".format(port)))
            print('Listing current serial ports with devices:')
            for ser in list_ports.comports():
                ser_str = '\t{0}: {1}'.format(ser[0], ser[1])
                print(ser_str)
            time.sleep(.01)  # just to let the above lines print before the exemption is raised. cleans console output.
            raise serial.SerialException('Requested COM port: {0} is not listed as connected.'.format(port))
        else:
            
            print(baudrate, timeout, writeTimeout)
            return serial.Serial(port, baudrate=baudrate, timeout=timeout, writeTimeout=writeTimeout)
    def read_value(self):
        ts = time.time()
        ts_2 = 0
        serial_values =[]
        while ts_2 < ts +1:
            ts_2 = time.time()
            this_read = self.serial.readline()
            serial_values.append(this_read)
            #print('conversion ')
            #print(this_read, float(this_read))
        serial_converted = [float(i) for i in serial_values]
        #print(serial_converted)
        return(np.mean(serial_converted))

class MFCAlicatDigArduino():
    
    def __init__(self, mfc_config, com_settings, flow_units='SCCM', setflow=-1):
        self.slaveindex = mfc_config['slave_index']
        self.mfc_type = mfc_config['MFC_type']
        self.capacity = int(mfc_config['capacity'])
        self.units = flow_units
        self.gas = mfc_config['gas']
        if self.mfc_type.startswith('alicat_digital'):
            self.address = mfc_config['address']
        if 'arduino_port_num' in list(mfc_config.keys()):  # this is only needed for Teensy olfactometers. This is the device ID
            self.arduino_port = int(mfc_config['arduino_port_num'])

        self.serial = self.connect_serial(com_settings['com_port'], baudrate=com_settings['baudrate'], timeout=1, writeTimeout=1)
        
    def connect_serial(self, port, baudrate, timeout=1, writeTimeout=1):
        """
        Return Serial object after making sure that the port is accessible and that the port is expressed as a string.

        :param port: str or int (ie "COM4" or 4 for Windows).
        :param baudrate: baudrate.
        :param timeout: read timeout in seconds, default 1 sec.
        :param writeTimeout: write timeout in seconds, default 1 sec.
        :return: serial port object.
        :rtype: serial.Serial
        """
        print(baudrate)
        if isinstance(port, int):
            port = "COM{0}".format(port)
        names_list = list()
        for i in list_ports.comports():
            names_list.append(i[0])
        if port not in names_list:
            print(("Serial not found on {0}.".format(port)))
            print('Listing current serial ports with devices:')
            for ser in list_ports.comports():
                ser_str = '\t{0}: {1}'.format(ser[0], ser[1])
                print(ser_str)
            time.sleep(.01)  # just to let the above lines print before the exemption is raised. cleans console output.
            raise serial.SerialException('Requested COM port: {0} is not listed as connected.'.format(port))
        else:
            
            print(baudrate, timeout, writeTimeout)
            return serial.Serial(port, baudrate=baudrate, timeout=timeout, writeTimeout=writeTimeout)

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
        command = "DMFC {0:d} {1:d} A{2:d}".format(self.slaveindex, self.arduino_port, flownum)
        #print(command)
        confirmation = self.send_command(command)
        #print(confirmation)
        if(confirmation != 'MFC set\r\n'):
            print("Error setting MFC: ", confirmation)
        else:
            # Attempt to read back
            success = True
            command = "DMFC {0:d} {1:d}".format(self.slaveindex, self.arduino_port)
            returnstring = self.send_command(command)
            while (returnstring is None or returnstring.startswith('Error -2')) and time.time() - start_time < .2:
                returnstring = self.send_command(command)
        return success

    def get_flowrate(self):
        """

        :param args:
        :param kwargs:
        :return: float flowrate normalized to max flowrate.
        """
        start_time = time.time()

        command = "DMFC {0:d} {1:d} A".format(self.slaveindex, self.arduino_port)
        command_get = "DMFC {0:d} {1:d}".format(self.slaveindex, self.arduino_port)

        # first, flush the buffer on the Teensy:
        _ = self.send_command(command_get)
        # stick around querying the olfactometer until it gets the command.
        confirmation = self.send_command(command)
        while (confirmation is None or not confirmation.startswith(b"MFC set")) and time.time() - start_time < .2:
            confirmation = self.send_command(command)
        # stick around querying the olfactometer until it gets the flow data from the alicat.
        returnstring = self.send_command(command_get)
        while (returnstring is None or returnstring.startswith(b"Error -2")) and time.time() - start_time < .2:
            returnstring = self.send_command(command_get)
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
    
    def send_command(self, command, tries=1):
        self.serial.flushInput()
        for i in range(tries):
            # logging.debug("Sending command: {0}".format(command))
            self.serial.write(bytes("{0}\r".format(command), 'utf8'))
            line = self.read_line()
            line = self.read_line()
            morebytes = self.serial.inWaiting()
            if morebytes:
                extrabytes = self.serial.read(morebytes)
            if line:
                return line

    
    def read_line(self):
        line = None
        try:
            line = self.serial.readline()
            # logging.debug("Recieved line: {0}".format(repr(line)))
        except SerialException as e:
            print('pySerial exception: Exception that is raised on write timeouts')
        return line



# # Important default  parameters for MFC
# COM_settings_mfc = dict()
# COM_settings_mfc['baudrate'] = 115200
# COM_settings_mfc['com_port'] = 25
# MFC_settings = dict()
# MFC_settings['MFC_type'] = 'alicat_digital'
# MFC_settings['address'] = 'A'
# MFC_settings['arduino_port_num'] = 2
# MFC_settings['capacity'] = 1000
# MFC_settings['gas'] = "Air"
# MFC_settings["slave_index"] = 1 # this in full honestly is a teensy 


# COM_settings_flowmeter = dict()
# COM_settings_flowmeter['baudrate'] = 9600
# COM_settings_flowmeter['com_port'] = 7
# # TO DO, extract functions from MFC class, so that the parent device is not needed anymore

# # Initialize MFC
# mfc = MFCAlicatDigArduino( MFC_settings, COM_settings_mfc)

# # Initialize Flow Sensor communication
# calibration = FlowSensorCalibration(COM_settings_flowmeter)
# flow_sensor_reading = []
# flows = np.linspace(10, 100, 91)

# csv_file = open('R:\\rinberglabspace\\Users\\Bea\\olfactometry\\flow_sensor_calibration\\calibration_files\\prova.csv', 'w')
# writer = csv.writer(csv_file)
# for iflow, flow in enumerate(flows):
#     print('Setting flow ', flow)
#     mfc.set_flowrate(flow*10)
#     time.sleep(3)
#     sensor_value = calibration.read_value()
#     print(sensor_value, float(sensor_value))
#     flow_sensor_reading.append(float(sensor_value))
#     writer.writerow([flow, float(sensor_value)])

#     print(calibration.read_value())


# csv_file.close()
