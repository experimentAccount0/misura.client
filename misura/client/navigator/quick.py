#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Tree visualization of opened misura Files in a document."""
from misura.canon.logger import Log as logging
from veusz.dialogs.plugin import PluginDialog

from veusz import document
from PyQt4.QtCore import Qt
from PyQt4 import QtGui, QtCore

import functools
from .. import _
from ..filedata import MisuraDocument
from ..filedata import OperationMisuraImport
from ..filedata import DatasetEntry
from ..filedata import getFileProxy
from ..filedata import axis_selection
import numpy as np

ism = isinstance


def docname(ds):
    """Get dataset name by searching in parent document data"""
    for name, obj in ds.document.data.iteritems():
        if obj == ds:
            return name
    return None


def node(func):
    """Decorator for functions which should get currentIndex node if no arg is passed"""
    @functools.wraps(func)
    def node_wrapper(self, *a, **k):
        n = False
        keyword = True
        # Get node from named parameter
        if k.has_key('node'):
            n = k['node']
        # Or from the first unnamed argument
        elif len(a) >= 1:
            n = a[0]
            keyword = False
        # If node was not specified, get from currentIndex
        if n is False:
            n = self.model().data(self.currentIndex(), role=Qt.UserRole)
        elif isinstance(n, document.Dataset):
            n = docname(n)

        # If node was expressed as/converted to string, get its corresponding
        # tree entry
        if isinstance(n, str) or isinstance(n, unicode):
            logging.debug('%s %s', 'traversing node', n)
            n = str(n)
            n = self.model().tree.traverse(n)

        if keyword:
            k['node'] = n
        else:
            a = list(a)
            a[0] = n
            a = tuple(a)
        logging.debug(
            '%s %s %s %s', '@node with', n, type(n), isinstance(n, unicode))
        return func(self, *a, **k)
    return node_wrapper


def nodes(func):
    """Decorator for functions which should get a list of currentIndex nodes if no arg is passed"""
    @functools.wraps(func)
    def node_wrapper(self, *a, **k):
        n = []
        keyword = True
        # Get node from named parameter
        if k.has_key('nodes'):
            n = k['nodes']
        # Or from the first unnamed argument
        elif len(a) >= 1:
            n = a[0]
            keyword = False
        # If node was not specified, get from currentIndex
        if not len(n):
            n = []
            for idx in self.selectedIndexes():
                n0 = self.model().data(idx, role=Qt.UserRole)
                n.append(n0)
        if keyword:
            k['nodes'] = n
        else:
            a = list(a)
            a[0] = n
            a = tuple(a)
        logging.debug(
            '%s %s %s %s %s', '@nodes with', n, type(n), isinstance(n, unicode))
        return func(self, *a, **k)
    return node_wrapper

class NavigatorDomain(object):
    def __init__(self, navigator):
        self.navigator = navigator
        
    @property
    def model(self):
        """Hack to allow nodes() decorator"""
        return self.navigator.model
    
    @property
    def currentIndex(self):
        return self.navigator.currentIndex
    
    @property
    def mainwindow(self):
        return self.navigator.mainwindow
    
    @property
    def doc(self):
        return self.navigator.doc
    
    def xnames(self,*a,**k):
        return self.navigator.xnames(*a,**k)
    
    def dsnode(self, *a, **k):
        return self.navigator.dsnode(*a, **k)
    
    def plot(self, *a, **k):
        return self.navigator.plot(*a, **k)
    
    def is_loaded(self, node):
        return (node.ds is not False) and (len(node.ds) > 0)
    
    def is_plotted(self, node):
        if not self.is_loaded(node):
            return False
        return self.model().is_plotted(node.path)
        
    def check_node(self, node):
        """Check if node pertain to this domain"""
        return True
    
    def add_file_menu(self, menu, node):
        return True
    
    def build_file_menu(self, menu, node):
        if not self.check_node(node):
            return False
        return self.add_file_menu(menu, node)  
    
    def add_sample_menu(self, menu, node):
        return True
    
    def build_sample_menu(self, menu, node):
        if not self.check_node(node):
            return False
        return self.add_sample_menu(menu, node)  
    
    def add_group_menu(self, menu, node):
        return True
    
    def build_group_menu(self, menu, node):
        if not self.check_node(node):
            return False
        return self.add_group_menu(menu, node)  
    
    def add_dataset_menu(self, menu, node):
        return True
    
    def build_dataset_menu(self, menu, node):
        if not self.check_node(node):
            return False
        return self.add_dataset_menu(menu, node)  
    
    def add_derived_dataset_menu(self, menu, node):
        return True
    
    def build_derived_dataset_menu(self, menu, node):
        if not self.check_node(node):
            return False
        return self.add_derived_dataset_menu(menu, node)  
    
