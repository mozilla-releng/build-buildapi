"""Pylons environment configuration"""
import os, thread

from mako.lookup import TemplateLookup
from pylons.configuration import PylonsConfig
from pylons.error import handle_mako_error
from sqlalchemy import engine_from_config

import buildapi.lib.app_globals as app_globals
import buildapi.lib.helpers
from buildapi.config.routing import make_map
from buildapi.model import init_scheduler_model, init_status_model,\
    init_buildapi_model
from buildapi.lib.mq import LoggingJobRequestPublisher, \
    LoggingJobRequestDoneConsumer

def load_environment(global_conf, app_conf):
    """Configure the Pylons environment via the ``pylons.config``
    object
    """
    config = PylonsConfig()

    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = dict(root=root,
                 controllers=os.path.join(root, 'controllers'),
                 static_files=os.path.join(root, 'public'),
                 templates=[os.path.join(root, 'templates')])

    # Initialize config with the basic options
    config.init_app(global_conf, app_conf, package='buildapi', paths=paths)

    config['routes.map'] = make_map(config)
    config['pylons.app_globals'] = app_globals.Globals(config)
    config['pylons.h'] = buildapi.lib.helpers
    config['pylons.tmpl_context_attach_args'] = True

    # Setup cache object as early as possible
    import pylons
    pylons.cache._push_object(config['pylons.app_globals'].cache)

    # Create the Mako TemplateLookup, with the default auto-escaping
    config['pylons.app_globals'].mako_lookup = TemplateLookup(
        directories=paths['templates'],
        error_handler=handle_mako_error,
        module_directory=os.path.join(app_conf['cache_dir'], 'templates'),
        input_encoding='utf-8', default_filters=['escape'],
        imports=['from webhelpers.html import escape'])

    # Setup the SQLAlchemy database engine
    scheduler_engine = engine_from_config(config, 'sqlalchemy.scheduler_db.')
    init_scheduler_model(scheduler_engine)

    status_engine = engine_from_config(config, 'sqlalchemy.status_db.')
    init_status_model(status_engine)

    buildapi_engine = engine_from_config(config, 'sqlalchemy.buildapi_db.')
    init_buildapi_model(buildapi_engine)

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)

    # Create our AMQP message publisher
    if 'mq.kombu_url' in config and 'testing' not in config:
        config['pylons.app_globals'].mq = LoggingJobRequestPublisher(buildapi_engine,
                config)

        # And our consumer
        config['pylons.app_globals'].mq_consumer = LoggingJobRequestDoneConsumer(
                buildapi_engine,
                config)
        thread.start_new_thread(config['pylons.app_globals'].mq_consumer.run, ())
    else:
        config['pylons.app_globals'].mq = None

    return config
