__author__ = 'labadmin'
from PyQt4 import QtCore, QtGui
import olfactometer
from serial.tools import list_ports
import logging

class Cleaner(QtGui.QWidget):
    def __init__(self, config=None):
        super(Cleaner, self).__init__()
        self.i = 0
        self.vial_open = False
        self.olfactometer = None
        self.setWindowTitle('Olfactometer Cleaner')
        olfa_type_select = QtGui.QComboBox()
        olfa_type_select.addItem('Select olfa type')
        olfa_type_select.addItem('Teensy Olfactometer')
        olfa_type_select.activated[str].connect(self._type_selected)
        self.main_layout = QtGui.QVBoxLayout()
        init_layout = QtGui.QHBoxLayout()
        init_layout.addWidget(olfa_type_select)
        self.init_widget = QtGui.QWidget()
        self.init_widget.setLayout(init_layout)

        self.main_layout.addWidget(self.init_widget)
        self.setLayout(self.main_layout)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._continue_run)
        self.timer.setSingleShot(True)

        self.rungroup = QtGui.QGroupBox()
        run_layout = QtGui.QGridLayout()
        self.rungroup.setLayout(run_layout)
        self.valve_clean_time_selector = QtGui.QSpinBox()
        self.valve_clean_time_selector.setRange(1, 120)
        self.valve_clean_time_selector.setSingleStep(5)
        self.valve_clean_time_selector.setSuffix(' sec')
        self.valve_clean_time_selector.setValue(30)
        self.valve_clean_time_selector_lbl = QtGui.QLabel('Valve clean time:')
        run_layout.addWidget(self.valve_clean_time_selector_lbl, 0, 2, 1, 1)
        run_layout.addWidget(self.valve_clean_time_selector, 0, 3, 1, 1)

        self.dummy_flush_time_selector = QtGui.QSpinBox()
        self.dummy_flush_time_selector.setRange(1, 120)
        self.dummy_flush_time_selector.setSingleStep(1)
        self.dummy_flush_time_selector.setSuffix(' sec')
        self.dummy_flush_time_selector.setValue(3)
        self.dummy_flush_time_selector_lbl = QtGui.QLabel('Dummy flush time:')
        run_layout.addWidget(self.dummy_flush_time_selector_lbl, 1, 2, 1, 1)
        run_layout.addWidget(self.dummy_flush_time_selector, 1, 3, 1, 1)

        self.n_runs_selector = QtGui.QSpinBox()
        self.n_runs_selector.setRange(1, 500)
        self.n_runs_selector.setSingleStep(1)
        self.n_runs_selector.setValue(2)
        self.n_runs_selector_lbl = QtGui.QLabel('Number runs:')
        run_layout.addWidget(self.n_runs_selector_lbl, 2, 2, 1, 1)
        run_layout.addWidget(self.n_runs_selector, 2, 3, 1, 1)

        run_type_bgroup = QtGui.QButtonGroup(self)
        run_type_widget = QtGui.QGroupBox()
        run_type_widget.setTitle('Run type:')
        run_type_layout = QtGui.QHBoxLayout()
        run_type_widget.setLayout(run_type_layout)
        liquid_flush_button = QtGui.QRadioButton('Liquid Flush')
        liquid_flush_button.clicked.connect(self._liquid_flush_selected)
        liquid_flush_button.setChecked(True)
        self._liquid_flush_selected(True)
        run_type_layout.addWidget(liquid_flush_button)
        run_type_bgroup.addButton(liquid_flush_button)
        air_flush_button = QtGui.QRadioButton('Air Flush')
        air_flush_button.clicked.connect(self._air_flush_selected)
        run_type_layout.addWidget(air_flush_button)
        run_type_bgroup.addButton(air_flush_button)

        run_layout.addWidget(run_type_widget, 0, 0, 2, 2)
        
        self.run_button = QtGui.QPushButton('Start')
        self.run_button.clicked.connect(self._run_button_pressed)
        self.run_button.setCheckable(True)
        self.run_button.setChecked(False)

        self.reset_button = QtGui.QPushButton('Reset')
        self.reset_button.clicked.connect(self._reset_button_pressed)

        run_layout.addWidget(self.run_button, 2, 0, 1, 1)
        run_layout.addWidget(self.reset_button, 2, 1, 1, 1)

        self.progress_bar = QtGui.QProgressBar()
        progress_bar_lbl = QtGui.QLabel('Progress:')
        run_layout.addWidget(progress_bar_lbl, 3,0,1,1)
        run_layout.addWidget(self.progress_bar, 3, 1, 1, 3)
        self.progress = 0.

    def _type_selected(self, typestr):
        if typestr == 'Select olfa type':
            pass
        elif typestr == "Teensy Olfactometer":
            self.olfa_config = teensy
            layout = self.init_widget.layout()
            self.arduino_serial_select = QtGui.QComboBox()
            self.arduino_serial_select.addItem('Select COM port')
            for ser in list_ports.comports():
                ser_str = '{0}: {1}'.format(ser[0], ser[1])
                self.arduino_serial_select.addItem(ser_str)
            self.arduino_serial_select.activated[str].connect(self._arduino_com_selected)
            layout.addWidget(self.arduino_serial_select)

    def _arduino_com_selected(self, com_str):
        if self.olfactometer is not None:
            self.olfactometer.close_serial()
            self.olfactometer.deleteLater()
            self.valve_select.deleteLater()
        if com_str == 'Select COM port':
            return
        else:
            cp = com_str.split(':')[0]
            port = int(cp[3:])
            teensy['com_port'] = port
            self.olfactometer = olfactometer.TeensyOlfa(None, config_dict=teensy)
            self.main_layout.addWidget(self.olfactometer)
            vials = [int(v) for v in teensy['Vials'].keys()]
            vials.sort()
            self.valve_select = ValveSelector(self, vials, default_off=[self.olfactometer.dummyvial])
            self.main_layout.addWidget(self.valve_select)
            self.main_layout.addWidget(self.rungroup)
        return

    def _air_flush_selected(self, selected):
        if selected:
            self.n_runs_selector.setValue(300)
            self.dummy_flush_time_selector.setValue(2)
            self.valve_clean_time_selector.setValue(10)

    def _liquid_flush_selected(self, selected):
        if selected:
            self.n_runs_selector.setValue(2)
            self.dummy_flush_time_selector.setValue(5)
            self.valve_clean_time_selector.setValue(30)

    def _run_button_pressed(self, checked):
        if checked:
            self.start_run()
            logging.info('Starting rn')
        else:
            self.pause_run()
            logging.info('Pausing run')
        pass

    def start_run(self):
        self.run_button.setText('Pause')
        self.run_button.setChecked(True)
        self.progress_bar.setValue(self.progress)
        self._continue_run()

    def _continue_run(self):
        vials_to_clean = self.valve_select.vials_to_clean
        i = self.i % len(vials_to_clean)
        vial = vials_to_clean[i]
        if not self.vial_open:
            self.olfactometer.set_vial(vial, valvestate=1, override_checks=True)
            self.vial_open = True
            t_ms = self.valve_clean_time_selector.value() * 1000
            self.timer.start(t_ms)  # already connected the timer to the the continue_run method.
        else:
            self.olfactometer.set_vial(vial, valvestate=0, override_checks=True)
            self.vial_open = False
            self.i += 1  # now that we're done cleaning that vial, we'll iterate to move to the next vial.

            progress = float(self.i) / (len(vials_to_clean) * self.n_runs_selector.value()) * 100
            self.progress_bar.setValue(int(progress))
            self.progress = progress

            if int(self.i/len(vials_to_clean)) >= self.n_runs_selector.value():
                self._reset_button_pressed()
                self.progress_bar.setValue(100)
                self.olfactometer.set_vial(self.olfactometer.dummyvial, valvestate=1)
            else:
                t_ms = self.dummy_flush_time_selector.value() * 1000
                self.timer.start(t_ms)


    def pause_run(self):
        self.run_button.setText('Start')
        self.run_button.setChecked(False)
        self.timer.stop()
        if self.vial_open:
            i = self.i % len(self.valve_select.vials_to_clean)
            vial = self.valve_select.vials_to_clean[i]
            self.olfactometer.set_vial(vial, valvestate=0)
            self.vial_open = False
        self.olfactometer.set_vial(self.olfactometer.dummyvial, valvestate=0)  # stop flow through dummy.

    def _reset_button_pressed(self):
        self.pause_run()
        progress = 0.
        self.progress_bar.setValue(progress)
        self.progress = progress
        self.i = 0  # now we're going to start from the beginning instead of from the last vial opened.
    
    def close(self):
        if self.olfactometer:
            self.olfactometer.all_off()
        super(Cleaner, self).close()


