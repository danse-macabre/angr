from .errors import KnowledgeBaseNoPlugin

import logging
l = logging.getLogger(name=__name__)


class KnowledgeBase(object):
    """Represents a "model" of knowledge about an artifact.

    The knowledge base should contain as absolutely little redundant data
    as possible - effectively the most fundemental artifacts that we can
    use to efficiently reconstruct anything the user would want to know about.
    """
    _default_plugins = {}

    def __init__(self, project, obj):
        self._project = project
        self.obj = obj
        self._plugins = {}

        # Temporary measure for the testing purposes only
        self.unresolved_indirect_jumps = set()
        self.resolved_indirect_jumps = set()

    @property
    def callgraph(self):
        return self.functions.callgraph

    def __setstate__(self, state):
        self._project = state['project']
        self.obj = state['obj']
        self._plugins = state['plugins']

    def __getstate__(self):
        s = {
            'project': self._project,
            'obj': self.obj,
            'plugins': self._plugins,
        }
        return s

    #
    # Plugin accessor
    #

    def __contains__(self, plugin_name):
        return plugin_name in self._plugins

    def __getattr__(self, v):
        return self.get_plugin(v)

    #
    # Plugins
    #

    def has_plugin(self, name):
        return name in self._plugins

    def get_plugin(self, name):
        if name in self._plugins:
            return self._plugins[name]

        elif name in self._default_plugins:
            plugin_cls = self._default_plugins[name]
            return self.register_plugin(name, plugin_cls(kb=self))

        else:
            raise KnowledgeBaseNoPlugin("No such plugin: %s" % name)

    def register_plugin(self, name, plugin):
        self._plugins[name] = plugin
        return plugin

    def release_plugin(self, name):
        if name in self._plugins:
            del self._plugins[name]

    @classmethod
    def register_default(cls, name, plugin_cls):
        if name in cls._default_plugins:
            l.warn("%s is already set as the default for %s" % (cls._default_plugins[name], name))
        cls._default_plugins[name] = plugin_cls


import knowledge_plugins

# Knowledge Artifacts
KnowledgeBase.register_default('basic_blocks', knowledge_plugins.BasicBlocksPlugin)
KnowledgeBase.register_default('indirect_jumps', knowledge_plugins.IndirectJumpsPlugin)
KnowledgeBase.register_default('labels', knowledge_plugins.LabelsPlugin)
KnowledgeBase.register_default('functions', knowledge_plugins.FunctionManager)
KnowledgeBase.register_default('variables', knowledge_plugins.VariableManager)

# Knowledge Views
KnowledgeBase.register_default('blocks', knowledge_plugins.BlockView)
KnowledgeBase.register_default('transitions', knowledge_plugins.TransitionsView)

