#!/usr/bin/python
# -*- coding: utf-8 -*-
"""misura Configuration Manager"""
import os
from misura.canon.logger import Log as logging
import sqlite3
import re
from traceback import format_exc

from PyQt4 import QtCore

from ..canon import option
from ..canon.option import ao
from ..canon.indexer import Indexer
import units

import parameters as params

default_desc = {}

ao(default_desc, 'lang', **{'name': "Client Language",
                            'current': 'sys',
                            'type': 'Chooser',
                            'options': ['sys', 'en', 'it', 'fr', 'es', 'ru']
                            })
ao(default_desc, 'refresh', **{'name': 'Remote Server Refresh Rate (ms)',
                               'current': 2000,	'max': 20000,	'min': 100, 'type': 'Integer'})

ao(default_desc, 'database', **
   {'name': 'Default Database', 'current': '', 'type': 'FilePath'})
ao(default_desc, 'autodownload', **
   {'name': 'Auto-download finished tests', 'current': True, 'type': 'Boolean'})
ao(default_desc, 'hserver', **
   {'name': 'Recent Servers', 'current': 5,	'max': 20, 'min': 0, 'type': 'Integer'})
ao(default_desc, 'saveLogin', **
   {'name': 'Save User/Password by Default', 'current': True, 'type': 'Boolean'})
ao(default_desc, 'hdatabase', **
   {'name': 'Recent Database Files', 'current': 10, 'max': 100,	'min': 1, 'type': 'Integer'})
ao(default_desc, 'hfile', **{'name': 'Recent Test Files',
                             'current': 15, 'max': 100, 'min': 1, 'type': 'Integer'})
ao(default_desc, 'hm3database', **
   {'name': 'Recent Misura3 Databases', 'current': 10, 'max': 100, 'min': 1, 'type': 'Integer'})

ao(default_desc, 'logfile', **{'name': 'Log files directory', 'current':
                               os.path.expanduser("~/.misura_log/misura.log"), 'type': 'FilePath'})
ao(default_desc, 'loglevel', **{'name': 'Logging Level', 'current': 30,
                                'max': 50, 'min': -1, 'step': 10, 'type': 'Integer', 'parent': 'logfile'})
ao(default_desc, 'logsize', **{'name': 'Size of each log file', 'current':
                               2048, 'min': 0, 'unit': 'kilobyte', 'type': 'Integer', 'parent': 'logfile'})
ao(default_desc, 'lognumber', **{'name': 'Max number of logfiles to be kept',
                                 'current': 50, 'min': 0, 'type': 'Integer', 'parent': 'logfile'})


u = [[k, v] for k, v in units.user_defaults.iteritems()]
ao(default_desc, 'units', 'Table', [
   [('Dimension', 'String'), ('Unit', 'String')]] + u, 'Measurement units')

ao(default_desc, 'rule', 'Section', 'Dataset Rules', 'Dataset Rules')

rule_exc = r'''^(/summary/)?beholder/
^(/summary/)?hydra/
/analyzer/
/autoroi/'''
ao(default_desc, 'rule_exc', 'TextArea', rule_exc, 'Ignore datasets')

rule_inc = ''
ao(default_desc, 'rule_inc', 'TextArea', rule_inc, 'Force inclusion')

rule_load = r'''hsm/sample\d/h$
hsm/sample\d/Vol$
/sample\d/d$
^(/summary/)?kiln/T$
^(/summary/)?kiln/S$
^(/summary/)?kiln/P$'''
ao(default_desc, 'rule_load', 'TextArea', rule_load, 'Force loading')

rule_unit = [
    [('Rule', 'String'), ('Unit', 'String')],
    [r'/hsm/sample\d/h$', 'percent'],
    [r'/hsm/sample\d/Vol$', 'percent']
]
ao(default_desc, 'rule_unit', 'Table', rule_unit, 'Dataset units')

rule_plot = r'''hsm/sample\d/Vol$
/sample\d/d$
^(/summary/)?kiln/T$'''
ao(default_desc, 'rule_plot', 'TextArea', rule_plot, 'Auto Plot')

rule_style = [[('Rule', 'String'), ('Range', 'String'), ('Scale', 'Float'),
               ('Color', 'String'), ('Line', 'String'), ('Marker', 'String')],
              ['/kiln/T$', '', 1, 'red', '', '']
              ]
ao(default_desc, 'rule_style', 'Table', rule_style, 'Formatting')

recent_tables = 'server,database,file,m3database'.split(',')


def tabname(name):
    if name in recent_tables:
        return 'recent_' + name
    return name


