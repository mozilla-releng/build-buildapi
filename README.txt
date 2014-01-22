Installation and Setup
======================

Install ``buildapi`` using easy_install::

    easy_install buildapi

Then install either redis or memcached:

    easy_install redis
    easy_install python-memcached

Make a config file as follows::

    paster make-config buildapi config.ini

Tweak the config file as appropriate::

    email_to = your email
    port = something available, eg. 6005
    update the sqlalchemy db urls and the carrot info as needed for staging/dev
    # add the following lines to have your url be http://cruncher.build.mozilla.org/~(username)/wsgi
    [filter:proxy-prefix]
    use = egg:PasteDeploy#prefix
    prefix = /~(username)/wsgi

Also set up your cache configuration:

    buildapi.cache = redis:HOSTNAME:PORT

or

    buildapi.cache = memcached:HOSTNAME:PORT,HOSTNAME:PORT,..

You'll need to set up some scheduler and status DB's.  The schema for these
DBs are in the root directory, although you may want to fill them with test
data which is not included.

    sqlite3 statusdb.sqlite3 < statusdb_schema.sql
    sqlite3 schedulerdb.sqlite3 < schedulerdb_schema.sql
    sqlite3 buildapi.sqlite3 < buildapi_schema.sql

And point the proper DB strings

Now setup the application::

    paster setup-app config.ini

Edit your config.ini to add to the [app:main] section::

    filter-with = proxy-prefix

Now you can start/stop your application::

    paster serve --daemon config.ini
    paster serve --stop-daemon

You should be able to load pages like http://cruncher.build.mozilla.org/~(username)/wsgi/self-serve

Installing google viz::

    wget http://google-visualization-python.googlecode.com/files/gviz_api_py-1.7.0.tar.gz
    tar -xvf gviz_api_py-1.7.0.tar.gz
    cd gviz_api_py-1.7.0
    python setup.py install
    python setup.py test

Now you should be able to see reports like http://cruncher.build.mozilla.org/~(username)/wsgi/reports/pushes
which use the google visualization library (make sure you have the statusdb set in your config.ini
