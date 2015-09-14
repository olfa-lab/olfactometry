__author__ = 'chris'

from PyQt4 import QtCore, QtGui
from utils import get_olfa_config
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
        self.olfas = self.add_olfas(self.olfa_specs)

        self.setWindowTitle("Olfactometry")
        layout = QtGui.QVBoxLayout()
        for olfa in self.olfas:
            layout.addWidget(olfa)
        central_widget = QtGui.QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setLayout(layout)
        self.statusBar()

        menubar = self.menuBar()
        self.buildmenubar(menubar)
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('CleanLooks'))

    def buildmenubar(self, bar):
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


    def add_olfas(self, olfa_specs):
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

    def add_dillutors(self, dilutor_specs):
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
        self.olfas = self.add_olfas(self.olfa_specs)
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
