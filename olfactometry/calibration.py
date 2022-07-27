import numpy as np
import scipy.stats as stats
import tables as tb
from PyQt5 import QtCore, QtGui, QtWidgets
import logging
import os
import sys
from matplotlib.backends.backend_qt4agg import FigureCanvas
from matplotlib.figure import Figure
try:
    from numba import jit  # used for detrending maths. Not required.
except ImportError:
    logging.warning('Numba is not installed. Please install numba package for optimal performance!')

    def jit(a):
        return a


LIST_ITEM_ENABLE_FLAG = QtCore.Qt.ItemFlag(QtCore.Qt.ItemIsSelectable + QtCore.Qt.ItemIsEnabled +
                                           QtCore.Qt.ItemIsDragEnabled + QtCore.Qt.ItemIsUserCheckable)  # 57


class CalibrationViewer(QtWidgets.QMainWindow):
    trialsChanged = QtCore.pyqtSignal()

    def __init__(self):
        self.filters = list()
        super(CalibrationViewer, self).__init__()
        self.setWindowTitle('Olfa Calibration')
        self.statusBar()
        self.trial_selected_list = []
        self.trialsChanged.connect(self._trial_selection_changed)

        mainwidget = QtWidgets.QWidget(self)
        self.setCentralWidget(mainwidget)
        layout = QtWidgets.QGridLayout(mainwidget)
        mainwidget.setLayout(layout)

        menu = self.menuBar()
        filemenu = menu.addMenu("&File")
        toolsmenu = menu.addMenu("&Tools")

        openAction = QtWidgets.QAction("&Open recording...", self)
        openAction.triggered.connect(self._openAction_triggered)
        openAction.setStatusTip("Open a HDF5 data file with calibration recording.")
        openAction.setShortcut("Ctrl+O")
        filemenu.addAction(openAction)
        saveFigsAction = QtWidgets.QAction('&Save figures...', self)
        saveFigsAction.triggered.connect(self._saveFiguresAction_triggered)
        saveFigsAction.setShortcut('Ctrl+S')
        openAction.setStatusTip("Saves current figures.")
        filemenu.addAction(saveFigsAction)
        exitAction = QtWidgets.QAction("&Quit", self)
        exitAction.setShortcut("Ctrl+Q")
        exitAction.setStatusTip("Quit program.")
        exitAction.triggered.connect(sys.exit)
        filemenu.addAction(exitAction)
        removeTrialAction = QtWidgets.QAction("&Remove trials", self)
        removeTrialAction.setStatusTip('Permanently removes selected trials (bad trials) from trial list.')
        removeTrialAction.triggered.connect(self._remove_trials)
        removeTrialAction.setShortcut('Ctrl+R')
        toolsmenu.addAction(removeTrialAction)

        trial_group_list_box = QtWidgets.QGroupBox()
        trial_group_list_box.setTitle('Trial Groups')
        self.trial_group_list = TrialGroupListWidget()
        trial_group_layout = QtWidgets.QVBoxLayout()
        trial_group_list_box.setLayout(trial_group_layout)
        trial_group_layout.addWidget(self.trial_group_list)
        layout.addWidget(trial_group_list_box, 0, 0)
        self.trial_group_list.itemSelectionChanged.connect(self._trial_group_selection_changed)

        trial_select_list_box = QtWidgets.QGroupBox()
        trial_select_list_box.setMouseTracking(True)
        trial_select_list_layout = QtWidgets.QVBoxLayout()
        trial_select_list_box.setLayout(trial_select_list_layout)
        trial_select_list_box.setTitle('Trials')
        self.trial_select_list = TrialListWidget()
        self.trial_select_list.setMouseTracking(True)
        trial_select_list_layout.addWidget(self.trial_select_list)
        self.trial_select_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.trial_select_list.itemSelectionChanged.connect(self._trial_selection_changed)
        layout.addWidget(trial_select_list_box, 0, 1)
        self.trial_select_list.createGroupSig.connect(self.trial_group_list.create_group)

        filters_box = QtWidgets.QGroupBox("Trial filters.")
        filters_box_layout = QtWidgets.QVBoxLayout(filters_box)
        filters_scroll_area = QtWidgets.QScrollArea()
        filters_buttons = QtWidgets.QHBoxLayout()
        filters_all = QtWidgets.QPushButton('Select all', self)
        filters_all.clicked.connect(self._select_all_filters)
        filters_none = QtWidgets.QPushButton('Select none', self)
        filters_none.clicked.connect(self._select_none_filters)
        filters_buttons.addWidget(filters_all)
        filters_buttons.addWidget(filters_none)
        filters_box_layout.addLayout(filters_buttons)
        filters_box_layout.addWidget(filters_scroll_area)
        filters_wid = QtWidgets.QWidget()
        filters_scroll_area.setWidget(filters_wid)
        filters_scroll_area.setWidgetResizable(True)
        filters_scroll_area.setFixedWidth(300)
        self.filters_layout = QtWidgets.QVBoxLayout()
        filters_wid.setLayout(self.filters_layout)
        layout.addWidget(filters_box, 0, 2)

        plots_box = QtWidgets.QGroupBox()
        plots_box.setTitle('Plots')
        plots_layout = QtWidgets.QHBoxLayout()

        self.figure = Figure((9, 5))
        self.figure.patch.set_facecolor('None')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setParent(plots_box)
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        plots_layout.addWidget(self.canvas)
        plots_box.setLayout(plots_layout)
        layout.addWidget(plots_box, 0, 3)
        self.ax_pid = self.figure.add_subplot(2, 1, 1)
        self.ax_pid.set_title('PID traces')
        self.ax_pid.set_ylabel('')
        self.ax_pid.set_xlabel('t (ms)')
        # self.ax_pid.set_yscale('log')
        self.ax_mean_plots = self.figure.add_subplot(2, 1, 2)
        self.ax_mean_plots.set_title('Mean value')
        self.ax_mean_plots.set_ylabel('value')
        self.ax_mean_plots.set_xlabel('Concentration')
        self.ax_mean_plots.autoscale(enable=True, axis='both', tight=False)
        self.figure.tight_layout()

    @QtCore.pyqtSlot()
    def _list_context_menu_trig(self):
        pass

    @QtCore.pyqtSlot()
    def _filters_changed(self):
        mask = np.ones_like(self.trial_mask)
        for v in self.filters:
            mask *= v.trial_mask
        self.trial_mask = mask
        self.trial_select_list.itemSelectionChanged.disconnect(self._trial_selection_changed)
        for i in range(len(self.trial_mask)):
            hide = not self.trial_mask[i]
            it = self.trial_select_list.item(i)
            it.setHidden(hide)
            select = it.isSelected() * self.trial_mask[i]
            it.setSelected(select)
        self.trial_select_list.itemSelectionChanged.connect(self._trial_selection_changed)
        self.trial_select_list.itemSelectionChanged.emit()  # emit that something changed so that we redraw.

    @QtCore.pyqtSlot()
    def _openAction_triggered(self):
        filedialog = QtWidgets.QFileDialog(self)
        if os.path.exists('D:\\experiment\\raw_data'):
            startpath = 'D:\\experiment\\raw_data\\mouse_o_cal_cw\\sess_001'
        else:
            startpath = ''
        fn = filedialog.getOpenFileName(self, "Select a data file.", startpath, "HDF5 (*.h5)")
        if fn:
            data = CalibrationFile(str(fn))
            self.data = data
            self.trial_actions = []
            trial_num_list = []
            self.trial_select_list.clear()
            trials = self.data.trials
            for i, t in enumerate(trials):
                tstr = "Trial {0}".format(i)
                it = QtWidgets.QListWidgetItem(tstr, self.trial_select_list)
                # trial = trials[i]
                # odor = trial['odor']
                # vialconc = trial['vialconc']
                # odorconc = trial['odorconc']
                # dilution = 1000 - trial['dilution'][0]
                # trst = 'Odor: {0}, vialconc: {1}, odorconc: {2}, dilution: {3}'.format(odor, vialconc, odorconc,
                #                                                                        dilution)
                # it.setStatusTip(trst)
                trial_num_list.append(i)
            self.trial_select_list.trial_num_list = np.array(trial_num_list)
            self.trial_mask = np.ones(len(self.trial_select_list.trial_num_list), dtype=bool)
            self.build_filters(trials)
        else:
            print('No file selected.')
        return

    def build_filters(self, trials):
        while self.filters_layout.itemAt(0):
            self.filters_layout.takeAt(0)
        if self.filters:
            for f in self.filters:
                f.deleteLater()
        self.filters = list()
        colnames = trials.dtype.names
        if 'odorconc' not in colnames:
            self.error = QtWidgets.QErrorMessage()
            self.error.showMessage('Data file must have "odorconc" field to allow plotting.')
        start_strings = ('odorconc', 'olfas', 'dilutors')
        filter_fields = []
        for ss in start_strings:
            for fieldname in colnames:
                if fieldname.startswith(ss):
                    filter_fields.append(fieldname)

        for field in filter_fields:
            filter = FiltersListWidget(field)
            filter.populate_list(self.data.trials)
            filter.setVisible(False)
            self.filters.append(filter)
            box = QtWidgets.QWidget()
            box.setSizePolicy(0, 0)
            # box.setTitle(filter.fieldname)
            show_button = QtWidgets.QPushButton(filter.fieldname)
            show_button.setStyleSheet('text-align:left; border:0px')
            show_button.clicked.connect(filter.toggle_visible)
            _filt_layout = QtWidgets.QVBoxLayout(box)
            _filt_layout.addWidget(show_button)
            _filt_layout.addWidget(filter)
            _filt_layout.setSpacing(0)
            self.filters_layout.addWidget(box)
            filter.filterChanged.connect(self._filters_changed)
        for v in self.filters:
            assert isinstance(v, FiltersListWidget)

        # self.filters_layout.addWidget(QtWidgets.QSpacerItem())
        self.filters_layout.addStretch()
        self.filters_layout.setSpacing(0)

        return

    @QtCore.pyqtSlot()
    def _saveFiguresAction_triggered(self):
        # TODO: add figure saving functionality with filedialog.getSaveFileName.
        self.saveDialog = QtWidgets.QFileDialog()
        saveloc = self.saveDialog.getSaveFileName(self, 'Save figure', '', 'PDF (*.pdf);;JPEG (*.jpg);;TIFF (*.tif)')
        saveloc = str(saveloc)
        self.figure.savefig(saveloc)

    @QtCore.pyqtSlot()
    def _remove_trials(self):
        selected_idxes = self.trial_select_list.selectedIndexes()
        remove_idxes = []
        for id in selected_idxes:
            idx = id.row()
            remove_idxes.append(idx)
        while self.trial_select_list.selectedIndexes():
            selected_idxes = self.trial_select_list.selectedIndexes()
            idx = selected_idxes[0].row()
            self.trial_select_list.takeItem(idx)
        new_trials_array = np.zeros(len(self.trial_select_list.trial_num_list)-len(remove_idxes), dtype=np.int)
        ii = 0
        remove_trialnums = []
        new_trials_mask = np.zeros_like(new_trials_array, dtype=bool)
        for i in range(len(self.trial_select_list.trial_num_list)):
            if i not in remove_idxes:
                new_trials_mask[ii] = self.trial_mask[i]
                new_trials_array[ii] = self.trial_select_list.trial_num_list[i]
                ii += 1
            else:
                remove_trialnums.append(self.trial_select_list.trial_num_list[i])
        self.trial_mask = new_trials_mask
        self.trial_select_list.trial_num_list = new_trials_array

        for f in self.filters:
            f.remove_trials(remove_idxes)
        self.trial_group_list._remove_trials(remove_trialnums)

    @QtCore.pyqtSlot()
    def _trial_selection_changed(self):
        selected_idxes = self.trial_select_list.selectedIndexes()
        selected_trial_nums = []
        for id in selected_idxes:
            idx = id.row()
            trialnum = self.trial_select_list.trial_num_list[idx]
            selected_trial_nums.append(trialnum)
        self.update_plots(selected_trial_nums)
        self.trial_group_list.blockSignals(True)
        for i, g in zip(range(self.trial_group_list.count()), self.trial_group_list.trial_groups):
            it = self.trial_group_list.item(i)
            all_in = True
            group_trials = g['trial_nums']
            for t in group_trials:
                if t not in selected_trial_nums:
                    all_in = False
            if not all_in:
                it.setSelected(False)
            elif all_in:
                it.setSelected(True)
        self.trial_group_list.blockSignals(False)
        return

    @QtCore.pyqtSlot()
    def _trial_group_selection_changed(self):
        selected_idxes = self.trial_group_list.selectedIndexes()
        self._select_all_filters()
        selected_trial_nums = []
        for id in selected_idxes:
            idx = id.row()
            trialnums = self.trial_group_list.trial_groups[idx]['trial_nums']
            selected_trial_nums.extend(trialnums)
        self.trial_select_list.blockSignals(True)
        for i in range(self.trial_select_list.count()):
            item = self.trial_select_list.item(i)
            self.trial_select_list.setItemSelected(item, False)
        for i in selected_trial_nums:
            idx = np.where(self.trial_select_list.trial_num_list == i)[0][0]
            it = self.trial_select_list.item(idx)
            if not it.isSelected():
                it.setSelected(True)
        self.trial_select_list.blockSignals(False)
        self._trial_selection_changed()

    def update_plots(self, trials):
        padding = (2000, 2000)  #TODO: make this changable - this is the number of ms before/afterr trial to extract for stream.
        trial_streams = []
        trial_colors = []
        while self.ax_pid.lines:
            self.ax_pid.lines.pop(0)
        while self.ax_mean_plots.lines:
            self.ax_mean_plots.lines.pop(0)
        groups_by_trial = []
        all_groups = set()
        ntrials = len(trials)
        vals = np.empty(ntrials)
        concs = np.empty_like(vals)
        if trials:
            a = max([1./len(trials), .25])
            for i, tn in enumerate(trials):
                color = self.trial_group_list.get_trial_color(tn)
                groups = self.trial_group_list.get_trial_groups(tn)
                trial_colors.append(color)
                groups_by_trial.append(groups)
                all_groups.update(groups)
                trial = self.data.return_trial(tn, padding=padding)
                stream = remove_stream_trend(trial.streams['sniff'], (0, padding[0]))
                stream -= stream[0:padding[0]].min()
                # TODO: remove baseline (N2) trial average from this.
                trial_streams.append(stream)
                self.ax_pid.plot(stream, color=color, alpha=a)
                conc = trial.trials['odorconc']
                baseline = np.mean(stream[:2000])
                val = np.mean(stream[3000:4000]) - baseline
                vals[i] = val
                concs[i] = conc
                self.ax_mean_plots.plot(conc, val, '.', color=color)
        minlen = 500000000
        for i in trial_streams:
            minlen = min(len(i), minlen)
        streams_array = np.empty((ntrials, minlen))
        for i in range(ntrials):
            streams_array[i, :] = trial_streams[i][:minlen]
        for g in all_groups:
            mask = np.empty(ntrials, dtype=bool)
            for i in range(ntrials):
                groups = groups_by_trial[i]
                mask[i] = g in groups
            c = concs[mask]
            groupstreams = streams_array[mask]
            if len(np.unique(c)) < 2:
                self.ax_pid.plot(groupstreams.mean(axis=0), color='k', linewidth=2)
            else:
                v = vals[mask]
                a, b, _, _, _ = stats.linregress(c, v)
                color = self.trial_group_list.get_group_color(g)
                minn, maxx = self.ax_mean_plots.get_xlim()
                x = np.array([minn, maxx])
                self.ax_mean_plots.plot(x, a*x + b, color=color)
        self.ax_pid.relim()
        self.ax_mean_plots.set_yscale('log')
        self.ax_mean_plots.set_xscale('log')
        self.ax_mean_plots.relim()

        self.canvas.draw()

    @QtCore.pyqtSlot()
    def _select_none_filters(self):
        for filter in self.filters:
            filter.filterChanged.disconnect(self._filters_changed)
            filter.clearSelection()
            filter.filterChanged.connect(self._filters_changed)
        self._filters_changed()

    @QtCore.pyqtSlot()
    def _select_all_filters(self):
        for filter in self.filters:
            filter.filterChanged.disconnect(self._filters_changed)
            filter.selectAll()
            filter.filterChanged.connect(self._filters_changed)
        self._filters_changed()


