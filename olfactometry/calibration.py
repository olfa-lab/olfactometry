from __future__ import division
import numpy as np
import tables as tb
from PyQt4 import QtCore, QtGui
import logging
import os
from matplotlib.backends.backend_qt4agg import FigureCanvas, NavigationToolbar2QTAgg
from matplotlib.figure import Figure

__author__ = 'chris'

LIST_ITEM_ENABLE_FLAG = QtCore.Qt.ItemFlag(QtCore.Qt.ItemIsSelectable + QtCore.Qt.ItemIsEnabled +
                                           QtCore.Qt.ItemIsDragEnabled + QtCore.Qt.ItemIsUserCheckable)  # 57


class CalibrationViewer(QtGui.QMainWindow):
    trialsChanged = QtCore.pyqtSignal()

    def __init__(self):
        super(CalibrationViewer, self).__init__()
        self.filters = [FiltersListWidget('odor'),
                        FiltersListWidget('vialconc'),
                        FiltersListWidget('odorconc'),
                        DilutionListWidget('dilution')]
        self.setWindowTitle('Olfa Calibration')
        self.statusBar()
        self.trial_selected_list = []
        self.trialsChanged.connect(self._trial_selection_changed)

        mainwidget = QtGui.QWidget(self)
        self.setCentralWidget(mainwidget)
        layout = QtGui.QGridLayout(mainwidget)
        mainwidget.setLayout(layout)

        menu = self.menuBar()
        filemenu = menu.addMenu("&File")
        toolsmenu = menu.addMenu("&Tools")

        openAction = QtGui.QAction("&Open recording...", self)
        openAction.triggered.connect(self._openAction_triggered)
        openAction.setStatusTip("Open a HDF5 data file with calibration recording.")
        openAction.setShortcut("Ctrl+O")
        filemenu.addAction(openAction)
        saveFigsAction = QtGui.QAction('&Save figures...', self)
        saveFigsAction.triggered.connect(self._saveFiguresAction_triggered)
        saveFigsAction.setShortcut('Ctrl+S')
        openAction.setStatusTip("Saves current figures.")
        filemenu.addAction(saveFigsAction)
        exitAction = QtGui.QAction("&Quit", self)
        exitAction.setShortcut("Ctrl+Q")
        exitAction.setStatusTip("Quit program.")
        exitAction.triggered.connect(QtGui.qApp.quit)
        filemenu.addAction(exitAction)
        removeTrialAction = QtGui.QAction("&Remove trials", self)
        removeTrialAction.setStatusTip('Permanently removes selected trials (bad trials) from trial list.')
        removeTrialAction.triggered.connect(self._remove_trials)
        removeTrialAction.setShortcut('Ctrl+R')
        toolsmenu.addAction(removeTrialAction)

        trial_group_list_box = QtGui.QGroupBox()
        trial_group_list_box.setTitle('Trial Groups')
        self.trial_group_list = TrialGroupListWidget()
        trial_group_layout = QtGui.QVBoxLayout()
        trial_group_list_box.setLayout(trial_group_layout)
        trial_group_layout.addWidget(self.trial_group_list)
        layout.addWidget(trial_group_list_box, 0, 0)
        self.trial_group_list.itemSelectionChanged.connect(self._trial_group_selection_changed)

        trial_select_list_box = QtGui.QGroupBox()
        trial_select_list_box.setMouseTracking(True)
        trial_select_list_layout = QtGui.QVBoxLayout()
        trial_select_list_box.setLayout(trial_select_list_layout)
        trial_select_list_box.setTitle('Trials')
        self.trial_select_list = TrialListWidget()
        self.trial_select_list.setMouseTracking(True)
        trial_select_list_layout.addWidget(self.trial_select_list)
        self.trial_select_list.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.trial_select_list.itemSelectionChanged.connect(self._trial_selection_changed)
        layout.addWidget(trial_select_list_box, 0, 1)
        self.trial_select_list.createGroupSig.connect(self.trial_group_list.create_group)

        filters_box = QtGui.QGroupBox()
        filters_box.setTitle("Trial filters.")
        filters_layout = QtGui.QVBoxLayout()
        filters_box.setLayout(filters_layout)
        layout.addWidget(filters_box, 0, 2)
        for v in self.filters:
            assert isinstance(v, FiltersListWidget)
            box = QtGui.QGroupBox()
            box.setTitle(v.fieldname)
            _filt_layout = QtGui.QVBoxLayout(box)
            _filt_layout.addWidget(v)
            filters_layout.addWidget(box)
            v.filterChanged.connect(self._filters_changed)

        plots_box = QtGui.QGroupBox()
        plots_box.setTitle('Plots')
        plots_layout = QtGui.QVBoxLayout()

        self.figure = Figure((9, 5))
        self.figure.patch.set_facecolor('None')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setParent(plots_box)
        self.canvas.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        plots_layout.addWidget(self.canvas)
        plots_box.setLayout(plots_layout)
        layout.addWidget(plots_box, 0, 3)
        self.ax_pid = self.figure.add_subplot(111)
        self.ax_pid.set_title('PID traces')

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
        for i in xrange(len(self.trial_mask)):
            hide = not self.trial_mask[i]
            it = self.trial_select_list.item(i)
            it.setHidden(hide)
            select = it.isSelected() * self.trial_mask[i]
            it.setSelected(select)
        self.trial_select_list.itemSelectionChanged.connect(self._trial_selection_changed)
        self.trial_select_list.itemSelectionChanged.emit()  # emit that something changed so that we redraw.

    @QtCore.pyqtSlot()
    def _openAction_triggered(self):
        filedialog = QtGui.QFileDialog(self)
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
                it = QtGui.QListWidgetItem(tstr, self.trial_select_list)
                trial = trials[i]
                odor = trial['odor']
                vialconc = trial['vialconc']
                odorconc = trial['odorconc']
                dilution = 1000 - trial['dilution'][0]
                trst = 'Odor: {0}, vialconc: {1}, odorconc: {2}, dilution: {3}'.format(odor, vialconc, odorconc,
                                                                                       dilution)
                it.setStatusTip(trst)
                trial_num_list.append(i)
            self.trial_select_list.trial_num_list = np.array(trial_num_list)
            self.trial_mask = np.ones(len(self.trial_select_list.trial_num_list), dtype=bool)
            self.build_filters()
        else:
            print('No file selected.')
        return

    def build_filters(self):
        for v in self.filters:
            assert isinstance(v, FiltersListWidget)
            v.populate_list(self.data.trials)
        return

    @QtCore.pyqtSlot()
    def _saveFiguresAction_triggered(self):
        # TODO: add figure saving functionality with filedialog.getSaveFileName.
        pass

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
        for i in xrange(len(self.trial_select_list.trial_num_list)):
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
        self.update_pid_plot(selected_trial_nums)
        self.trial_group_list.blockSignals(True)
        for i, g in zip(xrange(self.trial_group_list.count()), self.trial_group_list.trial_groups):
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
        selected_trial_nums = []
        for id in selected_idxes:
            idx = id.row()
            trialnums = self.trial_group_list.trial_groups[idx]['trial_nums']
            selected_trial_nums.extend(trialnums)
        self.trial_select_list.blockSignals(True)
        for i in selected_trial_nums:
            idx = np.where(self.trial_select_list.trial_num_list == i)[0][0]
            it = self.trial_select_list.item(idx)
            if not it.isSelected():
                it.setSelected(True)
        self.trial_select_list.blockSignals(False)
        self._trial_selection_changed()

    def update_pid_plot(self, trials):
        trial_streams = []
        self.ax_pid.clear()
        if trials:
            a = max([1./len(trials), .25])
            for tn in trials:
                color = self.trial_group_list.check_trial_color(tn)
                trial = self.data.return_trial(tn, padding=(2000, 2000))
                trial_streams.append(trial.streams['sniff'])
                self.ax_pid.plot(trial.streams['sniff'], color=color, alpha=a)
        self.canvas.draw()

    def update_trials(self):
        pass

    def _odor_constructor(self, trial_list):
        self.odors = np.unique(trial_list['odor'])

        select_list = QtGui.QListWidget()
        for odor in self.odors:
            item = QtGui.QListWidgetItem(odor, select_list)
            item.setCheckState(True)
            item.setData()
        return select_list

    def _vconc_constructor(self, trial_list):
        self.vconcs = np.unique(trial_list['vialconc'])
        select_list = QtGui.QListWidget()
        for vc in self.vconcs:
            item = QtGui.QListWidgetItem()
            select_list.addItem(str(vc))


