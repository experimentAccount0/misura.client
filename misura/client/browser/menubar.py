#!/usr/bin/python
# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from .. import _
from ..clientconf import confdb
from ..confwidget import RecentMenu


class BrowserMenuBar(QtGui.QMenuBar):
    """Browser menus"""

    def __init__(self, server=False, parent=None):
        QtGui.QMenuBar.__init__(self, parent)

        self.lstActions = []
        self.func = []
        self.file = self.addMenu(_('File'))

        self.recentFile = RecentMenu(confdb, 'file', self)
        self.actFile = self.file.addAction(_('Open File'), self.recentFile.new)
        act = self.addMenu(self.recentFile)

        self.recentDatabase = RecentMenu(confdb, 'database', self)
        self.actDb = self.file.addAction(
            _('Open Database'), self.recentDatabase.new)
        self.addMenu(self.recentDatabase)

        self.actNewDb = self.file.addAction(
            _('New Database'), self.new_database)

        
        self.recentM3db = RecentMenu(confdb, 'm3database', self)
#       self.connect(self.recentM3db,QtCore.SIGNAL('new(QString)'),self.open_database)
        self.file.addMenu(self.recentM3db)

        self.currents = self.addMenu(_('View Tests'))
        self.databases = self.addMenu(_('View Databases'))

    def new_database(self, path=False):
        if not path:
            path = QtGui.QFileDialog.getSaveFileName(
                self, "Choose a name for the new database", "C:\\")
        if not path:
            return
        self.emit(QtCore.SIGNAL('new_database(QString)'), path)

    def eval_standard(self):
        self.emit(QtCore.SIGNAL('re_standard()'))