class TrialListWidget(QtWidgets.QListWidget):

    createGroupSig = QtCore.pyqtSignal(list)

    def __init__(self):
        super(TrialListWidget, self).__init__()
        self.trial_num_list = np.array([])

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            super(TrialListWidget, self).mousePressEvent(event)
        elif event.button() == QtCore.Qt.RightButton:
            popMenu = QtWidgets.QMenu()
            createGroupAction = QtWidgets.QAction('Create grouping', self)
            createGroupAction.setStatusTip("Creates a trial group from the selected trials.")
            createGroupAction.triggered.connect(self._create_group)
            popMenu.addAction(createGroupAction)
            popMenu.exec_(event.globalPos())

    def _create_group(self):
        selected_trial_nums = []
        for i in self.selectedIndexes():
            ii = i.row()
            trialnum = self.trial_num_list[ii]
            selected_trial_nums.append(trialnum)
        self.createGroupSig.emit(selected_trial_nums)


class TrialGroupListWidget(QtWidgets.QListWidget):

    def __init__(self):

        super(TrialGroupListWidget, self).__init__()
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.trial_groups = []
        self.name_widget = QtWidgets.QInputDialog()
        # self.itemPressed.connect(self._mouse_pressed)


    @QtCore.pyqtSlot(QtGui.QMouseEvent)
    def mousePressEvent(self, event):
        assert isinstance(event, QtGui.QMouseEvent)
        button = event.button()
        if button == QtCore.Qt.LeftButton:
            super(TrialGroupListWidget, self).mousePressEvent(event)
        elif button == QtCore.Qt.RightButton:
            pos = event.pos()
            self.click_position = pos
            popMenu = QtWidgets.QMenu()
            delGroupAction = QtWidgets.QAction('Remove groups', self)
            delGroupAction.triggered.connect(self._remove_groups)
            delGroupAction.setStatusTip('Removes selected groupings.')
            popMenu.addAction(delGroupAction)
            changeColorAction = QtWidgets.QAction('Change color...', self)
            changeColorAction.triggered.connect(self._color_selection_triggered)
            changeColorAction.setStatusTip('Open color selection dialog to set group color.')
            popMenu.addAction(changeColorAction)
            if self.itemAt(pos):
                changeNameAction = QtWidgets.QAction('Change group name...', self)
                popMenu.addAction(changeNameAction)
                changeNameAction.triggered.connect(self._change_group_name)
            popMenu.exec_(event.globalPos())

    def get_trial_color(self, trialnum):
        color = 'b'
        for g in self.trial_groups:
            if trialnum in g['trial_nums']:
                qc = g['color']
                assert isinstance(qc, QtGui.QColor)
                color = [qc.redF(), qc.greenF(), qc.blueF()]
        return color

    def get_group_color(self, groupnum):
        g = self.trial_groups[groupnum]
        qc = g['color']
        return [qc.redF(), qc.greenF(), qc.blueF()]

    def get_trial_groups(self, trialnum):
        groups = []
        trial_groups = self.trial_groups
        for i in range(self.count()):
            g = trial_groups[i]
            if trialnum in g['trial_nums']:
                groups.append(i)
        return groups

    @QtCore.pyqtSlot(list)
    def create_group(self, trial_numbers):
        existing_group_numbers = list()
        for group in self.trial_groups:
            gname = group['name']
            try:
                gnum = int(gname[6:])
                existing_group_numbers.append(gnum)
            except ValueError:
                pass
        i = 1
        while i in existing_group_numbers:
            i += 1
        new_group_name = 'Group {0}'.format(i)
        it = QtWidgets.QListWidgetItem(new_group_name)
        it.setSelected(True)
        self.addItem(it)
        group_dict = {'name': new_group_name,
                      'trial_nums': trial_numbers,
                      'color': QtGui.QColor(0, 0, 0, 255)}  # black
        self.trial_groups.append(group_dict)
        return

    def _remove_groups(self):
        remove_idxes = []
        for i in self.selectedIndexes():
            ii = i.row()
            remove_idxes.append(ii)
        remove_idxes.sort(reverse=True)
        while self.selectedIndexes():
            i = self.selectedIndexes()[0]
            ii = i.row()
            self.takeItem(ii)
        for i in remove_idxes:
            del self.trial_groups[i]
        return

    def _color_selection_triggered(self):
        self.colorpicker = QtWidgets.QColorDialog()
        self.colorpicker.colorSelected.connect(self._change_group_color)
        self.colorpicker.show()
        return

    @QtCore.pyqtSlot(QtGui.QColor)
    def _change_group_color(self, color):
        if not self.selectedItems() and self.itemAt(self.click_position):
            item = self.itemAt(self.click_position)
            itemidx = self.indexAt(self.click_position)
            item.setForeground(color)
            ii = itemidx.row()
            tg = self.trial_groups[ii]
            tg['color'] = color
        else:
            for item in self.selectedItems():
                item.setForeground(color)
            for i in self.selectedIndexes():
                ii = i.row()
                tg = self.trial_groups[ii]
                tg['color'] = color
            self.itemSelectionChanged.emit()

    @QtCore.pyqtSlot()
    def _change_group_name(self):
        item = self.itemAt(self.click_position)
        assert isinstance(item, QtWidgets.QListWidgetItem)
        self.change_name_dialog = QtWidgets.QInputDialog()
        name, ok = self.change_name_dialog.getText(self, 'Change group name', 'Enter a new group name:')
        if name and ok:
            item.setText(name)

    def _remove_trials(self, removetrials):
        #TODO: connect this.
        for group in self.trial_groups:
            trials = group['trial_nums']
            for i in removetrials:
                if i in trials:
                    trials.remove(i)
        return


