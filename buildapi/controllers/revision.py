from buildapi.controllers.results import ResultsController

class RevisionController(ResultsController):
    def __init__(self, **kwargs):
       ResultsController.__init__(self, pending=True, running=False, complete=False,
                                   revision=True,
                                   template="/revision.mako", **kwargs)
