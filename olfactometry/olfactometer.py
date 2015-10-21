__author__ = 'labadmin'

from PyQt4 import QtCore, QtGui
import time
from mfc import MFCclasses, MFC
from dilutor import DILUTORS
from serial import SerialException
from utils import OlfaException, flatten_dictionary, connect_serial

import logging


class Olfactometer(QtGui.QGroupBox):
    vialChanged = QtCore.pyqtSignal(int)  # this signal should be used when a vial is set.
    # It is connected to valvegroup button setting.

    def __init__(self, *args, **kwargs):
        super(Olfactometer, self).__init__(*args, **kwargs)
        self.check_flows_before_opening = True  # this will check

    def set_stimulus(self, stimulus_dict):
        pass

    def set_odor(self, odor, conc=None, valvestate=None):
        pass

    def set_flows(self, flows):
        pass

    def check_flows(self):
        pass

    def send_command(self, command, tries=1):
        pass

    def stop_mfc_polling(self):
        raise OlfaException('stop_mfc_polling must be defined by olfactometer class')

    def restart_mfc_polling(self):
        pass

    def read_line(self):
        pass

    def all_off(self):
        """
        Mandatory function to turn off all valves.
        :return:
        """
        pass

    def set_vial(self, val):
        """
        Mandatory function to open a valve. This is called by vialgroup when buttons are pressed.
        :return:
        """
        pass

    def close_serial(self):
        """
        Mandatory function to close physical devices so that the olfactometer can be deleted. Called during a restart.
        :return:
        """

    def generate_tables_definition(self):
        pass

    def generate_stimulus_template_string(self):
        pass

    @QtCore.pyqtSlot(bool)
    def check_flows_changed(self, checked):
        self.check_flows_before_opening = checked
        return


