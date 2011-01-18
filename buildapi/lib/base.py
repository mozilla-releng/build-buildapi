"""The base Controller API

Provides the BaseController class for subclassing.
"""
import time

from pylons.controllers import WSGIController
from pylons.templating import render_mako as render
from pylons import request, response, tmpl_context as c

from buildapi.lib import json

class BaseController(WSGIController):

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']
        return WSGIController.__call__(self, environ, start_response)

    def jsonify(self, data):
        response.headers['Content-Type'] = 'application/json'
        return json.dumps(data)

    def __before__(self):
        """Set self._fmt depending on query parameters or the Accept
        header"""
        self._started = time.time()
        c.started = self._started
        if 'format' in request.GET:
            self._fmt = request.GET.getone('format')
        elif 'Accept' in request.headers and 'application/json' in request.headers['Accept']:
            self._fmt = 'json'
        else:
            self._fmt = 'html'