class FiltersListWidget(QtWidgets.QListWidget):

    filterChanged = QtCore.pyqtSignal()

    def __init__(self, fieldname):
        """
        build a QListWidget to be used with the calibrator.

        :param fieldname:
        :return:
        """
        super(FiltersListWidget, self).__init__()
        self.setSpacing(0)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.fieldname = fieldname
        self.list_values = np.array([])
        self.trial_values = np.array([])
        self.trial_mask = np.array([], dtype=bool)
        self.itemSelectionChanged.connect(self._selection_changed)
        return

    def populate_list(self, trials):
        self.itemSelectionChanged.disconnect(self._selection_changed)
        self.clear()
        fieldname = self.fieldname
        trial_vals = trials[fieldname]
        self.trial_values = trial_vals  # values for the field for every trial
        self.list_values = np.unique(trial_vals)  # values as they correspond to the list.
        self.trial_mask = np.ones(len(trial_vals), dtype=bool)
        for val in self.list_values:
            it = QtWidgets.QListWidgetItem(str(val), self)
            it.setSelected(True)
        self.itemSelectionChanged.connect(self._selection_changed)
        self.setMaximumHeight(self.sizeHintForRow(0) * (max(len(self.list_values), 1) + .75))
        return

    @QtCore.pyqtSlot()
    def toggle_visible(self):
        self.setVisible(not self.isVisible())
        if not self.isVisible():
            for i in range(self.count()):
                field = self.item(i)
                field.setSelected(True)

    @QtCore.pyqtSlot(QtGui.QMouseEvent)
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            selected = self.selectedIndexes()
            popMenu = QtWidgets.QMenu()
            combineAction = QtWidgets.QAction('Combine groups', self)
            combineAction.triggered.connect(self._combine)
            popMenu.addAction(combineAction)
            if len(selected) > 1:
                combineAction.setStatusTip("Combines selected filter groups into one supergroup.")
            else:
                combineAction.setEnabled(False)
                combineAction.setStatusTip("Must select at least 2 filter groups to combine.")
            popMenu.exec_(event.globalPos())
        else:
            super(FiltersListWidget, self).mousePressEvent(event)
        return

    @QtCore.pyqtSlot()
    def _combine(self):
        selected = self.selectedIndexes()
        assert len(selected) > 1
        template_i = selected[0]
        template_ii = template_i.row()
        template_val = self.list_values[template_ii]
        template_item = self.item(template_ii)
        remove_vals = []
        self.item(template_ii).setSelected(False)
        for i in self.selectedIndexes():
            ii = i.row()
            val = self.list_values[ii]
            self.trial_values[self.trial_values == val] = template_val
            remove_vals.append(val)
        while self.selectedIndexes():
            idx = self.selectedIndexes()[0].row()
            self.takeItem(idx)
        new_list_vals = []
        for i in self.list_values:
            if i not in remove_vals:
                new_list_vals.append(i)
        self.list_values = np.array(new_list_vals)
        template_item.setSelected(True)
        return

    @QtCore.pyqtSlot()
    def _selection_changed(self):
        mask = np.zeros_like(self.trial_mask)
        for i in self.selectedIndexes():
            ii = i.row()
            val = self.list_values[ii]
            mask += self.trial_values == val
        self.trial_mask = mask
        self.filterChanged.emit()
        return

    def remove_trials(self, removeidx_list):
        new_trial_val_list = []
        new_trial_mask_list = []
        for i in range(len(self.trial_values)):
            if i not in removeidx_list:
                val = self.trial_values[i]
                new_trial_val_list.append(val)
                m = self.trial_mask[i]
                new_trial_mask_list.append(m)
        self.trial_values = np.array(new_trial_val_list)
        self.trial_mask = np.array(new_trial_mask_list, dtype=bool)

    def sizeHint(self):
        s = QtCore.QSize()
        # print self.count()
        # print self.sizeHintForRow(0)
        # s.setHeight(self.sizeHintForRow(self.count()))
        s.setHeight(self.sizeHintForRow(0) * (max(len(self.list_values), 1) + .75))
        s.setWidth(super(FiltersListWidget, self).sizeHint().width())
        return s