class TeensyOlfa(Olfactometer):

    def __init__(self, parent, config_dict, mfc_polling_interval=2.):
        """

        :param parent: parent Olfactometers window.
        :param config_dict: _Single_ olfactometer configuration dictionary (see readme for specs on configuration file)
        :return:
        """
        super(TeensyOlfa, self).__init__()
        self.config = config_dict
        self.slaveindex = config_dict['slave_index']
        self.polling_interval = mfc_polling_interval

        self.dummyvial = self._config_dummy(config_dict["Vials"])
        self.checked_id = self.dummyvial
        self._valve_time_lockout = False

        # CONFIGURE SERIAL
        baudrate = 115200

        com_port = config_dict['com_port']
        logging.info('Starting Teensy Olfactometer on {0}'.format(com_port))
        self.serial = connect_serial(com_port, baudrate=baudrate, timeout=1, writeTimeout=1)

        # CONFIGURE DEVICES
        self.dilutors = self._config_dilutors(config_dict.get('Dilutors', {}))
        self.mfcs = self._config_mfcs(config_dict['MFCs'])
        self.vials = VialGroup(self, config_dict['Vials'])
        self._poll_mfcs()
        self._mfc_timer = self._start_mfc_polling(mfc_polling_interval)

        layout = QtGui.QHBoxLayout(self)
        for mfc in self.mfcs:
            layout.addWidget(mfc)
        layout.addWidget(self.vials)
        for dil in self.dilutors:
            layout.addWidget(dil)
        self.setLayout(layout)
        self.setStatusTip("Teensy olfactometer on {0}.".format(com_port))

        self.all_off()

    def set_stimulus(self, stimulus_dict):
        """
        Sets stimulus based on stimulus dictionary defined in self.generate_stimulus_template()

        :param stimulus_dict: dictionary conforming to stimulus template.
        :type stimulus_dict: dict
        :return: True if stimulus set successfully.
        :rtype: bool
        """
        successes = []
        dilspecs = stimulus_dict['dilutors']
        odor = stimulus_dict['odor']
        try:
            vialconc = stimulus_dict['vialconc']
        except KeyError:
            vialconc = None
        for i in xrange(len(dilspecs)):
            dilutor = self.dilutors[i]
            k = 'dilutor_{0}'.format(i)
            success = dilutor.set_stimulus(dilspecs[k])
            successes.append(success)
        flows = []
        for i in xrange(2):
            k = 'mfc_{0}_flow'.format(i)
            flows.append(stimulus_dict[k])
        successes.append(self.set_flows(flows))
        successes.append(self.set_odor(odor, vialconc))
        return all(successes)

    def set_odor(self, odor, conc=None, valvestate=None):
        """
        Finds the exact matches for a vial with the specified odor / concentration.  Concentration is optional if only
        one vial with the odor is present in the configuration.

        ** Raises exemption if no matches are found or if multiple matches are found. **

        :param odor: String to specify odor.  None, False, or '' will open no vial and return True.
        :param conc: Float concentration, optional.
        :param valvestate: Optionally explicitly state whether to open or close valve. Pass True to open, False to close.
        :return: True if setting appears to be successful.
        :rtype: bool
        """
        if isinstance(odor, str):
            vnum = self.vials.find_odor(odor, conc)
            return self.set_vial(vnum, valvestate)
        elif isinstance(odor, int):  # a valve was specified.
            return self.set_vial(odor, valvestate)
        else:  # no odor specified. Return true because you were asked to do nothing and complied.
            return True

    def set_vial(self, vial_num, valvestate=None, override_checks=False):
        """
        Sets a vial by number. This vial corresponds to the vial number in the teensy. It opens/closes a pair of valves
        using the "vialOn"/"vialOff" commands. Teensy handles actuating the pair of valves for the vial.

        :param vial_num: Vial number to actuate. None, False, or 0 will open no vial and return True.
        :param valvestate: Optionally explicitly state whether to open or close valve. Pass True to open, False to close.
        :param override_checks: Optionally override flow checks and lockout timing. Used for cleaning.
        :return: True if setting appears to be successful.
        :rtype: bool
        """
        if vial_num:
            set_completed = False  # this is returned. Set to true if things go ok.

            if valvestate is None:
                if vial_num == self.checked_id:
                    valvestate = 0
                else:
                    valvestate = 1

            if vial_num == self.dummyvial:
                return self.set_dummy_vial(valvestate)

            if valvestate:  # we're opening a vial, so we have to check some conditions first.
                if not self.check_flows() and not override_checks:
                    logging.warning("MFCs reporting no flow. Cannot open valve.")
                elif not self.checked_id == self.dummyvial and not override_checks:
                    logging.warning('Operation not permitted: another valve is open and must be closed before opening another.')
                elif vial_num == self.checked_id:
                    logging.warning('Valve is already open.')
                elif self._valve_time_lockout and not override_checks:
                    logging.warning('Cannot open vial. Must wait 1 second after last valve closed to prevent cross=contamination.')
                else:
                    set_completed = self._set_valveset(vial_num, valvestate)
                    if set_completed:
                            self._valve_time_lockout = True
                            self.checked_id = vial_num
                            self.vialChanged.emit(self.checked_id)

            elif not valvestate:
                if not vial_num == self.checked_id:
                    logging.warning('Cannot close valve, it is not open.')
                else:
                    set_completed = self._set_valveset(vial_num, valvestate)
                    if set_completed:
                        logging.debug('set completed')
                        QtCore.QTimer.singleShot(1000, self._valve_lockout_clear)
                        self.checked_id = self.dummyvial
                        self.vialChanged.emit(self.checked_id)
        else:  # no vial specified. Return true because you were asked to do nothing and complied.
            set_completed = True
        return set_completed

    def set_flows(self, flows):
        """
        Sets flow rate for MFCs based on provided tuple. Specified flowrates should be in the units of the MFC.

        i.e. (900, 100) will set the first MFC to 900 SCCM and the second to 100 SCCM.

        :param flows:
        :return: return bool if all sets are complete.
        """

        if not len(flows) == len(self.mfcs):
            ex_str = 'Number of flows specified ({0}) not equal to number of MFCs in olfa ({1}).'.format(len(flows),
                                                                                                         len(self.mfcs))
            raise OlfaException(ex_str)
        else:
            successes = []
            for mfc, flow in zip(self.mfcs, flows):
                success = mfc.set_flowrate(flow)
                successes.append(success)
            return all(successes)

    def check_flows(self):
        """
        Checks all MFCs in olfa to see if they are reporting flow. This prevents opening a vial in a no-flow condition.

        :return: True if all MFCs polling correctly and are reporting flow.
        :rtype: bool
        """

        flows_on = True
        if self.check_flows_before_opening:
            for i, mfc in enumerate(self.mfcs):
                time_elapsed = time.time() - mfc.last_poll_time
                if time_elapsed > 2.1 * self.polling_interval:
                    raise OlfaException('MFC polling is not ok.')
                elif mfc.flow <= 0.:
                    logging.warning('MFC {0} reporting no flow.'.format(i))
                    flows_on = False
        else:
            pass
        return flows_on

    def set_dilution(self, dilution_factor=None, flows=None):
        """
        Sets dilutors attached to the olfactometer.

        :param dilution_factor: list of dilution factors, one for each dilutor on the olfactometer.
        :param flows:  list of lists, one list per dilutor. Each list contains flowrates for each MFC in the dilutor (vac, air).
        :return: True if setting appears to be successful.
        :rtype: bool
        """
        successes = list()
        if dilution_factor is not None:
            pass
        elif flows is not None:
            for f, d in zip(flows, self.dilutors):
                successes.append(d.set_flows(f))
        return all(successes)

    def _config_mfcs(self, mfc_config):
        mfcs = []
        for v in mfc_config:
            mfc_type = v['MFC_type']
            mfc = MFCclasses[mfc_type](self, v)
            mfcs.append(mfc)
        return mfcs

    def _config_dilutors(self, dilutor_config):
        dilutors = []
        for v in dilutor_config:
            dilutor_type = v['dilutor_type']
            logging.debug('Configuring {0} dilutor.'.format(dilutor_type))
            dil = DILUTORS[dilutor_type](self, v)
            dilutors.append(dil)
        return dilutors

    def send_command(self, command, tries=1):
        self.serial.flushInput()
        for i in xrange(tries):
            # logging.debug("Sending command: {0}".format(command))
            self.serial.write("{0}\r".format(command))
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

    def _start_mfc_polling(self, polling_interval_sec=1.):
        logging.debug('Starting MFC polling.')
        mfc_timer = QtCore.QTimer()
        mfc_timer.timeout.connect(self._poll_mfcs)
        polling_interval_ms = int(polling_interval_sec * 1000)
        mfc_timer.start(polling_interval_ms)
        return mfc_timer

    def close_serial(self):
        """
        Closes serial communication to olfactometer. Used before deleting object or reinitializing.
        :return: None
        """
        self.serial.close()
        for dil in self.dilutors:
            dil.close_serial()

    @QtCore.pyqtSlot()
    def _poll_mfcs(self):
        for i in xrange(len(self.mfcs)):
            mfc = self.mfcs[i]
            assert isinstance(mfc, MFC)
            success = mfc.poll()
            if mfc.flow < 0. and self.check_flows_before_opening:
                self.all_off()
                raise OlfaException('MFC is reporting no flow. Cannot continue.')
            if not success:
                logging.error("Olfactometer cannot poll MFC {0}".format(i))
        return

    @QtCore.pyqtSlot()
    def stop_mfc_polling(self):
        """
        Stops MFC polling.
        :return:
        """
        self._mfc_timer.stop()
        return

    @QtCore.pyqtSlot()
    def restart_mfc_polling(self):
        """
        Restarts MFC pooling after stop.
        :return:
        """
        if not self._mfc_timer.isActive():
            self._mfc_timer.start(int(self.polling_interval*1000))  # from seconds to msec
        return

    def _set_valveset(self, valvenum, valvestate=1, suppress_errors=False):
        if valvestate:
            command = "vialOn {0} {1}".format(self.slaveindex, valvenum)
        else:
            command = "vialOff {0} {1}".format(self.slaveindex, valvenum)
        line = self.send_command(command)
        if not line.split()[0] == 'Error':
            return True
        elif not suppress_errors:
            logging.error('Cannot set valveset for vial {0}'.format(valvenum))
            logging.error(repr(line))
            return False

    def set_dummy_vial(self, valvestate=1):
        """
        Sets the dummy vial.

        Valvestate means the state of the valve. This is inversed from a normal valve!!

        * A valvestate of 0 means to *close* the dummy by powering the solenoid.
        * A valvestate of 1 means to *open* the dummy by closing other open valves (if any) and depower the dummy valves.

        Usually, you want to pass valvestate with a 1 to close open valves and set the dummy open.

        :param valvestate: Desired state of the dummy (0 closed, 1 open). Default is 1.
        :return: True if successful setting.
        :rtype : bool
        """
        success = False
        if self.checked_id == self.dummyvial and not valvestate:  # dummy is "off" (this means open as it is normally open),
            command = "vial {0} {1} on".format(self.slaveindex, self.dummyvial)
            logging.debug(command)
            line = self.send_command(command)
            logging.debug(line)
            if not line.split()[0] == "Error":
                logging.info('Dummy ON.')
                self.vialChanged.emit(self.dummyvial)
                self.checked_id = 0
            else:
                logging.error('Cannot set dummy vial.')
                logging.error(line)
        elif self.checked_id == self.dummyvial and valvestate:  # valve is already open, do nothing and return success!
            success = True
        elif self.checked_id == 0 and valvestate:  # dummy is already (closed)
            command = "vial {0} {1} off".format(self.slaveindex, self.dummyvial)
            logging.debug(command)
            line = self.send_command(command)
            logging.debug(line)
            if not line.split()[0] == "Error":
                logging.info("Dummy OFF.")
                self.vialChanged.emit(self.dummyvial)
                self.checked_id = self.dummyvial
                success = True
                self.vialChanged.emit(self.dummyvial)
        elif self.checked_id != self.dummyvial and valvestate:  # another valve is open. close it.
            success = self._set_valveset(self.checked_id, 0)  # close open vial.
            if success:
                self.vialChanged.emit(self.dummyvial)
                QtCore.QTimer.singleShot(1000, self._valve_lockout_clear)
                self.checked_id = self.dummyvial
        else:
            logging.error("THIS SHOULDN'T HAPPEN!!!")
        return success

    def all_off(self):
        """
        Closes all valves on olfactometer. Called during startup.
        """
        logging.info('Setting all valves to OFF.')
        for button in self.vials.valves.buttons():
            vial = self.vials.valves.id(button)
            self._set_valveset(int(vial), 0, suppress_errors=True)
        QtCore.QTimer.singleShot(1000, self._valve_lockout_clear)
        self.vialChanged.emit(self.dummyvial)
        self.vials.valves.button(self.dummyvial).setChecked(True)
        self.checked_id = self.dummyvial
        return

    def _set_valve(self, valvenum, valvestate=1):
        # todo: set this to use Olfactometer method instead of hardcoding arduino protocol here.
        if valvestate:
            command = "valve {0} {1} on".format(self.slaveindex, valvenum)
        else:
            command = "valve {0} {1} off".format(self.slaveindex, valvenum)
        logging.debug(command)
        line = self.parent_device.send_command(command)
        logging.debug(line)
        return

    def _config_dummy(self, valve_config):
        dummys = []
        for k, v in valve_config.iteritems():
            if v.get('odor', '').lower() == 'dummy':
                dummy = int(k)
                dummys.append(dummy)
        if len(dummys) > 1:
            print dummys
            raise OlfaException("Configuration file must specify one dummy vial.")
        elif len(dummys) < 1:
            dummy = 4
            logging.warning('Dummy not specified, using vial 4.')
        return dummy

    def _valve_lockout_clear(self):
        self._valve_time_lockout = False
        return

    def generate_stimulus_template_string(self):
        stim_template_dict = {'odor': 'str (odorname) or int (vialnumber).',
                              'vialconc': 'float concentration of odor to be presented (optional if using vialnumber)'}
        dilutor_dict = dict()
        for i in xrange(len(self.mfcs)):
            k = 'mfc_{0}_flow'.format(i)
            stim_template_dict[k] = 'numeric flowrate'

        for i in xrange(len(self.dilutors)):
            dilutor = self.dilutors[i]
            k = 'dilutor_{0}'.format(i)
            dilutor_dict[k] = dilutor.generate_stimulus_template_string()
        stim_template_dict['dilutors'] = dilutor_dict
        return stim_template_dict

    def generate_tables_definition(self):
        import tables
        stim_template_dict = {'odor': tables.StringCol(32),
                              'vialconc': tables.Float64Col()}
        for i in xrange(len(self.mfcs)):
            k = 'mfc_{0}_flow'.format(i)
            stim_template_dict[k] = tables.Float64Col()
        if self.dilutors:
            stim_template_dict['dilutors'] = dict()
            for i in xrange(len(self.dilutors)):
                k = 'dilutor_{0}'.format(i)
                dilutor = self.dilutors[i]
                stim_template_dict['dilutors'][k] = dilutor.generate_tables_definition()
        return flatten_dictionary(stim_template_dict)



