#!/usr/bin/python
"""buildapi-rest.py action [options]"""
import urllib
from collections import namedtuple

try:
    import simplejson as json
except ImportError:
    import json

RESTMethodSpec = namedtuple('RESTMethodSpec', ['method', 'url', 'required_args', 'data_args'])

class Agent:
    methods = {
            'reprioritize': RESTMethodSpec('PUT', 'builds/%(branch)s/request/%(request_id)s',
                ('request_id', 'priority', 'branch'), ('request_id', 'priority')),
            'rebuild_request': RESTMethodSpec('POST', 'builds/%(branch)s/request',
                ('request_id', 'branch'), ('request_id', 'priority')),
            'cancel_request': RESTMethodSpec('DELETE', 'builds/%(branch)s/request/%(request_id)s',
                ('request_id', 'branch'), ()),
            'cancel_build': RESTMethodSpec('DELETE', 'builds/%(branch)s/build/%(build_id)s',
                ('build_id', 'branch'), ()),
            'new_build': RESTMethodSpec('POST', 'builds/%(branch)s/rev/%(revision)s',
                ('branch', 'revision'), ()),
            }

    def __init__(self, base_url):
        self.base_url = base_url

    def get_job_status(self, request_id):
        url = "%s/builds/jobs/%s?format=json" % (self.base_url, request_id)
        return urllib.urlopen(url).read()

    def do_action(self, action, options):
        if action not in self.methods:
            raise ValueError("Unknown action")

        spec = self.methods[action]

        kw = {}
        for arg in spec.required_args:
            if not hasattr(options, arg) or getattr(options, arg) is None:
                raise ValueError("%s is required" % arg)
            kw[arg] = getattr(options, arg)

        url = "%s/%s" % (self.base_url, spec.url % kw)
        url += "?format=json"

        data = {}
        for arg in spec.data_args:
            v = getattr(options, arg)
            if v is not None:
                data[arg] = v

        if spec.method != "GET":
            data['_method'] = spec.method

        data = urllib.urlencode(data)
        return urllib.urlopen(url, data).read()

if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser()
    parser.set_defaults(
            url=None,
            who=None,
            build_id=None,
            request_id=None,
            priority=None,
            branch=None,
            revision=None,
            wait=True,
            )
    parser.add_option('-u', '--url', dest='url')
    parser.add_option('-b', '--branch', dest='branch')
    parser.add_option('--build_id', dest='build_id')
    parser.add_option('--request_id', dest='request_id')
    parser.add_option('--priority', dest='priority')
    parser.add_option('--revision', dest='revision')
    parser.add_option('--dontwait', dest='wait', action='store_const', const=False)

    options, args = parser.parse_args()

    if len(args) != 1:
        parser.error("Must specify exactly one action")

    if not options.url:
        parser.error("Must specify a base url")

    a = Agent(options.url)
    action = args[0]

    result = json.loads(a.do_action(action, options))

    print result

    if options.wait:
        if result['status'] == "OK":
            request_id = result['request_id']
            import time
            while True:
                status = json.loads(a.get_job_status(request_id))
                print status
                if status['completed_at']:
                    break
                time.sleep(5)


