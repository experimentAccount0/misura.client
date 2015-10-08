#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Designer per il ciclo termico."""
from misura.canon.logger import Log as logging
from .. import _
from misura.canon.csutil import next_point
from PyQt4 import QtGui, QtCore
import row
import flags
import collections

def clean_curve(dat, events=True):
    crv = []
    for index_row, ent in enumerate(dat):
        t, T = ent[:2]
        if None in ent:
            logging.debug('%s %s', 'Skipping row', index_row)
            continue
        if isinstance(T, basestring):
            if events:
                T = str(T)
            else:
                logging.debug('%s %s', 'Skipping EVENT', index_row)
                continue

        crv.append([t * 60, T])
    return crv


class ThermalCurveModel(QtCore.QAbstractTableModel):

    """Data model for thermal cycle editing"""
    sigModeChanged = QtCore.pyqtSignal()

    def __init__(self, crv=None, is_live=False):
        QtCore.QAbstractTableModel.__init__(self)
        self.dat = []
        self.rows_models = []
        header = []
        for s in ['Time', 'Temperature', 'Heating Rate', 'Duration']:
            header.append(_(s))
        self.header = header
        self.is_live = is_live

    def rowCount(self, index=QtCore.QModelIndex()):
        return len(self.dat)

    def columnCount(self, index=QtCore.QModelIndex()):
        return len(self.header)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return 0
        row_entry = self.dat[index.row()]
        col = index.column()

        if role == QtCore.Qt.DisplayRole:
            r = row_entry[index.column()]
            if col == row.colTEMP:
                if isinstance(r, basestring):
                    r = r.replace('>', 'Event: ')
            return r

        if role == QtCore.Qt.ForegroundRole:
            modes_dict = collections.defaultdict(bool)
            modes_dict[row.colTIME] = 'points'
            modes_dict[row.colRATE] = 'ramp'
            modes_dict[row.colDUR] = 'dwell'

            current_row_mode = self.rows_models[index.row()]
            current_column_mode = modes_dict[col]
            has_to_be_highligthed = index.row(
            ) > 0 and current_row_mode == current_column_mode

            if has_to_be_highligthed:
                return QtGui.QBrush(QtCore.Qt.darkRed)

            return None

    def flags(self, index):
        return flags.execute(self, index, is_live=self.is_live)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        index_row = index.row()
        index_column = index.column()
        if not index.isValid() or index_row < 0 or index_row > self.rowCount() or index_column < 0 or index_column > self.columnCount():
            logging.debug(
                '%s %s %s', 'setData: invalid line', index_row, index_column)
            return False
        if isinstance(value, basestring) and (not value.startswith('>')):
            value = float(value)
        row_entry = self.dat[index_row]
        logging.debug(
            '%s %s %s %s %s', 'setData:', index_row, index_column, value, row_entry[index_column])
        row_entry[index_column] = value
        self.dat[index_row] = row_entry
        for ir in range(index_row, self.rowCount()):
            self.updateRow(ir)
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex,QModelIndex)"), self.index(index_row, 0),
                  self.index(self.rowCount(), self.columnCount()))
        # Emetto la durata totale del ciclo termico
        self.emit(QtCore.SIGNAL("duration(float)"),
                  self.dat[-1][row.colTIME])
        return True

    def insertRows(self, position, rows_number=1, index=QtCore.QModelIndex(), values=False):
        logging.debug(
            '%s %s %s %s', 'insertRows', position, rows_number, index.row())
        self.beginInsertRows(
            QtCore.QModelIndex(), position, position + rows_number - 1)
        if not values:
            values = [0] * self.columnCount()
        for current_row_index in range(rows_number):
            self.dat.insert(position + current_row_index, values)
            self.rows_models.insert(position + current_row_index, 'ramp')

        self.endInsertRows()

        return True

    def removeRows(self, position, rows=1, index=QtCore.QModelIndex()):
        self.beginRemoveRows(
            QtCore.QModelIndex(), position, position + rows - 1)
        self.dat = self.dat[:position] + self.dat[position + rows:]
        self.endRemoveRows()
        return True

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return
        if role == QtCore.Qt.DisplayRole:
            return self.header[section]
        elif role == QtCore.Qt.BackgroundRole:
            return QtGui.QBrush(QtGui.QColor(10, 200, 10))

    def mode_to(self, modename, row):
        self.rows_models[row] = modename
        self.emit(QtCore.SIGNAL(
            "headerDataChanged(Qt::Orientation,int,int)"), QtCore.Qt.Horizontal, 0, self.columnCount() - 1)
        self.sigModeChanged.emit()

    def mode_points(self, row):
        self.mode_to('points', row)

    def mode_ramp(self, row):
        self.mode_to('ramp', row)

    def mode_dwell(self, row):
        self.mode_to('dwell', row)

    def setCurve(self, crv, progressBar=False):
        self.removeRows(0, self.rowCount())
        self.insertRows(0, len(crv))
        for i, row in enumerate(crv):
            t, T = row
            # Detect TCEv
            if isinstance(T, basestring):
                self.dat[i] = [t / 60., T, 0, 0]
                continue
            D = 0
            R = 0
            if i > 0:
                idx, ent = next_point(crv, i - 1, -1)
                if ent is False:
                    ent = row
                t0, T0 = ent
                D = (t - t0) / 60.
                if T == T0 or D == 0:
                    R = 0
                else:
                    R = (T - T0) / D
            self.dat[i] = [t / 60., T, R, D]
            if progressBar:
                progressBar.setValue(i)
                # QtGui.QApplication.processEvents()
        # Segnalo che l'intera tabella è cambiata:
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex,QModelIndex)"), self.index(0, 0),
                  self.index(self.rowCount(), self.columnCount()))

    def updateRow(self, row_index):
        self.dat[row_index] = row.ThermalCycleRow().update_row(
            self.dat, row_index, self.rows_models[row_index])

    def curve(self, events=True):
        """Format table for plotting or transmission"""
        return clean_curve(self.dat, events)
    
    