class VialGroup(QtGui.QWidget):
    """
    GUI element for vials. This contains a bunch of buttons based on the configuration file that will open specific
    vials. It also holds the identity of the vials (ie odor and concentration).
    """

    def __init__(self, parent_olfa, valve_config):
        """
        Widget containing valve operation gui and handling valve operation.

        :param parent: parent olfactometer widget.
        :param config: Single olfactometer configuration dictionary (see readme for specs on configuration file)
        :type parent_olfa: Olfactometer
        :return:
        """
        super(VialGroup, self).__init__()

        self.parent_device = parent_olfa
        self.valve_numbers = [int(s) for s in valve_config.keys()]
        self.valve_config = valve_config
        self.valve_numbers.sort()
        self.valves = QtGui.QButtonGroup(self)
        self.vgroupbox = QtGui.QGroupBox("Odor Vials", self)
        buttonlayout = QtGui.QHBoxLayout(self)
        self.vgroupbox.setLayout(buttonlayout)
        self.parent_device.vialChanged.connect(self.changeButton)
        self._checked = 0  # last checked button. updated by changeButton slot.
        dummyvial = 4  # this is default for the teensy olfa.
        for valnum in self.valve_numbers:
            val = valve_config[str(valnum)]
            button = QtGui.QPushButton(str(valnum))
            button.setMaximumWidth(30)
            button.setCheckable(True)
            try:
                if val['odor'].lower() == 'dummy':
                    dummyvial = valnum
                button.setStatusTip(val.get('status_str', "Vial: {0} [{1}]".format(val['odor'], val['conc'])))
            except KeyError:
                button.setStatusTip('No odor+conc or status_str specified.')
            self.valves.addButton(button, valnum)
            buttonlayout.addWidget(button)
        if dummyvial:
            self.dummyvial = dummyvial
            self.valves.button(self.dummyvial).setText('{0}D'.format(self.dummyvial))
        self.valves.buttonClicked[int].connect(self._button_clicked)
        self.resize(self.vgroupbox.sizeHint())
        self.setMinimumSize(self.size())
        self.setSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding)
        return


    @QtCore.pyqtSlot('int')
    def _button_clicked(self, valnum):
        """
        Button selection specific method. This is only called when using the gui, so it just does the state checks
        required for gui operation. All other checks are preformed in the setodor() method.
        :param valnum:
        :return:
        """
        if self._checked > 0:
            self.valves.button(self._checked).setChecked(True)
        self.parent_device.set_vial(valnum)
        return

    @QtCore.pyqtSlot(int)
    def changeButton(self, val):
        if self.valves.checkedId() == val:
            self._checked = 0
            self.valves.setExclusive(False)
            self.valves.button(val).setChecked(False)
            self.valves.setExclusive(True)
        else:
            self.valves.button(val).setChecked(True)
            self._checked = val
        return

    def find_odor(self, odor, conc=None):
        """
        Finds the exact matches for a vial with the specified odor / concentration.  Concentration is optional if only
        one vial with the odor is present in the configuration.

        ** Raises exemption if no matches are found or if multiple matches are found. **

        :param odor: string for odor.
        :param conc: float concentration, optional.
        :return: integer of the vial where odor/concentration found.
        :rtype: int
        """
        odor_matches = []
        for k, v in self.valve_config:
            if 'odor' in v.keys() and odor.lower() == v['odor'].lower():
                odor_matches.append(k)

        odor_conc_matches = []
        if conc:
            tol = conc * 1e-6
            for k in odor_matches:
                v = self.valve_config[k]
                if abs(v['conc'] - conc) < tol:
                    odor_conc_matches.append(k)
        else:
            odor_conc_matches = odor_matches

        if not odor_conc_matches:
            print self.valve_config
            raise OlfaException('Cannot find specified odor/concentration in vialset (odor: {0}, conc: {1}).'.format(odor, conc))
        elif len(odor_conc_matches) > 1:
            print self.valve_config
            raise OlfaException('Multiple matches for odor/concentration found in vialset (odor: {0}, conc: {1}).'.format(odor, conc))
        else:
            return int(odor_conc_matches[0])

def main():
    app = QtGui.QApplication(sys.argv)
    conf = get_olfa_config()
    olf_conf = conf['olfas'][0]
    w = TeensyOlfa(None, olf_conf)
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    import sys
    from utils import get_olfa_config
    LOGGING_LEVEL = logging.DEBUG
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(LOGGING_LEVEL)

    main()
