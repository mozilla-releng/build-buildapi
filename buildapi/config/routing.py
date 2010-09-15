"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
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
    map.connect('/reports/pushes', controller='reports', action='pushes')
    map.connect('/reports/waittimes/{pool}', controller='reports', action='waittimes')
    map.connect('/reports/endtoend/{branch_name}', controller='reports', action='endtoend')
    map.connect('/reports/revision/{branch_name}/{revision}', controller='reports', action='endtoend_revision')

    map.connect('/{controller}/{action}')
    map.connect('/{controller}/{action}/{id}')

    # Redirect /foo/ to /foo
    map.redirect('/*(url)/', '/{url}', _redirect_code='301 Moved Permanently')

    return map
