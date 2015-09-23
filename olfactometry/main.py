__author__ = 'chris'

from PyQt4 import QtCore, QtGui
from utils import get_olfa_config, OlfaException, flatten_dictionary
from olfactometer import TeensyOlfa, Olfactometer
from dilutor import Dilutor
from pprint import pformat
import logging
import os


class Olfactometers(QtGui.QMainWindow):
    """

    Also, acts like a list of olfactometers (actual objects stored in self.olfas). So Olfactometers[0] returns the first
    olfactometer in the configuration file.
    """

    def __init__(self, parent=None, config_obj=None):
        super(Olfactometers, self).__init__()  # not sure if this will work.
        if not config_obj:
            self.config_fn, self.config_obj = get_olfa_config()
        elif isinstance(config_obj, dict):
            self.config_obj = config_obj
        elif isinstance(config_obj, str):
            self.config_fn, self.config_obj = get_olfa_config(config_obj)
        else:
            raise OlfaException("Passed config_obj is of unknown type. Can be a dict, path to JSON or None.")
        self.olfa_specs = self.config_obj['Olfactometers']
        self.olfas = self._add_olfas(self.olfa_specs)
        try:
            self.dilutor_specs = self.config_obj['Dilutors']  # configure *global* dilutors.
            self.dilutors = self._add_dillutors(self.dilutor_specs)
        except KeyError:  # no global Dilutors are specified, which is OK!
            self.dilutors = []
        self.setWindowTitle("Olfactometry")
        layout = QtGui.QVBoxLayout()
        for olfa in self.olfas:
            layout.addWidget(olfa)
        central_widget = QtGui.QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setLayout(layout)
        self.statusBar()

        menubar = self.menuBar()
        self._buildmenubar(menubar)
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('CleanLooks'))

    def set_stimulus(self, stimulus_dictionary):
        """
        This sets the stimulus for ALL olfactometers and attached devices using a single dictionary. This dictionary
        format depends on the configuration of the attached devices. Within the gui, a template can be generated for the
        current configuration from the "Tools:Stimulus Template..." function.

        :param stimulus_dictionary: Dictionary of stimulus parameters for olfactory stimulus.
        :type stimulus_dictionary: dict
        :return: True if all successes appear to be successful.
        :rtype: bool
        """
        std = stimulus_dictionary
        n_olfas = len(std['olfas'])
        successes = []
        for i in xrange(n_olfas):
            k = 'olfa_{0}'.format(i)
            o = std['olfas'][k]
            olfa = self.olfas[i]
            success = olfa.set_stimulus(o)
            successes.append(success)
        if 'dilutors' in std.keys():
            for i in xrange(len(std['dilutors'])):
                dil = self.dilutors[i]
                k = 'dilutor_{0}'.format(i)
                d = std['dilutors'][k]
                success = dil.set_stimulus(d)
                successes.append(success)
        return all(successes)

    def set_vials(self, vials, valvestates=None):
        """
        Sets vials on all olfactometers based on list of vial numbers provided. 0 or None will open no vial for that
        olfa.

        :param vials: list or tuple of vials.
        :param valvestates: (optional) list of valvestates (True opens, False closes)
        :return: True if all setting appears successful.
        :rtype: bool
        """
        successes = []
        if not len(vials) == len(self.olfas):
            raise OlfaException('Number of vials specified must be equal to the number of olfactometers.')
        if not valvestates:
            valvestates = [None] * len(vials)
        for vial, olfa, valvestate in zip(vials, self.olfas, valvestates):
            if vial:
                success = olfa.set_vial(vial, valvestate)
                successes.append(success)
        return all(successes)

    def set_odors(self, odors, concs=None, valvestates=None):
        """
        Sets odors on all olfactometers based on list of odor strings provided. Empty string or None will open no odor.

        :param odors: list or tuple of strings specifying odors by olfactometer (one string per olfactometer).
        :param valvestates: (optional) list of valvestates (True opens, False closes)
        :return: True if all setting appears successful.
        :rtype: bool
        """

        successes = []
        if not len(odors) == len(self.olfas):
            raise OlfaException('Number of odors specified must be equal to the number of olfactometers.')
        if not valvestates:
            valvestates = [None] * len(odors)  #just allows us to zip through this. Olfactometer will deal with Nones.
        if not concs:
            concs = [None] * len(odors)  # just allows us to zip through this. Olfactometer will deal with Nones.
        for odor, conc, olfa, valvestate in zip(odors, concs, self.olfas, valvestates):
            if odor:
                success = olfa.set_odor(odor, conc, valvestate)
                successes.append(success)
        return all(successes)

    def set_dummy_vials(self):
        """
        Call this to close all odorvials. Used after trial complete.

        :return: True if all dummys set.
        :rtype: bool
        """
        successes = []
        for o in self.olfas:
            success = o.set_dummy_vial()
            successes.append(success)
        return all(successes)

    def set_flows(self, flows):
        """
        Sets MFC flows for all olfactometers.

        :param flows: List of flowrates (ie "[(olfa1_MFCflow1, olfa1_MFCflow2), (olfa2_MFCflow1,...),...]")
        :return: True if sets appear to be successful as reported by olfas.
        :rtype: bool
        """
        successes = []
        if not len(self.olfas) == len(flows):
            raise OlfaException('Number of flowrates specified must equal then number of olfactometers.')
        for olfa, flow in zip(self.olfas, flows):
            if flow:
                success = olfa.set_flows(flow)
                successes.append(success)
        return all(successes)

    def set_dilution_flows(self, olfa_dilution_flows=(), global_dilution_flows=()):
        """
        This sets dilution flows for dilutors attached to olfactometers or global dilutors attached to all olfactometers.
        Each flow spec is specified by a list of flowrates: [vac, air].

        :param olfa_dilution_flows: list of lists of lists specifying dilution flows for dilutors attached to
        olfactometers: [[[olfa1_vac1, olfa1_air1], [olfa1_vac2, olfa1_air2], ...], [[olfa2_vac1, olfa2_vac2],... ], ...]
        :param global_dilution_flows: sets flow for global dilutor (ie those attached to all olfactometers):
        [[global1_vac, global1_air], [global2_vac,...], ...]
        :return: True if all setting appears successful.
        :rtype: bool
        """

        olfa_succeses = []
        global_successes = []
        if not len(olfa_dilution_flows) == len(self.olfas):
            raise OlfaException('Number of flowrate pairs for olfa_dilution_flows parameter '
                                'must be consistent with number of olfactometers.\n\n'
                                '\t\t( i.e. "[(olfa1_vac, olfa1_air), (olfa2_vac, olfa2_air), ...]" )')
        if olfa_dilution_flows:
            for olfa, flows in zip(self.olfas, olfa_dilution_flows):
                success = olfa.set_dilution(flows=flows)
                olfa_succeses.append(success)
        olfa_success = all(olfa_succeses)
        if not len(global_dilution_flows) == len(self.dilutors):
            raise OlfaException('Number of flowrate pairs for global_dilution_flows parameter must be consistent with '
                                'number of global dilutors present in configuration. \n\n'
                                '\t\tThis does not include dilutors embedded in olfactometer objects!!!')
        if global_dilution_flows:
            for dilutor, flows in zip(self.dilutors, global_dilution_flows):
                success = dilutor.set_flows(flows)
                global_successes.append(success)
        global_success = all(global_successes)
        return all((olfa_success, global_success))

    def check_flows(self):
        """
        Check that all olfactometers' MFCs are reporting flow.
        :return: True if all olfas' MFCs are flowing.
        :rtype: bool
        """
        successes = []
        for o in self.olfas:
            successes.append(o.check_flows())
        return all(successes)

    def _buildmenubar(self, bar):
        assert isinstance(bar, QtGui.QMenuBar)
        filemenu = bar.addMenu('&File')
        toolsmenu = bar.addMenu('&Tools')

        reloadAction = QtGui.QAction('&Reload configuration', self)
        reloadAction.setStatusTip('Destroys current olfactometers and reloads with JSON at {0}'.format(self.config_fn))
        reloadAction.triggered.connect(self._reload_config)
        filemenu.addAction(reloadAction)

        openConfigAction = QtGui.QAction("Open &configuration", self)
        openConfigAction.triggered.connect(self._open_config)
        openConfigAction.setStatusTip("Opens config file: {0} in system text editor.".format(self.config_fn))
        toolsmenu.addAction(openConfigAction)

        stimTemplateAction = QtGui.QAction('Stimulus template...', self)
        stimTemplateAction.setStatusTip('Displays a stimulus dictionary template based on current configuration.')
        stimTemplateAction.triggered.connect(self._stim_template_display)
        toolsmenu.addAction(stimTemplateAction)

        calibrationAction = QtGui.QAction('Open calibration...', self)
        calibrationAction.setStatusTip('Opens calibration widget.')
        calibrationAction.triggered.connect(self._start_calibration)
        filemenu.addAction(calibrationAction)

        exitAction = QtGui.QAction("&Quit", self)
        exitAction.setShortcut("Ctrl+Q")
        exitAction.setStatusTip("Quit program.")
        exitAction.triggered.connect(QtGui.qApp.quit)
        filemenu.addAction(exitAction)


    def _add_olfas(self, olfa_specs):
        """

        :param olfa_specs: tuple of olfactometer specs from olfa dict.
        :return:
        """
        olfas = list()
        for i in xrange(len(olfa_specs)):
            o = olfa_specs[i]
            try:
                olfatype = o['olfa_interface']
            except KeyError:
                olfatype = 'teensy'
            if olfatype == 'teensy':
                olfa = TeensyOlfa(self, config_dict=o)
                olfa.setTitle('Olfactometer {0}'.format(i))
            olfas.append(olfa)
        return olfas

    def _add_dillutors(self, dilutor_specs):
        pass

    @QtCore.pyqtSlot()
    def _reload_config(self):
        try:
            _, config_obj = get_olfa_config(self.config_fn)
            self.olfa_specs = config_obj['Olfactometers']
        except ValueError as e:
            errorbox = QtGui.QErrorMessage(self)
            errorbox.showMessage('Error, JSON is not valid: {0}'.format(e.message))
            return
        logging.info('Reloading config from {0}'.format(self.config_fn))
        for olfa in self.olfas:
            olfa.close_serial()
            olfa.deleteLater()  # deletes all timers, etc.
        self.olfas = []
        _, config_obj = get_olfa_config(self.config_fn)
        self.olfa_specs = config_obj['Olfactometers']
        self.olfas = self._add_olfas(self.olfa_specs)
        for o in self.olfas:
            self.centralWidget().layout().addWidget(o)
        return

    @QtCore.pyqtSlot()
    def _stim_template_display(self):
        template_string = self.generate_stimulus_template()
        print template_string
        d = QtGui.QWidget()
        d.setWindowTitle('Stimulus template')
        l = QtGui.QVBoxLayout(d)
        desc_box = QtGui.QLabel()
        desc_box.setText('The text below is a template for a stimulus dictionary for this configuration.\n\nPassing this '
                         'dictionary to the Olfactometers.set_stimulus function will set the stimulus for all '
                         'olfactometers and dilutors in the configuration.')
        desc_box.setWordWrap(True)
        l.addWidget(desc_box)
        text_box = QtGui.QPlainTextEdit()
        text_box.setReadOnly(True)
        # text_box.setPlainText(template_string)
        text_box.setPlainText(template_string)
        text_box.setFont(QtGui.QFont("Courier"))
        text_box.setLineWrapMode(text_box.NoWrap)
        text_box.setMinimumSize(text_box.document().size().toSize())
        l.addWidget(text_box)
        self.stimulus_template_dialog = d
        self.stimulus_template_dialog.show()

    def generate_stimulus_template(self):
        stimulus_template = {}
        olfa_templates = {}
        dilutor_templates = {}

        for i in xrange(len(self.olfas)):
            olfa = self.olfas[i]
            k = 'olfa_{0}'.format(i)
            olfa_templates[k] = olfa.generate_stimulus_template_string()
        stimulus_template['olfas'] = olfa_templates
        if self.dilutors:
            for i in xrange(len(self.dilutors)):
                dil = self.dilutors[i]
                k = 'dilutor_{0}'.format(i)
                dilutor_templates[k] = dil.generate_stimulus_templates()
            stimulus_template['dilutors'] = dilutor_templates
        s = pformat(stimulus_template, width=120)
        return s

    def generate_tables_definition(self):
        definition = dict()
        dilutor_def = dict()
        olfa_definition = dict()
        for i, dilutor in enumerate(self.dilutors):
            assert isinstance(dilutor, Dilutor)
            k = 'dilutor_{0}'.format(i)
            dilutor_def[k] = dilutor.generate_tables_definition()
        for i, olfa in enumerate(self.olfas):
            assert isinstance(olfa, Olfactometer)
            k = 'olfa_{0}'.format(i)
            olfa_definition[k] = olfa.generate_tables_definition()
        definition['olfas'] = olfa_definition
        definition['dilutors'] = dilutor_def
        return flatten_dictionary(definition)

    @QtCore.pyqtSlot()
    def _open_config(self):
        os.startfile(self.config_fn)
        return

    def _start_calibration(self):
        import calibration  # only import if required, because we have some other imports that will waste memory.
        self.cal_view = calibration.CalibrationViewer()
        self.cal_view.show()

    def __getitem__(self, olfa_idx):
        return self.olfas[olfa_idx]

    def __len__(self):
        return len(self.olfas)

    def close(self):
        """
        Reimplementation of close function. If the window has no parent, it will exit as normal. However, if the window
        has a parent (ie Voyeur), the window will hide without deleting the underlying C++ object.
        """
        if self.parent is None:
            super(Olfactometers, self).close()
        else:
            self.hide()

    def close_serials(self):
        for o in self.olfas:
            o.close_serial()
        for d in self.dilutors:
            d.close_serial()


def main(config_path=''):
    import sys
    app = QtGui.QApplication(sys.argv)
    w = Olfactometers(None, config_path)
    w.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    LOGGING_LEVEL = logging.DEBUG
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(LOGGING_LEVEL)

    main()