class DataNavigatorDomain(NavigatorDomain):
    @node
    def change_rule(self, node=False, act=0):
        """Change current rule"""
        # TODO: change_rule
        pass

    def add_load(self, menu, node):
        """Add load/unload action"""
        self.act_load = menu.addAction(_('Load'), self.navigator.load)
        self.act_load.setCheckable(True)
        is_loaded = True
        if node.linked is None:
            self.act_load.setVisible(False)
        else:
            is_loaded = (node.ds is not False) and (len(node.ds) > 0)
            self.act_load.setChecked(is_loaded)
        return is_loaded
    
    @node
    def keep(self, node=False):
        """Inverts the 'keep' flag on the current dataset,
        causing it to be saved (or not) on the next file commit."""
        ds, node = self.dsnode(node)
        cur = getattr(ds, 'm_keep', False)
        ds.m_keep = not cur
    
    def add_keep(self, menu, node):
        temporary_disabled = True
        return temporary_disabled
        """Add on-file persistence action"""
        self.act_keep = menu.addAction(
            _('Saved on test file'), self.keep)
        self.act_keep.setCheckable(True)
        self.act_keep.setChecked(node.m_keep)
        
    @node
    def save_on_current_version(self, node=False):
        proxy = getFileProxy(node.linked.filename)
        prefix = node.linked.prefix
        try:
            proxy.save_data(node.ds.m_col, node.ds.data, self.model().doc.data[prefix + "t"].data)
        except Exception as e:
            message = "Impossible to save data.\n\n" + str(e)
            QtGui.QMessageBox.warning(None,'Error', message)
        proxy.close()
    
    def add_rules(self, menu, node):
        """Add loading rules sub menu"""
        menu = menu.addMenu(_('Rules'))
        self.act_rule = []
        self.func_rule = []

        def gen(name, idx):
            f = functools.partial(self.change_rule, act=1)
            act = menu.addAction(_(name), f)
            act.setCheckable(True)
            self.act_rule.append(act)
            self.func_rule.append(f)

        gen('Ignore', 1)
        gen('Force', 2)
        gen('Load', 3)
        gen('Plot', 4)

        # Find the highest matching rule
        r = confdb.rule_dataset(node.path, latest=True)
        if r:
            r = r[0]
        if r > 0:
            self.act_rule[r - 1].setChecked(True)
        
    def add_file_menu(self, menu, node):
        return True
        
    def add_sample_menu(self, menu, node):
        menu.addAction(_('Delete'), self.navigator.deleteChildren)
        return True
             
    def add_dataset_menu(self, menu, node):
        self.add_load(menu, node)
        self.add_keep(menu, node)
        menu.addAction(('Save on current version'), self.save_on_current_version)
        self.add_rules(menu, node)
        menu.addAction(_('Delete'), self.navigator.deleteData)
        return True
    
    def add_derived_dataset_menu(self, menu, node):
        self.add_keep(menu, node)
        menu.addAction(_('Delete'), self.navigator.deleteData)
        # menu.addAction(_('Overwrite parent'), self.navigator.overwrite)
        