class TrialListWidget(QtGui.QListWidget):

    createGroupSig = QtCore.pyqtSignal(list)

    def __init__(self):
        super(TrialListWidget, self).__init__()
        self.trial_num_list = np.array([])

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            super(TrialListWidget, self).mousePressEvent(event)
        elif event.button() == QtCore.Qt.RightButton:
            popMenu = QtGui.QMenu()
            createGroupAction = QtGui.QAction('Create grouping', self)
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


class TrialGroupListWidget(QtGui.QListWidget):

    def __init__(self):

        super(TrialGroupListWidget, self).__init__()
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.trial_groups = []

    @QtCore.pyqtSlot(QtGui.QMouseEvent)
    def mousePressEvent(self, event):
        button = event.button()
        if button == QtCore.Qt.LeftButton:
            super(TrialGroupListWidget, self).mousePressEvent(event)
        elif button == QtCore.Qt.RightButton:
            popMenu = QtGui.QMenu()
            delGroupAction = QtGui.QAction('Remove groups', self)
            delGroupAction.triggered.connect(self._remove_groups)
            delGroupAction.setStatusTip('Removes selected groupings.')
            popMenu.addAction(delGroupAction)
            changeColorAction = QtGui.QAction('Change color...', self)
            changeColorAction.triggered.connect(self._color_selection_triggered)
            changeColorAction.setStatusTip('Open color selection dialog to set group color.')
            popMenu.addAction(changeColorAction)
            popMenu.exec_(event.globalPos())

    def check_trial_color(self, trialnum):
        color = 'b'
        for g in self.trial_groups:
            if trialnum in g['trial_nums']:
                qc = g['color']
                assert isinstance(qc, QtGui.QColor)
                color = [qc.redF(), qc.greenF(), qc.blueF()]
        return color

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
        it = QtGui.QListWidgetItem(new_group_name)
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
        for i in remove_idxes:
            del self.trial_groups[i]
        while self.selectedIndexes():
            i = self.selectedIndexes()[0]
            ii = i.row()
            self.takeItem(ii)
        return

    def _color_selection_triggered(self):
        self.colorpicker = QtGui.QColorDialog()
        self.colorpicker.colorSelected.connect(self._change_group_color)
        self.colorpicker.show()
        return

    @QtCore.pyqtSlot(QtGui.QColor)
    def _change_group_color(self, color):

        for item in self.selectedItems():
            assert isinstance(item, QtGui.QListWidgetItem)
            item.setForeground(color)
        for i in self.selectedIndexes():
            ii = i.row()
            tg = self.trial_groups[ii]
            tg['color'] = color
        self.itemSelectionChanged.emit()

    def _remove_trials(self, removetrials):
        #TODO: connect this.
        for group in self.trial_groups:
            trials = group['trial_nums']
            assert isinstance(trials, list)
            for i in removetrials:
                if i in trials:
                    trials.remove(i)
        return