class RichData(object):
    def __init__(self, data, attributes={}):
        """

        :param data: Data object.
        :param attributes: Dictionary of attributes (metadata) that will be included with _h5 file_nm.
        :type attributes: dict
        :type data: np.array
        :return:
        """
        self.data = data
        self.attributes = attributes
        return


class CalibrationFile(object):
    """
    Container to dynamically load and parse Voyeur hdf5 files.
    """
    def __init__(self, h5_path, stream_names=('sniff',),
                 event_names=('lick1', 'lick2'),):
        """

        :param h5_path: Path to file

        :param stream_names:
        :param event_names:
        :return:
        """
        self.fn = h5_path

        with tb.open_file(h5_path, 'r') as h5:
            h5_attr = h5.root._v_attrs
            if hasattr(h5_attr, 'stream_names'):
                stream_names = h5_attr.stream_names
                if isinstance(stream_names, str):
                    stream_names = [stream_names]
            if hasattr(h5_attr, 'event_names'):
                event_names = h5_attr.event_names
                if isinstance(event_names, str):
                    event_names = [event_names]
            self.trials = h5.root.Trials.read()
            self.streams = {}
            self.events = {}

            for stream_name in stream_names:
                self.streams[stream_name] = self._process_continuous_stream(h5, stream_name)
            for event_name in event_names:
                self.events[event_name] = self._process_event_stream(h5, event_name)

    @staticmethod
    def _process_event_stream(h5, stream_name):
        """
        This processes event streams (specifically licks), which have an on-off event time from arduino. This returns an
        n by 2 np.array with the first column being the 'on' time and the second column being the 'off' time.

        If a stream is not present in the file_nm, it should skip it without crashing and return None.

        :param h5: tables HDF5 file_nm object
        :param stream_name: string of the stream name (as enumerated in the H5 file_nm).
        :type h5: tables.File
        :type stream_name str
        :return:
        """
        st = []
        fs = None
        for trial in h5.root:
            try:
                tr_st = trial._f_get_child(stream_name).read()
                for i in tr_st:
                    if i.size % 2:
                        # Protocol convention states that event streams are sent in even length packets of [on, off]
                        # The first event is a forced off event, so we should discard this, and subsequent stream packets
                        # will be 'in-phase', meaning (ON, OFF, ON, OFF).
                        continue
                    for ii in i:
                        st.append(ii)
                # Get sampling rate for individual stream, if not available, set to voyeur default (1 kHz).
                if fs is None:
                    try:
                        fs = tr_st.attrs['sample_rate']
                    except KeyError:
                        try:
                            h5.get_node_attr('/', 'voyeur_sample_rate')
                        except AttributeError:
                            fs = 1000  # default == 1000
            except tb.NoSuchNodeError:  # if the stream does not exist in this file_nm, return None.
                return None
            except AttributeError:  # if the table doesn't have an Events table, continue to the next trial group.
                continue
        # Reshape the array so that it will be 2 columns, column 1 is 'on' and column 2 is 'off'.
        st_arr = np.array(st)
        # this will reshape the array such that the first column is "on" events, and the second is "off events"
        st_attr = {'sample_rate' : fs}
        if stream_name.startswith('lick'):
            l = st_arr.size / 2
            st_arr.shape = (l, 2)
        # stream_obj = RichData(st_arr, st_attr)
        return st_arr

    @staticmethod
    def _process_continuous_stream(h5, stream_name):
        """
        Processes continuous analog acquisition streams (ie sniff,

        :param h5: tables file_nm object.
        :param stream_name: string specifying the name of the stream to parse.
        :type h5: tables.File
        :type stream_name: str
        :return: continuous sniff array.
        """
        #TODO: extract and return sampling frequency from attributes.
        st = np.zeros(1e8, dtype=np.int16)  # allocate memory for ~ 23 hrs of recording at 1 kHz.
        fs = None
        for trial in h5.root:
            try:
                tr_events = trial.Events.read()
                tr_st = trial._f_get_child(stream_name).read()
                # HANDLE EMPTY FRAMES:
                del_list=[]
                for i, ev in enumerate(tr_events):
                    if ev[1] == 0:
                        del_list.append(i)
                if del_list:
                    tr_events = np.delete(tr_events, del_list)
                # MOVE FROM TRIAL TO CONTINUOUS STREAM:
                for ev, st_pkt in zip(tr_events, tr_st):
                    tail = ev[0]
                    head = tail - ev[1]
                    st[head:tail] = st_pkt[:]
                if fs is None:
                    try:
                        fs = tr_st.attrs['sample_rate']
                    except KeyError:
                        try:
                            h5.get_node_attr('/', 'voyeur_sample_rate')
                        except AttributeError:
                            fs = 1000  # default == 1000
            except tb.NoSuchNodeError:  # if the stream does not exist in this file_nm, return None.
                # print 'no such node'
                return None
            except AttributeError as e:  # if the table doesn't have an Events table, continue to the next trial group.
                # print 'attribute error'
                # print e
                continue
        st_attr = {'sample_rate': fs}
        # stream_obj = RichData(st[:tail], st_attr)  # last tail is the last sample we need to save
        return st[:tail]

    def return_time_period(self, start_time, end_time, read_streams=True):
        """

        :param start_time:
        :param end_time:
        :type start_time: int
        :type end_time: int
        :return:
        """

        events = {}
        streams = {}
        for k, event_node in self.events.items():
            try:
                ev = event_node.read()
            except AttributeError:
                ev = event_node
            ev_l = (ev >= start_time) * (ev <= end_time)
            if ev.ndim == 2:  # for lick handling, we need to worry about both the on and off columns:
                if np.any(ev_l):
                    ev_i = np.where(ev_l)  # returns 2 d array. 1st row is row number, 2nd is column number.
                    ev_i_l = np.min(ev_i[0])  # using first column, which corresponds to the row (each row is an event).
                    ev_i_h = np.max(ev_i[0])
                    events[k] = ev[ev_i_l:ev_i_h+1]  #need +1 here because indexing a range!!!
                else:  # Handles the case where ev_l is an empty array, in which case the min and max functions explode.
                    events[k] = np.array([], dtype=ev.dtype)
            else:
                if np.any(ev_l):
                    events[k] = ev[ev_l]
                else:
                    events[k] = np.array([], dtype=ev.dtype)
        for k, stream_node in self.streams.items():
            if read_streams:
                streams[k] = np.copy(stream_node[start_time:end_time])  # reads these values from the stream node into memory.
            elif not read_streams:
                #TODO: implement function where we can read values that we want later instead of loading into memory now.
                pass
        # assume that all 'Trials' events occur between the 'starttrial' and 'endtrial' times.
        try:
            starts = self.trials['starttrial']
            ends = self.trials['endtrial']
        except ValueError:
            starts = self.trials['trialstart']
            ends = self.trials['trialend']
        idx = (starts <= end_time) * (starts >= start_time) * (ends <= end_time) * (
        ends >= start_time)  # a bit redundant.
        trials = self.trials[idx]  # produces a tables.Table

        if trials.size == 1:
            return BehaviorTrial(start_time, end_time, trials, events, streams, self)
        else:
            return BehaviorEpoch(start_time, end_time, trials, events, streams, self)

    def return_trial(self, trial_index, padding=(2000, 2000)):
        """

        :param trial_index: int index of the trial within the Trials table.
        :param padding:
        :type trial_index: int
        :type padding:tuple of [int]
        :return:
        """
        trial = self.trials[trial_index]
        try:
            start = trial['starttrial']
            end = trial['endtrial']  # don't really care here whether this is higher than the record: np will return
            # only as much as it has.
        except IndexError:
            start = trial['trialstart']
            end = trial['trialend']
        if not start or not end:
            return None
        if np.isscalar(padding):
            padding = [padding, padding]
        if start >= padding[0]:  # don't want the start time to be before 0
            start -= padding[0]
        end += padding[1]
        return self.return_time_period(start, end)