from ..clientconf import confdb
class PlottingNavigatorDomain(NavigatorDomain):
    def check_node(self, node):
        if not node.ds:
            return False
        is_loaded = len(node.ds) > 0
        return is_loaded
    
    @node
    def intercept(self, node=False):
        """Intercept all curves derived/pertaining to the current object"""
        if ism(node, DatasetEntry):
            dslist = [node.path]
        elif hasattr(node, 'datasets'):
            # FIXME: needs paths
            dslist = node.children.keys()
        else:
            dslist = []
        from misura.client import plugin
        xnames = self.xnames(node, page='/time')
        xnames.append('')
        p = plugin.InterceptPlugin(target=dslist, axis='X', critical_x=xnames[0])
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.InterceptPlugin)
        self.mainwindow.showDialog(d)   
        
    def add_plotted(self, menu, node, is_plotted=False):
        """Add plot/unplot action"""
        self.act_plot = menu.addAction(_('Plot'), self.plot)
        self.act_plot.setCheckable(True)
        self.act_plot.setChecked(is_plotted)
    
    @node
    def colorize(self, node=False):
        """Set/unset color markers."""
        plotpath = self.model().is_plotted(node.path)
        if not len(plotpath) > 0:
            return False
        x = self.xnames(node)[0]
        from misura.client import plugin
        p = plugin.ColorizePlugin(curve=plotpath[0], x=x)
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ColorizePlugin)
        self.mainwindow.showDialog(d)
        

    @node
    def save_style(self, node=False):
        """Save current curve color, style, marker and axis ranges and scale."""
        # TODO: save_style
        pass

    @node
    def delete_style(self, node=False):
        """Delete style rule."""
        # TODO: delete_style
        pass
    
    style_menu = False
    def add_styles(self, menu, node):
        """Styles sub menu"""
        plotpath = self.model().is_plotted(node.path)
        if not len(plotpath) > 0:
            return
        if not self.style_menu:
            self.style_menu = menu.addMenu(_('Style'))
        self.style_menu.clear()
        
        wg = self.doc.resolveFullWidgetPath(plotpath[0])
        self.act_color = self.style_menu.addAction(
            _('Colorize'), self.colorize)
        self.act_color.setCheckable(True)

        self.act_save_style = self.style_menu.addAction(
            _('Save style'), self.save_style)
        self.act_save_style.setCheckable(True)
        self.act_delete_style = self.style_menu.addAction(
            _('Delete style'), self.delete_style)
        if len(wg.settings.Color.points):
            self.act_color.setChecked(True)
        if confdb.rule_style(node.path):
            self.act_save_style.setChecked(True)
        
    def add_file_menu(self, menu, node):
        menu.addAction(_('Intercept all curves'), self.intercept)
        return True
        
    def add_sample_menu(self, menu, node):
        menu.addAction(_('Intercept all curves'), self.intercept)
        menu.addAction(_('Delete'), self.navigator.deleteChildren)
        return True
             
    def add_dataset_menu(self, menu, node):
        is_plotted = self.navigator.is_plotted(node)
        self.add_plotted(menu, node, is_plotted)
        if is_plotted:
            menu.addAction(_('Intercept this curve'), self.intercept)
            self.add_styles(menu, node)
        return True
        
    add_derived_dataset_menu = add_dataset_menu
    
    
