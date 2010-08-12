import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.decorators import jsonify
from pylons.decorators.cache import beaker_cache

from buildapi.lib import helpers as h
from buildapi.lib.base import BaseController, render
from buildapi.lib.visualization import gviz_pushes
from buildapi.model.pushes import GetPushes

import time

log = logging.getLogger(__name__)

class SourcestampsController(BaseController):

    def __init__(self, **kwargs):
        BaseController.__init__(self, **kwargs)

    @beaker_cache(query_args=True)
    def index(self):
        format = request.GET.getone('format') if 'format' in request.GET else 'html'
        if format not in ('html', 'json', 'chart'):
            abort(400, detail='Unsupported format: %s' % format)
        
        params = {}
        try: 
            if 'starttime' in request.GET:
                params['starttime'] = float(request.GET.getone('starttime'))
            if 'endtime' in request.GET:
                params['endtime'] = float(request.GET.getone('endtime'))
            if 'int' in request.GET:
                params['int_size'] = int(request.GET.getone('int'))
        except ValueError, e:
            abort(400, detail='Unsupported non numeric parameter value: %s' % e)
        
        if 'int_size' not in params or params['int_size']<=0:
            abort(400, detail='Time interval (int parameter) must be higher than 0: %s.' % int_size)
  
        c.report = GetPushes(**params)

        if format == 'json':
            return c.report.jsonify()
        elif format == 'chart':
            return gviz_pushes(c.report)
        else:
            return render('/sourcestamps.mako')