@jit  # this is a >30x performance over native python (30 ms vs <1 ms)
def remove_stream_trend(stream, slice_indeces, x=None):
    """
    Finds trend in stream[slice_indeces] using linear regression and removes it from entire stream

    :param stream: stream to detrend.
    :param sample_indeces: (start, stop) indeces prior to stimulus onset. This defines the trend.
    :param x: optional x array.
    :return: detrended array
    :type stream: np.array
    :rtype: np.array
    """

    stream_slice = stream[slice_indeces[0]:slice_indeces[1]]
    if not x:
        x = np.linspace(0, len(stream_slice)-1, len(stream_slice))
    a, b, _, _, _ = stats.linregress(x, stream_slice)
    for i in range(len(stream)):
        stream[i] -= i * a
    return stream


class BehaviorEpoch(object):
    def __init__(self, start_time, end_time, trials=np.ndarray([]), events={}, streams={}, parent=None, **kwargs):
        """
        Container for arbitrary epochs of behavior data. Inherits metadata from the parent.

        :param parent: Parent behavior
        :param trials: Trials object.
        :param events: Dict of events.
        :param streams: Dict of streams.
        :type parent: BehaviorRun
        :type trials: np.ndarray
        :type events: dict
        :type streams: dict
        :return:
        """
        # trials.__getitem__
        self.trials = trials
        self.events = events
        self.streams = streams
        self.parent_epoch = parent
        self.start_time = start_time
        self.end_time = end_time
        return


class BehaviorTrial(BehaviorEpoch):
    """
    Contains behavior epoch data for a single trial.
    """

    def __init__(self, *args, **kwargs):
        """
        BehaviorEpoch that contains a single trial's worth of data.
        :param args:
        :return:
        """
        super(BehaviorTrial, self).__init__(*args, **kwargs)
        # just want to check that this is in fact representing a single trial, and not many.
        assert len(self.trials) == 1, 'Warning: cannot initialize a BehaviorTrial object with more than one trial.'


def main(config_path=''):
    app = QtWidgets.QApplication(sys.argv)
    w = CalibrationViewer()
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