class MathNavigatorDomain(NavigatorDomain):
    def check_node(self, node):
        if not node.ds:
            return False
        istime = node.path == 't' or node.path.endswith(':t')
        is_loaded = len(node.ds) > 0
        return (not istime) and is_loaded
    
    @node
    def edit_dataset(self, node=False):
        """Slot for opening the dataset edit window on the currently selected entry"""
        ds, y = self.dsnode(node)
        name = node.path
        logging.debug('%s %s', 'name', name)
        dialog = self.mainwindow.slotDataEdit(name)
        if ds is not y:
            dialog.slotDatasetEdit()

    @node
    def smooth(self, node=False):
        """Call the SmoothDatasetPlugin on the current node"""
        ds, node = self.dsnode(node)
        w = max(5, len(ds.data) / 50)
        from misura.client import plugin
        p = plugin.SmoothDatasetPlugin(
            ds_in=node.path, ds_out=node.m_name + '/sm', window=int(w))
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.SmoothDatasetPlugin)
        self.mainwindow.showDialog(d)

    @node
    def coefficient(self, node=False):
        """Call the CoefficientPlugin on the current node"""
        ds, node = self.dsnode(node)
        w = max(5, len(ds.data) / 50)
        ds_x = self.xnames(node, '/temperature')[0]
        ini = getattr(ds, 'm_initialDimension', 0)
        if getattr(ds, 'm_percent', False):
            ini = 0. # No conversion if already percent
        from misura.client import plugin
        p = plugin.CoefficientPlugin(
            ds_y=node.path, ds_x=ds_x, ds_out=node.m_name + '/cf', smooth=w, percent=ini)
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.CoefficientPlugin)
        self.mainwindow.showDialog(d)

    @node
    def derive(self, node=False):
        """Call the DeriveDatasetPlugin on the current node"""
        ds, node = self.dsnode(node)
        w = max(5, len(ds.data) / 50)

        ds_x = self.xnames(node, "/time")[0]  # in current page

        from misura.client import plugin
        p = plugin.DeriveDatasetPlugin(
            ds_y=node.path, ds_x=ds_x, ds_out=node.m_name + '/d', smooth=w)
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.DeriveDatasetPlugin)
        self.mainwindow.showDialog(d)
        
        
    def add_dataset_menu(self, menu, node):
        menu.addAction(_('Edit'), self.edit_dataset)
        menu.addAction(_('Smoothing'), self.smooth)
        menu.addAction(_('Derivatives'), self.derive)
        menu.addAction(_('Linear Coefficient'), self.coefficient)
        
        
class MeasurementUnitsNavigatorDomain(NavigatorDomain):
    def check_node(self, node):
        if not node.ds:
            return False
        return len(node.ds) > 0

    @node
    def setInitialDimension(self, node=False):
        """Invoke the initial dimension plugin on the current entry"""
        logging.debug('%s %s %s', 'Searching dataset name', node, node.path)
        n = self.doc.datasetName(node.ds)
        ini = getattr(node.ds, 'm_initialDimension', False)
        if not ini:
            ini = 100.
        xname = self.xnames(node)[0]
        logging.debug('%s %s %s', 'Invoking InitialDimensionPlugin', n, ini)
        from misura.client import plugin
        p = plugin.InitialDimensionPlugin(ds=n, ini=ini, ds_x = xname)
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.InitialDimensionPlugin)
        self.mainwindow.showDialog(d)

    @node
    def convertPercentile(self, node=False):
        """Invoke the percentile plugin on the current entry"""
        n = self.doc.datasetName(node.ds)
        from misura.client import plugin
        p = plugin.PercentilePlugin(ds=n, propagate=True)
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.PercentilePlugin)
        self.mainwindow.showDialog(d)

    @node
    def set_unit(self, node=False, convert=False):
        logging.debug('%s %s %s %s', 'set_unit:', node, node.unit, convert)
        if node.unit == convert or not convert or not node.unit:
            logging.debug('%s', 'set_unit: Nothing to do')
            return
        n = self.doc.datasetName(node.ds)
        from misura.client import plugin
        p = plugin.UnitsConverterTool(ds=n, convert=convert, propagate=True)
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.UnitsConverterTool)
        self.mainwindow.showDialog(d)
    
    def add_percentile(self, menu, node):
        """Add percentile conversion action"""
        self.act_percent = menu.addAction(
            _('Set Initial Dimension'), self.setInitialDimension)
        self.act_percent = menu.addAction(
            _('Percentile'), self.convertPercentile)
        self.act_percent.setCheckable(True)
        self.act_percent.setChecked(node.m_percent)
        
    def add_unit(self, menu, node):
        """Add measurement unit conversion menu"""
        self.units = {}
        u = node.unit
        if not u:
            return
        un = menu.addMenu(_('Units'))
        kgroup, f, p = units.get_unit_info(u, units.from_base)
        same = units.from_base.get(kgroup, {u: lambda v: v}).keys()
        logging.debug('%s %s', kgroup, same)
        for u1 in same:
            p = functools.partial(self.set_unit, convert=u1)
            act = un.addAction(_(u1), p)
            act.setCheckable(True)
            if u1 == u:
                act.setChecked(True)
            # Keep reference
            self.units[u1] = (act, p)
        
    def add_dataset_menu(self, menu, node):
        self.add_percentile(menu, node)
        self.add_unit(menu, node)

      