class ValveSelector(QtGui.QGroupBox):
    def __init__(self, parent, vials, default_off=[]):
        super(ValveSelector, self).__init__()
        layout = QtGui.QHBoxLayout()
        self.setLayout(layout)
        self.setTitle('Select vial positions to clean:')
        button_group = QtGui.QButtonGroup(self)
        button_group.setExclusive(False)
        button_group.buttonClicked[QtGui.QAbstractButton].connect(self._button_clicked)
        self.vials_to_clean = []
        for i in vials:
            b = QtGui.QCheckBox(str(i))
            layout.addWidget(b)
            button_group.addButton(b)
            if i not in default_off:
                self.vials_to_clean.append(i)
                b.setChecked(True)
            else:
                b.setChecked(False)
        self.vials_to_clean.sort()
        return

    @QtCore.pyqtSlot(QtGui.QAbstractButton)
    def _button_clicked(self, button):
        vial = int(button.text())
        if button.isChecked():
            if vial not in self.vials_to_clean:
                self.vials_to_clean.append(vial)
                self.vials_to_clean.sort()
        else:
            if vial in self.vials_to_clean:
                self.vials_to_clean.remove(vial)
        return




teensy = {"Vials": {str(n): {} for n in range(1, 13)},  # all possible vials.
          "slave_index": 1,
          'com_port': 4,
          'MFCs': []}


def main():
    import sys
    LOGGING_LEVEL = logging.INFO
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(LOGGING_LEVEL)

    app = QtGui.QApplication(sys.argv)
    w = Cleaner()
    w.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()