class RulesTable(object):

    """Helper object for matching a string in a list of rules."""

    def __init__(self, tab=[]):
        self.set_table(tab)

    def set_table(self, tab):
        self.rules = []
        self.rows = []
        for row in tab:
            if len(row) <= 1:
                logging.debug('skipping malformed rule', row)
                logging.debug('%s %s', 'skipping malformed rule', row)
            if isinstance(row[0], tuple):
                # Skip header row
                continue
            r = row[0]
            if len(r) == 0:
                logging.debug('%s %s', 'skipping empty rule', row)
                continue
            r = re.compile(r.replace('\n', '|'))
            self.rules.append(r)
            self.rows.append(row[1:])

    def __call__(self, s, latest=False):
        """Return the row corresponding to the first rule matching the string `s`"""
        f = False
        for i, r in enumerate(self.rules):
            if r is False:
                continue
            if r.search(s):
                f = self.rows[i]
                if not latest:
                    return f
        # No match found
        return f


class ConfDb(option.ConfigurationProxy, QtCore.QObject):
    _Method__name = 'CONF'
    conn = False
    path = ''
    index = False
    
    def __init__(self, path=False, new=False):
        QtCore.QObject.__init__(self)
        option.ConfigurationProxy.__init__(self)
        self.store = option.SqlStore()
        self.nosave_server = []
        if not path:
            return None
        # Ensure missing if new
        if os.path.exists(path) and new:
            os.remove(path)
        # Load/create
        self.known_uids = {}
        self.load(path)

    _rule_style = RulesTable()

    @property
    def rule_style(self):
        """A RulesTable for styles"""
        if not self._rule_style:
            self._rule_style = RulesTable(self['rule_style'])
        return self._rule_style

    _rule_dataset = RulesTable()

    @property
    def rule_dataset(self):
        """A special RulesTable collecting dataset loading behaviors."""
        if not self._rule_dataset:
            tab = [[('header placeholder'), ('retn')],
                   [self['rule_exc'], 1],  # exclude
                   [self['rule_inc'], 2],  # create
                   [self['rule_load'], 3],  # load
                   [self['rule_plot'], 4],  # plot
                   ]
            self._rule_dataset = RulesTable(tab)
        return self._rule_dataset

    _rule_unit = RulesTable()

    @property
    def rule_unit(self):
        if not self._rule_unit:
            self._rule_unit = RulesTable(self['rule_unit'])
        return self._rule_unit

    def reset_rules(self):
        self._rule_style = False
        self._rule_dataset = False
        self._rule_unit = False

    def load(self, path=False):
        """Load an existent client configuration database, or create a new one."""
        logging.debug('LOAD %s', path)
        self.nosave_server = []
        self.index = False
        self.close()
        if path:
            self.path = path
        self.conn = sqlite3.connect(
            self.path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.text_factory = unicode
        cursor = self.conn.cursor()

        # Chron tables
        cursor.execute(
            "create table if not exists recent_server (i integer, address text, user text, password text)")
        cursor.execute(
            "create table if not exists recent_database (i integer, path text)")
        cursor.execute(
            "create table if not exists recent_file (i integer, path text, name text)")
        cursor.execute(
            "create table if not exists recent_m3database (i integer, path text)")

        # Configuration table
        isconf = cursor.execute(
            "select 1 from sqlite_master where type='table' and name='conf'").fetchone()
        if isconf:
            desc = default_desc.copy()
            try:
                desc.update(self.store.read_table(cursor, 'conf'))
            except:
                logging.debug(format_exc())
            self.desc = desc
            logging.debug('%s %s', 'Loaded configuration', self.desc)
        else:
            logging.debug('%s', 'Recreating client configuration')
            for key, val in default_desc.iteritems():
                self.store.desc[key] = option.Option(**val)
            self.desc = self.store.desc
            self.store.write_table(cursor, "conf")

        # Load recent files in memory
        for name in recent_tables:
            name = 'recent_' + name
            cursor.execute("select * from " + name)
            r = cursor.fetchall()
            r = list(set(r))
            # Sort by key
            r = sorted(r, key=lambda e: e[0])
            # Pop key
            r = [list(e[1:]) for e in r]
            setattr(self, name, r)
        cursor.close()
        self.conn.commit()
        self.emit(QtCore.SIGNAL('load()'))
        self.reset_rules()
        self.create_index()
        
    def create_index(self):
        self.index = False
        path = self['database']
        if path and os.path.exists(path):
            logging.debug('Creating indexer at %s', path)
            self.index = Indexer(path)
            return True
        else:
            logging.debug('Default database not found: "%s"', path)
            return False

    def get_table(self, name):
        """Return table `name` as list"""
        cursor = self.conn.cursor()
        cursor.execute("select * from " + name)
        r = cursor.fetchall()
        r = list(set(r))
        # Sort by key
        r = sorted(r, key=lambda e: e[0])
        # Pop key
        r = [list(e[1:]) for e in r]
        cursor.close()
        return r

    def save(self, path=False):
        """Save to an existent client configuration database."""
        logging.debug('%s', 'SAVING')
        cursor = self.conn.cursor()
        self.store.write_table(cursor, 'conf', desc=self.desc)
        for name in recent_tables:
            tname = "recent_" + name
            tab = getattr(self, tname, [])
            nosave = getattr(self, 'nosave_' + name, [])
            if nosave is None:
                nosave = []
            logging.debug("save: %s %s %s", tname, tab, nosave)
            cursor.execute("delete from " + tname)
            if len(tab) == 0:
                continue
            # Prepare the query
            q = '?,' * len(tab[0])
            q += '?'
            cmd = "insert into " + tname + " values (" + q + ")"
            # insert table rows
            for i, row in enumerate(tab):
                if row[0] in nosave:
                    continue
                row = [i] + row
                cursor.execute(cmd, row)
        cursor.close()
        self.conn.commit()
        self.reset_rules()
        self.create_index()

    def mem(self, name, *arg):
        """Memoize a recent datum"""
        logging.debug("mem %s %s", name, arg)
        tname = tabname(name)
        tab = getattr(self, tname)
        # Avoid saving duplicate values
        arg = list(unicode(a) for a in arg)
        if arg in tab:
            tab.remove(arg)
            tab.append(arg)

            return False
        
        tab.append(arg)

        lim = self.desc['h' + name]['current']
        if len(tab) > lim:
            tab.pop(0)
        setattr(self, tname, tab)
        self.emit(QtCore.SIGNAL('mem()'))
        self.save()
        return True

    def rem(self, name, key):
        """Forget a recent datum"""
        key = str(key)
        tname = tabname(name)
        tab = getattr(self, tname)
        v = [r[0] for r in tab]
        if key not in v:
            return False
        i = v.index(key)
        tab.pop(i)
        setattr(self, tname, tab)
        self.emit(QtCore.SIGNAL('rem()'))
        self.save()
        return True

    def close(self):
        if self.conn:
            self.conn.close()

    def mem_file(self, path, name=''):
        self.mem('file', path, name)

    def rem_file(self, path):
        self.rem('file', path)

    def mem_database(self, path):
        self.mem('database', path)

    def rem_database(self, path):
        self.rem('database', path)

    def mem_m3database(self, path):
        self.mem('m3database', path)

    def rem_m3database(self, path):
        self.rem('m3database', path)

    def found_server(self, addr):
        addr = str(addr)
        v = [r[0] for r in self.recent_server]
        # Check if the found server was already saved with its own user and
        # password
        if addr in v:
            return
        # Otherwise, save it with empty user and password
        self.mem('server', addr, '', '')

    def logout(self, addr):
        addr = str(addr)
        v = [r[0] for r in self.recent_server]
        if addr not in v:
            return False

        i = v.index(addr)
        self.recent_server.pop(i)
        self.recent_server.append((addr, '', ''))
        return True

    # TODO: accettare serial e name e altro...
    def mem_server(self, addr, user='', password='', save=True):
        # Remove entries with empty user/password
        addr, user, password = str(addr), str(user), str(password)
        if user != '':
            v = [r[0] for r in self.recent_server]
            if addr in v:
                i = v.index(addr)
                self.recent_server.pop(i)
        if not save:
            self.nosave_server.append(addr)
        return self.mem('server', addr, user, password)

    def rem_server(self, addr):
        self.rem('server', addr)

    def getUserPassword(self, addr):
        """Returns username and passwords used to login"""
        for entry in self.recent_server:
            if entry[0] == addr:
                return entry[1], entry[2]
        return '', ''
    
    def resolve_uid(self, uid):
        """Search file path corresponding to uid across default database and recent databases"""
        if not uid:
            logging.debug('no uid')
            return False
        known = self.known_uids.get(uid, False)
        if known:
            logging.debug( 'UID was known %s',known)
            return known, False
        else:
            logging.debug('Uid not previously known %s',uid)
        if self.index:
            dbPath = self.index.dbPath
            file_path = self.index.searchUID(uid)
            if file_path:
                logging.debug('uid found in default db %s %s', uid, file_path)
                return file_path
        else:
            dbPath = False
        file_path = False
        for path in self.recent_database:
            path = path[0]
            if path == dbPath:
                continue
            if not os.path.exists(path):
                logging.debug('Skip db: %s', path)
                continue
            try: 
                db = Indexer(path)
            except:
                logging.info('Db open error: \n%s',format_exc())
                continue
            file_path = db.searchUID(uid)
            if file_path: 
                dbPath = path
                break
            logging.debug('UID not found: %s %s', uid, path)
        if not file_path:
            return False
        self.known_uids[self.uid] = file_path
        return file_path, dbPath

settings = QtCore.QSettings(
    QtCore.QSettings.NativeFormat, QtCore.QSettings.UserScope, 'Expert System Solutions', 'Misura 4')
# Set the configuration db
cf = str(settings.value('/Configuration'))
if cf == '' or not os.path.exists(cf):
    confdb = ConfDb(params.pathConf)
elif os.path.exists(cf):
    params.pathConf = cf
    confdb = ConfDb(path=cf)
settings.setValue('/Configuration', confdb.path)