class MicroscopeSampleNavigatorDomain(NavigatorDomain):
    def check_node(self, node):
        return 'hsm/sample' in node.path
    
    @node
    def showPoints(self, node=False):
        """Show characteristic points"""
        from misura.client import plugin
        p = plugin.ShapesPlugin(sample=node)
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ShapesPlugin)
        self.mainwindow.showDialog(d)

    @node
    def hsm_report(self, node=False):
        """Execute HsmReportPlugin on `node`"""
        from misura.client import plugin
        p = plugin.ReportPlugin(node, 'report_hsm.vsz', 'Vol')
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ReportPlugin)
        self.mainwindow.showDialog(d)   
        
    @node
    def render(self, node=False):
        """Render video from `node`"""
        from misura.client import video
        sh = getFileProxy(node.linked.filename)
        pt = '/' + \
            node.path.replace(node.linked.prefix, '').replace('summary', '')
        v = video.VideoExporter(sh, pt)
        v.exec_()
        sh.close()

    @nodes
    def surface_tension(self, nodes):
        """Call the SurfaceTensionPlugin.
        - 1 node selected: interpret as a sample and directly use its beta,r0,Vol,T datasets
        - 2 nodes selected: interpret as 2 samples and search the node having beta,r0 children; use dil/T from the other
        - 4 nodes selected: interpret as separate beta, r0, Vol, T datasets and try to assign based on their name
        - 5 nodes selected: interpret as separate (beta, r0, T) + (dil, T) datasets and try to assign based on their name and path
        """
        if len(nodes) > 1:
            logging.debug('%s', 'Not implemented')
            return False
        smp = nodes[0].children
        dbeta, nbeta = self.dsnode(smp['beta'])
        beta = nbeta.path
        dR0, nR0 = self.dsnode(smp['r0'])
        R0 = nR0.path
        ddil, ndil = self.dsnode(smp['Vol'])
        dil = ndil.path
        T = nbeta.linked.prefix + 'kiln/T'
        out = nbeta.linked.prefix + 'gamma'
        if not self.doc.data.has_key(T):
            T = ''
        # Load empty datasets
        if len(dbeta) == 0:
            self._load(nbeta)
        if len(dR0) == 0:
            self._load(nR0)
        if len(ddil) == 0:
            self._load(ndil)
        from misura.client import plugin
        cls = plugin.SurfaceTensionPlugin
        p = cls(beta=beta, R0=R0, T=T,
                dil=dil, dilT=T, ds_out=out, temperature_dataset=self.doc.data[T].data)
        d = PluginDialog(self.mainwindow, self.doc, p, cls)
        self.mainwindow.showDialog(d)
            
    def add_sample_menu(self, menu, node):
        j = 0
        k = ['beta', 'r0', 'Vol']
        for kj in k:
            j += node.children.has_key(kj)
        if j == len(k):
            menu.addAction(_('Surface tension'), self.surface_tension)
        menu.addAction(_('Show Characteristic Points'), self.showPoints)
        menu.addAction(_('Report'), self.hsm_report)
        menu.addAction(_('Render video'), self.render)
        return True
    
    def add_dataset_menu(self, menu, node):
        if self.is_plotted(node):
            menu.addAction(_('Show Characteristic Points'), self.showPoints)
        return True
    
class DilatometerNavigatorDomain(NavigatorDomain):
    @node
    def calibration(self, node=False):
        """Call the CalibrationFactorPlugin on the current node"""
        ds, node = self.dsnode(node)

        T = self.xnames(node, "/temperature")[0]  # in current page

        from misura.client import plugin
        p = plugin.CalibrationFactorPlugin(d=node.path, T=T)
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.CalibrationFactorPlugin)
        self.mainwindow.showDialog(d)    
        
    def add_dataset_menu(self, menu, node):
        if not axis_selection.is_calibratable(node.path):
            return False
        menu.addAction(_('Calibration'), self.calibration)
        return True
    
