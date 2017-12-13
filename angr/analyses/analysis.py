import sys
import contextlib
from collections import defaultdict
import progressbar
import logging

from ..misc import PluginHub
from ..misc.ux import deprecated
from ..errors import AngrAnalysisError

l = logging.getLogger("angr.analysis")


class AnalysisLogEntry(object):
    def __init__(self, message, exc_info=False):
        if exc_info:
            (e_type, value, traceback) = sys.exc_info()
            self.exc_type = e_type
            self.exc_value = value
            self.exc_traceback = traceback
        else:
            self.exc_type = None
            self.exc_value = None
            self.exc_traceback = None

        self.message = message

    def __getstate__(self):
        return str(self.__dict__.get("exc_type")), \
               str(self.__dict__.get("exc_value")), \
               str(self.__dict__.get("exc_traceback")), \
               self.message

    def __setstate__(self, s):
        self.exc_type, self.exc_value, self.exc_traceback, self.message = s

    def __repr__(self):
        if self.exc_type is None:
            msg_str = repr(self.message)
            if len(msg_str) > 70:
                msg_str = msg_str[:66] + '...'
                if msg_str[0] in ('"', "'"):
                    msg_str += msg_str[0]
            return '<AnalysisLogEntry %s>' % msg_str
        else:
            msg_str = repr(self.message)
            if len(msg_str) > 40:
                msg_str = msg_str[:36] + '...'
                if msg_str[0] in ('"', "'"):
                    msg_str += msg_str[0]
            return '<AnalysisLogEntry %s with %s: %s>' % (msg_str, self.exc_type.__name__, self.exc_value)


class Analyses(PluginHub):
    """
    This class contains functions for all the registered and runnable analyses,
    """
    def __init__(self, p):
        """
        Creates an Analyses object

        :ivar p:                A project
        :type p:                angr.Project
        """
        super(Analyses, self).__init__()
        self.project = p

    @deprecated
    def reload_analyses(self):
        return

    def get_plugin(self, name):
        analysis_cls = super(Analyses, self).get_plugin(name)
        return AnalysisFactory(self.project, analysis_cls, name)

    def _init_plugin(self, plugin_cls):
        return plugin_cls

    def __getattribute__(self, name):
        plugins = super(Analyses, self).__getattribute__('_plugins')
        if name in plugins:
            return AnalysisFactory(self.project, plugins[name], name)
        return super(Analyses, self).__getattribute__(name)

    def __getstate__(self):
        s = super(Analyses, self).__getstate__()
        s['project'] = self.project
        return s

    def __setstate__(self, s):
        super(Analyses, self).__setstate__(s)
        self.project = s['project']


class AnalysisFactory(object):

    def __init__(self, project, analysis_cls, name):
        self._project = project
        self._analysis_cls = analysis_cls
        self._name = name

    def __call__(self, *args, **kwargs):
        fail_fast = kwargs.pop('fail_fast', False)
        kb = kwargs.pop('kb', self._project.kb)
        progress_callback = kwargs.pop('progress_callback', None)
        show_progressbar = kwargs.pop('show_progressbar', False)

        oself = object.__new__(self._analysis_cls)
        oself.named_errors = {}
        oself.errors = []
        oself.log = []

        oself._fail_fast = fail_fast
        oself._name = self._name
        oself.project = self._project
        oself.kb = kb
        oself._progress_callback = progress_callback

        if oself._progress_callback is not None:
            if not hasattr(oself._progress_callback, '__call__'):
                raise AngrAnalysisError('The "progress_callback" parameter must be a None or a callable.')

        oself._show_progressbar = show_progressbar
        oself.__init__(*args, **kwargs)
        return oself


class Analysis(object):
    """
    This class represents an analysis on the program.


    :ivar project:  The project for this analysis.
    :type project:  angr.Project
    :ivar KnowledgeBase kb: The knowledgebase object.
    :ivar callable _progress_callback: A callback function for receiving the progress of this analysis. It only takes
                                        one argument, which is a float number from 0.0 to 100.0 indicating the current
                                        progress.
    :ivar bool _show_progressbar: If a progressbar should be shown during the analysis. It's independent from
                                    _progress_callback.
    :ivar progressbar.ProgressBar _progressbar: The progress bar object.
    """
    project = None
    kb = None
    _fail_fast = None
    _name = None
    errors = []
    named_errors = defaultdict(list)
    _progress_callback = None
    _show_progressbar = False
    _progressbar = None

    _PROGRESS_WIDGETS = [
        progressbar.Percentage(),
        ' ',
        progressbar.Bar(),
        ' ',
        progressbar.Timer(),
        ' ',
        progressbar.ETA()
    ]

    @contextlib.contextmanager
    def _resilience(self, name=None, exception=Exception):
        try:
            yield
        except exception:  # pylint:disable=broad-except
            if self._fail_fast:
                raise
            else:
                error = AnalysisLogEntry("exception occurred", exc_info=True)
                l.error("Caught and logged %s with resilience: %s", error.exc_type.__name__, error.exc_value)
                if name is None:
                    self.errors.append(error)
                else:
                    self.named_errors[name].append(error)

    def _initialize_progressbar(self):
        """
        Initialize the progressbar.
        :return: None
        """

        self._progressbar = progressbar.ProgressBar(widgets=Analysis._PROGRESS_WIDGETS, maxval=10000 * 100).start()

    def _update_progress(self, percentage):
        """
        Update the progress with a percentage, including updating the progressbar as well as calling the progress
        callback.

        :param float percentage: Percentage of the progressbar. from 0.0 to 100.0.
        :return: None
        """

        if self._show_progressbar:
            if self._progressbar is None:
                self._initialize_progressbar()

            self._progressbar.update(percentage * 10000)

        if self._progress_callback is not None:
            self._progress_callback(percentage)  # pylint:disable=not-callable

    def _finish_progress(self):
        """
        Mark the progressbar as finished.
        :return: None
        """

        if self._show_progressbar:
            if self._progressbar is None:
                self._initialize_progressbar()
            if self._progressbar is not None:
                self._progressbar.finish()

        if self._progress_callback is not None:
            self._progress_callback(100.0)  # pylint:disable=not-callable

    def __repr__(self):
        return '<%s Analysis Result at %#x>' % (self._name, id(self))
