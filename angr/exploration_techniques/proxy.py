from . import ExplorationTechnique


class ProxyTechnique(ExplorationTechnique):
    """
    This dummy technique could be used to hook a couple of simulation manager methods
    without actually creating a new exploration technique, for example:

    class SomeComplexAnalysis(Analysis):

        def do_something():
            simgr = self.project.factory.simgr()
            simgr.use_tech(ProxyTechnique(step_state=self._step_state))
            simgr.run()

        def _step_state(self, state):
            # Do stuff!
            pass

    In the above example, the _step_state method can access all the neccessary stuff,
    hidden in the analysis instance, without passing that instance to a one-shot-styled
    exploration technique.
    """

    def __init__(self, setup=None, step_state=None, step=None, filter=None, complete=None):
        super(ProxyTechnique, self).__init__()
        self.setup = _its_a_func(setup) or super(ProxyTechnique, self).setup
        self.step_state = _its_a_func(step_state) or super(ProxyTechnique, self).step_state
        self.step = _its_a_func(step) or super(ProxyTechnique, self).step
        self.filter = _its_a_func(filter) or super(ProxyTechnique, self).filter
        self.complete = _its_a_func(complete) or super(ProxyTechnique, self).complete


def _its_a_func(func):
    """
    In case the target func doesn't have it's `im_func` attr set.

    :param func:
    :return:
    """
    if func is not None:
        func.im_func = True
    return func
