import logging

from pylons import request, response, session, tmpl_context as c, url
from pylons.controllers.util import abort, redirect
from pylons.decorators import jsonify
from sqlalchemy import *

from buildapi.lib.base import BaseController, render
import buildapi.model.meta as meta

log = logging.getLogger(__name__)

class PendingController(BaseController):

    def getBranch(self,longname):
        # nightlies don't have a branch set (FIXME)
        if not longname:
            return None
        
        branch = longname 
        
        # handle releases/mozilla-1.9.2, projects/foo, users/bob/foopy
        # by taking the part after the last '/'
        branch = branch.split('/')[-1]
        
        # handle unit 'branches' by trimming off '-platform-buildtype-test'
        # eg mozilla-central-win32-opt-unittest
        #    addonsmgr-linux-debug-unittest
        if branch.endswith('unittest'):
            branch = '-'.join(branch.split('-')[0:-3])        

        # trim off any leading 'l10n-' ??
        
        return branch

    def index(self, branch=None, platform=None):
        if 'format' in request.GET:
            format = request.GET.getone('format')
        else:
            format = 'html'

        if format not in ('html', 'json'):
            abort(400, detail='Unsupported format: %s' % format)

        if branch is not None:
            branch = [branch]
        elif 'branch' in request.GET:
            branch = request.GET.getall('branch')

        # query builds
        br = meta.scheduler_db_meta.tables['buildrequests']
        bs = meta.scheduler_db_meta.tables['buildsets']
        ss = meta.scheduler_db_meta.tables['sourcestamps']
        q = select([br.c.id,
                    br.c.buildsetid,
                    ss.c.branch,
                    ss.c.revision,
                    br.c.buildername,
                    br.c.submitted_at])
        q = q.where(and_(br.c.buildsetid==bs.c.id, bs.c.sourcestampid==ss.c.id))
        q = q.where(br.c.claimed_at == 0)
        # ignore nightlies, FIXME ?
        q = q.where(ss.c.revision != None)
        if branch is not None:
          q = q.where(ss.c.branch.like('%' + branch[0] + '%'))
        query_results = q.execute()

        c.pending_builds = {}
        for r in query_results:
            real_branch = self.getBranch(r['branch'])
            revision = r['revision'][:12]
            if real_branch not in c.pending_builds:
                c.pending_builds[real_branch] = {}
            if revision not in c.pending_builds[real_branch]:
                c.pending_builds[real_branch][revision] = []

            this_result = {}
            for key,value in r.items():
                this_result[key] = value
            this_result['branch'] = real_branch
            c.pending_builds[real_branch][revision].append(this_result)
                

        # Return a rendered template
        # or, return a json blob
        if format == "html":
            return render("/pending.mako")
        else:
            return self.jsonify({'pending': c.pending_builds})