class HorizontalSampleNavigatorDomain(DilatometerNavigatorDomain):
    
    def check_node(self, node):
        return 'horizontal/sample' in node.path
    
    @node
    def report(self, node=False):
        """Execute HorzizontalReportPlugin on `node`"""
        from misura.client import plugin
        p = plugin.ReportPlugin(node, 'report_horizontal.vsz', 'd')
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ReportPlugin)
        self.mainwindow.showDialog(d)
    
    def add_sample_menu(self, menu, node): 
        menu.addAction(_('Report'), self.report)
        return True
 
class VerticalSampleNavigatorDomain(DilatometerNavigatorDomain):
    
    def check_node(self, node):
        return 'vertical/sample' in node.path
    
    @node
    def report(self, node=False):
        """Execute VerticalReportPlugin on `node`"""
        from misura.client import plugin
        p = plugin.ReportPlugin(node, 'report_vertical.vsz', 'd')
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ReportPlugin)
        self.mainwindow.showDialog(d)
    
    def add_sample_menu(self, menu, node): 
        menu.addAction(_('Report'), self.report)
        return True
        
class FlexSampleNavigatorDomain(NavigatorDomain):
    def check_node(self, node):
        return 'flex/sample' in node.path
    @node
    def report(self, node=False):
        """Execute FlexReportPlugin on `node`"""
        from misura.client import plugin
        p = plugin.ReportPlugin(node, 'report_flex.vsz', 'd')
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.ReportPlugin)
        self.mainwindow.showDialog(d)
    
    def add_sample_menu(self, menu, node): 
        menu.addAction(_('Report'), self.report)
        return True
    

domains = [PlottingNavigatorDomain, MathNavigatorDomain, 
           MicroscopeSampleNavigatorDomain, 
           HorizontalSampleNavigatorDomain, VerticalSampleNavigatorDomain, 
           FlexSampleNavigatorDomain,
           DataNavigatorDomain,]

class QuickOps(object):

    """Quick interface for operations on datasets"""
    _mainwindow = False

    @property
    def mainwindow(self):
        if self._mainwindow is False:
            return self
        return self._mainwindow

    ###
    # File actions
    ###
    @node
    def viewFile(self, node=False):
        if not node.linked:
            return False
        doc = MisuraDocument(node.linked.filename)
        from misura.client import browser
        browser.TestWindow(doc).show()

    @node
    def closeFile(self, node=False):
        # FIXME: model no longer have a "tests" structure.
        lk = node.linked
        if not lk:
            logging.debug('%s %s', 'Node does not have linked file', node.path)
            return False
        for ds in self.doc.data.values():
            if ds.linked == lk:
                self.deleteData(ds)

        self.model().refresh(True)

    @node
    def reloadFile(self, node=False):
        logging.debug('%s', 'RELOADING')
        if not node.linked:
            return False
        logging.debug('%s', node.linked.reloadLinks(self.doc))


    def load_version(self, LF, version):
        # FIXME: VERSIONING!
        logging.debug('%s', 'LOAD VERSION')
        LF.params.version = version
        LF.reloadLinks(self.doc)

        fl = self.model().files
        logging.debug('%s %s', 'got linked files', self.model().files[:])

    @node
    def commit(self, node=False):
        """Write datasets to linked file. """
        name, st = QtGui.QInputDialog.getText(
            self, "Version Name", "Choose a name for the data version you are saving:")
        if not st:
            logging.debug('%s', 'Aborted')
            return
        logging.debug('%s %s', 'Committing data to', node.filename)
        node.commit(unicode(name))


    ###
    # Sample actions
    ###
    @node
    def deleteChildren(self, node=False):
        """Delete all children of node."""
        logging.debug('%s %s %s', 'deleteChildren', node, node.children)
        for sub in node.children.values():
            if not sub.ds:
                continue
            self.deleteData(sub)
