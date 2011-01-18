"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/contents.html
"""
from routes import Mapper

def make_map(config):
    """Create, configure and return the routes Mapper"""
    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    map.minimization = False

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved
    map.connect('/error/{action}', controller='error')
    map.connect('/error/{action}/{id}', controller='error')

    # CUSTOM ROUTES HERE
    map.connect('/pending', controller='pending', action='index')
    map.connect('/pending/{branch}', controller='pending', action='index')
    map.connect('/pending/{branch}/{platform}', controller='pending', action='index')

    map.connect('/running', controller='running', action='index')
    map.connect('/running/{branch}', controller='running', action='index')
    map.connect('/running/{branch}/{platform}', controller='running', action='index')

    map.connect('/recent', controller='recent', action='index')
    map.connect('/recent/{slave}', controller='recent', action='index')
    map.connect('/recent/{slave}/{count}', controller='recent', action='index')

    map.connect('/revision', controller='revision', action='index')
    map.connect('/revision/{branch}', controller='revision', action='index')
    map.connect('/revision/{branch}/{rev}', controller='revision', action='index')

    map.connect('/pushes', controller='pushes', action='index')
    map.connect('/pushes/{branch}', controller='pushes', action='index')
    map.connect('/pushes/{branch}/{fromtime}', controller='pushes', action='index')
    map.connect('/pushes/{branch}/{fromtime}/{totime}', controller='pushes', action='index')
    # we also support 'pushes/{branch}/?totime={totime}'

    map.connect('/reports/{action}', controller='reports')
    map.connect('/reports/builder/{buildername}', controller='reports', action='builder_details')
    map.connect('/reports/builders/{branch_name}', controller='reports', action='builders')
    map.connect('/reports/endtoend/{branch_name}', controller='reports', action='endtoend')
    map.connect('/reports/pushes', controller='reports', action='pushes')
    map.connect('/reports/revision', controller='reports', action='revision')
    map.connect('/reports/revision/{branch_name}/{revision}', controller='reports', action='endtoend_revision')
    map.connect('/reports/waittimes/{pool}', controller='reports', action='waittimes')

    map.connect('/reports/trychooser/{branch_name}', controller='reports', action='trychooser')

    # BuildAPI
    # Read-write
    map.connect('reprioritize', '/builds/{branch}/request/{request_id}', controller='builds', action='reprioritize', conditions=dict(method=['PUT']))
    map.connect('cancel_request', '/builds/{branch}/request/{request_id}', controller='builds', action='cancel_request', conditions=dict(method=['DELETE']))
    map.connect('cancel_build', '/builds/{branch}/build/{build_id}', controller='builds', action='cancel_build', conditions=dict(method=['DELETE']))
    map.connect('rebuild_build', '/builds/{branch}/build', controller='builds', action='rebuild_build', conditions=dict(method=['POST']))
    map.connect('rebuild_request', '/builds/{branch}/request', controller='builds', action='rebuild_request', conditions=dict(method=['POST']))
    map.connect('cancel_revision', '/builds/{branch}/rev/{revision}', controller='builds', action='cancel_revision', conditions=dict(method=['DELETE']))
    map.connect('new_build_at_rev', '/builds/{branch}/rev/{revision}', controller='builds', action='new_build_at_rev', conditions=dict(method=['POST']))
    #map.connect('new_build_for_builder', '/builds/{branch}/builders/{builder_name}', controller='builds', action='new_build_for_builder', conditions=dict(method=['POST']))

    # Status of jobs
    map.connect('job_status', '/builds/jobs/{job_id}', controller='builds', action='job_status')

    # Read-only
    map.connect('builds_home', '/builds', controller='builds', action='index')
    map.connect('branches', '/builds/branches', controller='builds', action='branches')
    map.connect('branch', '/builds/{branch}', controller='builds', action='branch')
    map.connect('build', '/builds/{branch}/build/{build_id}', controller='builds', action='build')
    map.connect('request', '/builds/{branch}/request/{request_id}', controller='builds', action='request')
    map.connect('revision', '/builds/{branch}/rev/{revision}', controller='builds', action='revision')
    map.connect('builders', '/builds/{branch}/builders', controller='builds', action='builders')
    map.connect('builder', '/builds/{branch}/builders/{builder_name}', controller='builds', action='builder')
    map.connect('user', '/builds/{branch}/user/{user}', controller='builds', action='user')

    # Redirect /foo/ to /foo
    map.redirect('/*(url)/', '/{url}', _redirect_code='301 Moved Permanently')

    return map
