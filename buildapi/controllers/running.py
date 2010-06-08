from buildapi.controllers.results import ResultsController

class RunningController(ResultsController):
    def __init__(self, **kwargs):
       ResultsController.__init__(self, pending=False, running=True, complete=False,
                                  template="/running.mako", **kwargs)