class FiltersListWidget(QtGui.QListWidget):

    filterChanged = QtCore.pyqtSignal()

    def __init__(self, fieldname):
        """
        build a QListWidget to be used with the calibrator.

        :param fieldname:
        :return:
        """
        super(FiltersListWidget, self).__init__()
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
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
            it = QtGui.QListWidgetItem(str(val), self)
            it.setSelected(True)
        self.itemSelectionChanged.connect(self._selection_changed)
        return

    @QtCore.pyqtSlot(QtGui.QMouseEvent)
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            selected = self.selectedIndexes()
            popMenu = QtGui.QMenu()
            combineAction = QtGui.QAction('Combine groups', self)
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
        for i in xrange(len(self.trial_values)):
            if i not in removeidx_list:
                val = self.trial_values[i]
                new_trial_val_list.append(val)
                m = self.trial_mask[i]
                new_trial_mask_list.append(m)
        self.trial_values = np.array(new_trial_val_list)
        self.trial_mask = np.array(new_trial_mask_list, dtype=bool)

    def sizeHint(self):
        s = QtCore.QSize()
        s.setHeight(self.sizeHintForRow(4))
        s.setWidth(super(FiltersListWidget, self).sizeHint().width())
        return s


class DilutionListWidget(FiltersListWidget):

    def populate_list(self, trials):
        self.clear()
        try:
            dil_flows = trials['dilution']
            n2 = trials['NitrogenFlow_1']
            air = trials['AirFlow_1']
            t_flow = air + n2
            trial_vals = (t_flow - dil_flows[:, 0]) / t_flow
            self.trial_values = trial_vals
            self.trial_mask = np.ones(len(trial_vals), dtype=bool)
            listvals = np.unique(trial_vals)
            self.list_values = listvals
            for val in listvals:
                it = QtGui.QListWidgetItem(str(val), self)
                it.setSelected(True)
        except:
            pass
        return


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
        for k, event_node in self.events.iteritems():
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
        for k, stream_node in self.streams.iteritems():
            if read_streams:
                streams[k] = stream_node[start_time:end_time]  # reads these values from the stream node into memory.
                #TODO: fix this to realize and correct for sample rate discrepancies.
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
    import sys
    app = QtGui.QApplication(sys.argv)
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