#
    ###
    # Dataset actions
    ###
    def _load(self, node):
        """Load or reload a dataset"""
        op = OperationMisuraImport.from_dataset_in_file(
            node.path, node.linked.filename)
        self.doc.applyOperation(op)

    @node
    def load(self, node=False):
        logging.debug('%s %s', 'load', node)
        if node.linked is None:
            logging.debug('%s %s', 'Cannot load: no linked file!', node)
            return
        if not node.linked.filename:
            logging.debug('%s %s', 'Cannot load: no filename!', node)
            return
        if len(node.data) > 0:
            logging.debug('%s %s', 'Unloading', node.path)
            # node.ds.data = []
            ds = node.ds
            self.deleteData(node=node)
            # self.deleteData(node=node, remove_dataset=False, recursive=False)
            ds.data = np.array([])
            self.doc.available_data[node.path] = ds
            self.model().pause(False)
            self.doc.setModified()

            return
        self._load(node)
        
    @node
    def plot(self, node=False):
        """Slot for plotting by temperature and time the currently selected entry"""
        pt = self.model().is_plotted(node.path)
        if pt:
            logging.debug('%s %s', 'UNPLOTTING', node)
            self.deleteData(node=node, remove_dataset=False, recursive=False)
            return
        # Load if no data
        if len(node.data) == 0:
            self.load(node)
        yname = node.path

        from misura.client import plugin
        # If standard page, plot both T,t
        page = self.model().page
        if page.startswith('/temperature/') or page.startswith('/time/'):
            logging.debug('%s %s', 'Quick.plot', page)
            # Get X temperature names
            xnames = self.xnames(node, page='/temperature')
            assert len(xnames) > 0
            p = plugin.PlotDatasetPlugin()
            p.apply(self.cmd, {
                    'x': xnames, 'y': [yname] * len(xnames), 'currentwidget': '/temperature/temp'})

            # Get time datasets
            xnames = self.xnames(node, page='/time')
            assert len(xnames) > 0
            p = plugin.PlotDatasetPlugin()
            p.apply(self.cmd, {
                    'x': xnames, 'y': [yname] * len(xnames), 'currentwidget': '/time/time'})
        else:
            if page.startswith('/report'):
                page = page + '/temp'
            logging.debug('%s %s', 'Quick.plot on currentwidget', page)
            xnames = self.xnames(node, page=page)
            assert len(xnames) > 0
            p = plugin.PlotDatasetPlugin()
            p.apply(
                self.cmd, {'x': xnames, 'y': [yname] * len(xnames), 'currentwidget': page})
        self.doc.setModified()
    
    @nodes
    def correct(self, nodes=[]):
        """Call the CurveOperationPlugin on the current nodes"""
        ds0, node0 = self.dsnode(nodes[0])
        T0 = node0.linked.prefix + 'kiln/T'
        ds1, node1 = self.dsnode(nodes[1])
        T1 = node1.linked.prefix + 'kiln/T'
        from misura.client import plugin
        p = plugin.CurveOperationPlugin(
            ax=T0, ay=node0.path, bx=T1, by=node1.path)
        # TODO: TC comparison?
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.CurveOperationPlugin)
        self.mainwindow.showDialog(d)
        
    @nodes
    def synchronize(self, nodes=[]):
        from misura.client import plugin

        reference_curve_full_path = self.widget_path_for(nodes[0])
        translating_curve_full_path = self.widget_path_for(nodes[1])

        sync_plugin = plugin.SynchroPlugin(
            reference_curve_full_path, translating_curve_full_path)

        dialog = PluginDialog(
            self.mainwindow, self.doc, sync_plugin, plugin.SynchroPlugin)
        self.mainwindow.showDialog(dialog)

    @node
    def thermalLegend(self, node=False):
        """Write thermal cycle onto a text label"""
        from misura.client import plugin
        p = plugin.ThermalCyclePlugin(test=node)
        d = PluginDialog(
            self.mainwindow, self.doc, p, plugin.ThermalCyclePlugin)
        self.mainwindow.showDialog(d)


    @node
    def deleteData(self, node=False, remove_dataset=True, recursive=True):
        """Delete a dataset and all depending graphical widgets."""
        self.model().pause(0)
        if not node:
            return True
        node_path = node.path
        # Remove and exit if dataset was only in available_data
        if self.doc.available_data.has_key(node_path):
            self.doc.available_data.pop(node_path)
            if not self.doc.data.has_key(node_path):
                return True
        # Remove and exit if no plot is associated
        if not self.model().plots['dataset'].has_key(node_path):
            if remove_dataset:
                self.doc.deleteDataset(node_path)
                self.doc.setModified()

            return True

        plots = self.model().plots['dataset'][node_path]
        # Collect involved graphs
        graphs = []
        # Collect plots to be removed
        remplot = []
        # Collect axes which should be removed
        remax = []
        # Collect objects which refers to xData or yData
        remobj = []
        # Remove associated plots
        for p in plots:
            p = self.doc.resolveFullWidgetPath(p)
            g = p.parent
            if g not in graphs:
                graphs.append(g)
            remax.append(g.getChild(p.settings.yAxis))
            remplot.append(p)

        # Check if an ax is referenced by other plots
        for g in graphs:
            for obj in g.children:
                if obj.typename == 'xy':
                    y = g.getChild(obj.settings.yAxis)
                    if y is None:
                        continue
                    # If the axis is used by an existent plot, remove from the
                    # to-be-removed list
                    if y in remax and obj not in remplot:
                        remax.remove(y)
                    continue
                # Search for xData/yData generic objects

                for s in ['xData', 'yData', 'xy']:
                    o = getattr(obj.settings, s, None)
                    refobj = g.getChild(o)
                    if refobj is None:
                        continue
                    if refobj not in plots + [node_path]:
                        continue
                    if obj not in remplot + remax + remobj:
                        remobj.append(obj)

        # Remove object and unreferenced axes
        for obj in remplot + remax + remobj:
            logging.debug('%s %s %s', 'Removing obj', obj.name, obj.path)
            obj.parent.removeChild(obj.name)
        # Finally, delete dataset
        if remove_dataset:
            self.doc.deleteDataset(node_path)
            logging.debug('%s %s', 'deleted', node_path)

        # Recursive call over derived datasets
        if recursive:
            for sub in node.children.itervalues():
                self.deleteData(sub, remove_dataset, recursive)

        self.doc.setModified()

        return True

    @nodes
    def deleteDatas(self, nodes=[]):
        """Call deleteData on each selected node"""
        for n in nodes:
            self.deleteData(node=n)


    def widget_path_for(self, node):
        result = '/'
        full_path = self.doc.model.is_plotted(node.path)
        if full_path:
            result = full_path[0]

        return result

    def xnames(self, y, page=False):
        """Get X dataset name for Y node y, in `page`"""
        logging.debug('%s %s %s %s', 'XNAMES', y, type(y), y.path)
        logging.debug('%s %s', 'y.linked', y.linked)
        logging.debug('%s %s', 'y.parent.linked', y.parent.linked)

        if page == False:
            page = self.model().page
        lk = y.linked if y.linked else y.parent.linked

        xname = axis_selection.get_best_x_for(y.path, lk.prefix, self.doc.data, page)

        return [xname]


    def dsnode(self, node):
        """Get node and corresponding dataset"""
        ds = node
        if isinstance(node, DatasetEntry):
            ds = node.ds
        return ds, node










    ####
    # Derived actions
    @node
    def overwrite(self, node=False):
        """Overwrite the parent dataset with a derived one."""
        ds, node = self.dsnode()
        from misura.client import plugin
        p = plugin.OverwritePlugin(
            a=node.parent.path, b=node.path, delete=True)
        d = PluginDialog(self.mainwindow, self.doc, p, plugin.OverwritePlugin)
        self.mainwindow.showDialog(d)
