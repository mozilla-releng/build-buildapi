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
    map.connect('/pending/{branch}/{platform}', controller='pending',
        action='index')

    map.connect('/running', controller='running', action='index')
    map.connect('/running/{branch}', controller='running', action='index')
    map.connect('/running/{branch}/{platform}', controller='running',
        action='index')

    map.connect('/recent', controller='recent', action='index')
    map.connect('/recent/{slave}', controller='recent', action='index')
    map.connect('/recent/{slave}/{count}', controller='recent', action='index')

    map.connect('/revision', controller='revision', action='index')
    map.connect('/revision/{branch}', controller='revision', action='index')
    map.connect('/revision/{branch}/{rev}', controller='revision',
        action='index')

    map.connect('/pushes', controller='pushes', action='index')
    map.connect('/pushes/{branch}', controller='pushes', action='index')
    map.connect('/pushes/{branch}/{fromtime}', controller='pushes', action='index')
    map.connect('/pushes/{branch}/{fromtime}/{totime}', controller='pushes',
        action='index')
    # we also support 'pushes/{branch}/?totime={totime}'

    map.connect('/reports/{action}', controller='reports')
    map.connect('/reports/builder/{buildername}', controller='reports',
        action='builder_details')
    map.connect('/reports/builders/{branch_name}', controller='reports',
        action='builders')
    map.connect('/reports/endtoend/{branch_name}', controller='reports',
        action='endtoend')
    map.connect('/reports/pushes', controller='reports', action='pushes')
    map.connect('/reports/revision', controller='reports', action='revision')
    map.connect('/reports/revision/{branch_name}/{revision}', 
        controller='reports', action='endtoend_revision')
    map.connect('/reports/slaves', controller='reports', action='slaves')
    map.connect('/reports/slaves/{slave_id}', controller='reports', 
        action='slave_details')
    map.connect('/reports/status_builders', controller='reports', 
        action='status_builders')
    map.connect('/reports/status_builders/{builder_name}', 
        controller='reports', action='status_builder_details')
    map.connect('/reports/trychooser/{branch_name}', controller='reports', 
        action='trychooser')
    map.connect('/reports/waittimes/{pool}', controller='reports', 
        action='waittimes')

    # BuildAPI
    # Read-write
    map.connect('reprioritize', '/self-serve/{branch}/request/{request_id}', controller='selfserve', action='reprioritize', conditions=dict(method=['PUT']))
    map.connect('cancel_request', '/self-serve/{branch}/request/{request_id}', controller='selfserve', action='cancel_request', conditions=dict(method=['DELETE']))
    map.connect('cancel_build', '/self-serve/{branch}/build/{build_id}', controller='selfserve', action='cancel_build', conditions=dict(method=['DELETE']))
    map.connect('rebuild_build', '/self-serve/{branch}/build', controller='selfserve', action='rebuild_build', conditions=dict(method=['POST']))
    map.connect('rebuild_request', '/self-serve/{branch}/request', controller='selfserve', action='rebuild_request', conditions=dict(method=['POST']))
    #map.connect('cancel_revision', '/self-serve/{branch}/rev/{revision}', controller='selfserve', action='cancel_revision', conditions=dict(method=['DELETE']))
    map.connect('new_build_at_rev', '/self-serve/{branch}/rev/{revision}', controller='selfserve', action='new_build_at_rev', conditions=dict(method=['POST']))
    #map.connect('new_build_for_builder', '/self-serve/{branch}/builders/{builder_name}', controller='selfserve', action='new_build_for_builder', conditions=dict(method=['POST']))

    # Status of jobs
    map.connect('job_status', '/self-serve/jobs/{job_id}', controller='selfserve', action='job_status')

    # Read-only
    map.connect('selfserve_home', '/self-serve', controller='selfserve', action='index')
    map.connect('branches', '/self-serve/branches', controller='selfserve', action='branches')
    map.connect('branch', '/self-serve/{branch}', controller='selfserve', action='branch')
    map.connect('build', '/self-serve/{branch}/build/{build_id}', controller='selfserve', action='build')
    map.connect('request', '/self-serve/{branch}/request/{request_id}', controller='selfserve', action='request')
    map.connect('revision', '/self-serve/{branch}/rev/{revision}', controller='selfserve', action='revision')
    map.connect('builders', '/self-serve/{branch}/builders', controller='selfserve', action='builders')
    map.connect('builder', '/self-serve/{branch}/builders/{builder_name}', controller='selfserve', action='builder')
    map.connect('user', '/self-serve/{branch}/user/{user}', controller='selfserve', action='user')

    # Redirect /foo/ to /foo
    map.redirect('/*(url)/', '/{url}', _redirect_code='301 Moved Permanently')

    return map
