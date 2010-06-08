from buildapi.controllers.results import ResultsController

class PendingController(ResultsController):
    def __init__(self, **kwargs):
       ResultsController.__init__(self, pending=True, running=False, complete=False, 
                                  template="/pending.mako", **kwargs)   
