__author__ = 'chris'

from PyQt4 import QtCore, QtGui
from utils import get_olfa_config, OlfaException
from olfactometer import TeensyOlfa
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
            self.config_fn, config_obj = get_olfa_config()
        self.olfa_specs = config_obj['Olfactometers']
        self.olfas = self._add_olfas(self.olfa_specs)
        try:
            self.dilutor_specs = config_obj['Dilutors']  # configure *global* dilutors.
            self.dilutors = self._add_dillutors(self.dilutor_specs)
        except KeyError:  # no global Dilutors are specified, which is OK!
            pass
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

        :param olfa_dilution_flows: list of lists specifying dilution flows for dilutors attached to olfactometers:
        [[olfa1_vac_flow, olfa1_air_flow], [olfa2_vac_flow...], ...]
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
    def _open_config(self):
        os.startfile(self.config_fn)
        return

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
