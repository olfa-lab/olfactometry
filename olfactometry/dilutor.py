from PyQt5 import QtCore, QtWidgets
from serial import SerialException
from .mfc import MFCclasses, MFC
import logging
from .utils import OlfaException, connect_serial


class Dilutor(QtWidgets.QGroupBox):
    """
    Dillutor v1 by CW.
    """
    # TODO: add dilution factor slider to gui.
    # TODO: implement json? dillution factor calibration system
    def __init__(self, parent, config, polling_interval=1.1):
        super(Dilutor, self).__init__()

        baudrate = 115200
        com_port = config['com_port']
        self.serial = connect_serial(com_port, baudrate=baudrate, timeout=1, writeTimeout=1)
        self._eol = '\r'

        layout = QtWidgets.QHBoxLayout()
        self.mfcs = self._config_mfcs(config['MFCs'])
        self.polling_interval = polling_interval
        self.mfc_timer = self.start_mfc_polling()

        # GUI:
        for mfc in self.mfcs:
            layout.addWidget(mfc)

        self.setTitle('Dilutor (COM:{0})'.format(com_port))
        self.setLayout(layout)

        return

    def _config_mfcs(self, mfc_config):
        mfcs = [None, None]
        gas_positions = {'vac': 0, 'air': 1}
        for mfc_spec in mfc_config:
            mfc_type = mfc_spec['MFC_type']
            gas = mfc_spec['gas']
            mfc = MFCclasses[mfc_type](self, mfc_spec)
            mfcs[gas_positions[gas.lower()]] = mfc
        return mfcs

    def start_mfc_polling(self, polling_interval_sec=2.):
        logging.debug('Starting MFC polling.')
        mfc_timer = QtCore.QTimer()
        mfc_timer.timeout.connect(self.poll_mfcs)
        polling_interval_ms = int(polling_interval_sec * 1000)
        mfc_timer.start(polling_interval_ms)
        return mfc_timer

    @QtCore.pyqtSlot()
    def poll_mfcs(self):
        for i in range(len(self.mfcs)):
            mfc = self.mfcs[i]
            assert isinstance(mfc, MFC)
            mfc.poll()
        return

    @QtCore.pyqtSlot()
    def stop_mfc_polling(self):
        self.mfc_timer.stop()
        return

    @QtCore.pyqtSlot()
    def restart_mfc_polling(self):
        self.mfc_timer.start(int(self.polling_interval*1000))  # from seconds to msec
        return

    def send_command(self, command, tries=1):
        # must send with '\r' end of line
        self.serial.flushInput()
        for i in range(tries):
            self.serial.write(bytes(command, 'utf-8'))
            line = self.read_line()
        return line

    def read_line(self):
        """
        reimplemented read line to allow for a non-standard end-of-line character used by Alicats.
        :return:
        """
        eol = self._eol
        leneol = len(eol)
        line = bytearray()
        while True:
            c = self.serial.read(1)
            if c:
                line += c
                if line[-leneol:] == eol:
                    break
            else:
                break
        return bytes(line)

        # this implementation must use '\r' end of line.

        line = None
        try:
            pass
            #
            # line = self.serial.readline()
        except SerialException as e:
            print('pySerial exception: Exception that is raised on write timeouts')
            print(e)
        return line

    def close_serial(self):
        """
        Closes physical serial connect used during restarts.

        :return:
        """
        self.serial.close()

    def set_stimulus(self, stim_dict):
        """
        Sets dilutor flows based on stimulus dictionary defined in generate_stimulus_template.

        :param stim_dict:
        :
        :return: True if set completed.
        """
        a = stim_dict['vac_flow']
        b = stim_dict['air_flow']
        return self.set_flows((a, b))

    def set_flows(self, flows):
        """
        Sets flowrates of attached MFCs.

        :param flows: iterable of flowrates to set MFCs, ordered as (vac, air).
        :return:
        """
        if not len(flows) == len(self.mfcs):
            ex_str = 'Number of flows specified ({0}) not equal to number of MFCs in Dilutor ({1}).'.format(len(flows),
                                                                                                         len(self.mfcs))
            raise OlfaException(ex_str)
        else:
            successes = []
            for mfc, flow in zip(self.mfcs, flows):
                success = mfc.set_flowrate(flow)
                successes.append(success)
            return all(successes)

    def generate_stimulus_template_string(self):
        stim_template_dict = {'dilution_factor': 'float (optional)',
                              'vac_flow': 'int flowrate in flow units',
                              'air_flow': 'int flowrate in flow units',}
        return stim_template_dict

    def generate_tables_definition(self):
        import tables
        tables_def = {'dilution_factor': tables.Float64Col(),
                      'vac_flow': tables.Float64Col(),
                      'air_flow': tables.Float64Col()}
        return tables_def


DILUTORS = {'serial_forwarding': Dilutor,}