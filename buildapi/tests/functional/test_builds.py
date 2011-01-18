from buildapi.tests import *
from buildapi.model import init_scheduler_model, init_buildapi_model
from buildapi.lib import json
import sqlalchemy
import os, time

import mock

class TestBuildsController(TestController):

    def setUp(self):
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:")
        sql = open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "state.sql")).read().split(";")
        for line in sql:
            line = line.strip()
            self.engine.execute(line)
        init_scheduler_model(self.engine)
        init_buildapi_model(self.engine)

        self.g.mq.engine.execute('delete from jobrequests')

        # disable actually sending messages!
        self.g.mq.send = mock.Mock()

    def get_jobrequests(self):
        p = self.g.mq.engine.execute('select * from jobrequests')
        requests = p.fetchall()
        return requests

    def test_branches(self):
        response = self.app.get(url('branches', format='json')).json
        self.assertEquals(response, self.config['branches'])

    def test_builders(self):
        # We have to fake out time.time here so it returns a time closely after
        # the build requests in the test database
        with mock.patch('time.time') as fake_time:
            fake_time.return_value = 1285848043

            response = self.app.get(url('builders', branch='branch1', format='json')).json
            self.assertEquals(response, ['branch1-build'])

            response = self.app.get(url('builders', branch='branch2', format='json')).json
            self.assertEquals(response, ['branch2-build'])

    def test_builders_bad_branch(self):
        response = self.app.get(url('builders', branch='branch3', format='json'), status=404)
        self.assertEquals(response.status_int, 404)
        self.assert_("Branch branch3 not found" in response.body)

    def test_branch(self):
        response = self.app.get(url('branch', branch='branch1', format='json')).json
        self.assertEquals(len(response['builds']), 1)
        self.assertEquals(len(response['pending']), 2)

    def test_branch2(self):
        response = self.app.get(url('branch', branch='branch2', format='json')).json
        self.assertEquals(len(response['builds']), 0)
        self.assertEquals(len(response['running']), 1)
        self.assertEquals(len(response['pending']), 0)

    def test_build(self):
        response = self.app.get(url('build', branch='branch1', build_id=1, format='json')).json
        self.assertEquals(response['branch'], 'branch1')
        self.assertEquals(len(response['requests']), 1)

    def test_no_build(self):
        response = self.app.get(url('build', branch='branch1', build_id=2, format='json'), status=404)
        self.assertEquals(response.status_int, 404)
        self.assert_("Build 2 not found on branch branch1" in response.body)

    def test_request(self):
        response = self.app.get(url('request', branch='branch1', request_id=1, format='json')).json
        self.assertEquals(response['revision'], '123456789')

    def test_revision(self):
        response = self.app.get(url('revision', branch='branch1', revision='123456789', format='json')).json
        self.assertEquals(len(response['builds']), 1)
        self.assertEquals(len(response['pending']), 0)

    def test_reprioritize(self):
        self.g.mq._clock = mock.Mock(return_value=543221)
        p = self.engine.execute('select priority from buildrequests where id=3').scalar()
        self.assertEquals(p, 0)
        response = self.app.put(url('reprioritize', branch='branch1', request_id=3), {'priority': 1}, extra_environ=dict(REMOTE_USER='me'))

        # We're looking for a message being sent, not an actual change in the priority
        requests = self.get_jobrequests()
        self.assertEquals(len(requests), 1)
        r = requests[0]
        self.assertEquals(r.action, 'reprioritize')
        self.assertEquals(r.who, 'me')
        self.assertEquals(json.loads(r.what), {'priority': 1, 'brid': 3})

    def test_reprioritize_bad_priority(self):
        response = self.app.put(url('reprioritize', branch='branch1', request_id=1), {'priority': 'a'}, extra_environ=dict(REMOTE_USER='me'), status=400)
        self.assertEquals(response.status_int, 400)
        self.assert_("Bad priority" in response.body)

    def test_reprioritize_completed_request(self):
        response = self.app.put(url('reprioritize', branch='branch1', request_id=1, format='json'), {'priority': 1}, extra_environ=dict(REMOTE_USER='me'), status=400)
        self.assertEquals(response.json['status'], 'FAILED')

    def test_reprioritize_running_build(self):
        response = self.app.put(url('reprioritize', branch='branch2', request_id=2, format='json'), {'priority': 1}, extra_environ=dict(REMOTE_USER='me'), status=400)
        self.assertEquals(response.json['status'], 'FAILED')

    def test_reprioritize_pending_build(self):
        response = self.app.put(url('reprioritize', branch='branch1', request_id=3, format='json'), {'priority': 1}, extra_environ=dict(REMOTE_USER='me'))
        self.assertEquals(response.json['status'], "OK")

    def test_reprioritize_bad_request(self):
        response = self.app.put(url('reprioritize', branch='branch1', request_id=123), {'priority': 1}, extra_environ=dict(REMOTE_USER='me'), status=404)
        self.assertEquals(response.status_int, 404)
        self.assert_("not found on branch" in response.body)

    def test_reprioritize_no_priority(self):
        response = self.app.put(url('reprioritize', branch='branch1', request_id=1), extra_environ=dict(REMOTE_USER='me'), status=400)
        self.assertEquals(response.status_int, 400)
        self.assert_("Bad priority" in response.body, response.body)

    def test_cancel_pending(self):
        response = self.app.delete(url('cancel_request', branch='branch1', request_id=3, format='json'), extra_environ=dict(REMOTE_USER='me'))

        requests = self.get_jobrequests()
        self.assertEquals(len(requests), 1)
        r = requests[0]
        self.assertEquals(r.who, 'me')
        self.assertEquals(r.action, 'cancel_request')
        self.assertEquals(json.loads(r.what), {'brid': 3})

    def test_cancel_running_request(self):
        response = self.app.delete(url('cancel_request', branch='branch2', request_id=2, format='json'), extra_environ=dict(REMOTE_USER='me'))

        requests = self.get_jobrequests()
        self.assertEquals(len(requests), 1)
        r = requests[0]
        self.assertEquals(r.who, 'me')
        self.assertEquals(r.action, 'cancel_request')
        self.assertEquals(json.loads(r.what), {'brid': 2})

    def test_cancel_complete_request(self):
        response = self.app.delete(url('cancel_request', branch='branch1', request_id=1, format='json'), extra_environ=dict(REMOTE_USER='me'))

        requests = self.get_jobrequests()
        self.assertEquals(len(requests), 1)
        r = requests[0]
        self.assertEquals(r.who, 'me')
        self.assertEquals(r.action, 'cancel_request')
        self.assertEquals(json.loads(r.what), {'brid': 1})

    def test_cancel_running_build(self):
        complete, claimed_at = self.engine.execute('select complete, claimed_at from buildrequests where id=2').fetchone()
        self.assertEquals(complete, 0)
        self.assert_(claimed_at != 0)

        self.app.delete(url('cancel_build', branch='branch2', build_id=2, format='json'), extra_environ=dict(REMOTE_USER='me'))

        # We're looking for a message being sent, not an actual change in the priority
        requests = self.get_jobrequests()
        self.assertEquals(len(requests), 1)
        r = requests[0]
        self.assertEquals(r.action, 'cancel_build')
        self.assertEquals(r.who, 'me')
        self.assertEquals(json.loads(r.what), {'bid': 2})

    def test_rebuild_build(self):
        old_req = self.engine.execute("select * from buildrequests where id=5").fetchone()
        self.assertEquals(old_req, None)

        old_build = self.engine.execute("select * from builds, buildrequests, buildsets where builds.id=1 and builds.brid= buildrequests.id and buildrequests.buildsetid = buildsets.id").fetchone()

        response = self.app.post(url('rebuild_build', branch='branch1', format='json'), {'build_id': 1}, extra_environ=dict(REMOTE_USER='me'))

        requests = self.get_jobrequests()
        self.assertEquals(len(requests), 1)
        r = requests[0]
        self.assertEquals(r.action, 'rebuild_build')
        self.assertEquals(r.who, 'me')
        self.assertEquals(json.loads(r.what), {'priority': 0, 'bid': 1})

    def test_rebuild_build_priority(self):
        response = self.app.post(url('rebuild_build', branch='branch1', format='json'), {'build_id': 1, 'priority': 1}, extra_environ=dict(REMOTE_USER='me'))

        requests = self.get_jobrequests()
        self.assertEquals(len(requests), 1)
        r = requests[0]
        self.assertEquals(r.action, 'rebuild_build')
        self.assertEquals(r.who, 'me')
        self.assertEquals(json.loads(r.what), {'priority': 1, 'bid': 1})

    def test_rebuild_request(self):
        old_req = self.engine.execute("select * from buildrequests where id=5").fetchone()
        self.assertEquals(old_req, None)

        old_req = self.engine.execute("select * from buildrequests, buildsets where buildrequests.id=1 and buildrequests.buildsetid = buildsets.id").fetchone()

        response = self.app.post(url('rebuild_request', branch='branch1', format='json'), {'request_id': 1}, extra_environ=dict(REMOTE_USER='me'))

        requests = self.get_jobrequests()
        self.assertEquals(len(requests), 1)
        r = requests[0]
        self.assertEquals(r.action, 'rebuild_request')
        self.assertEquals(r.who, 'me')
        self.assertEquals(json.loads(r.what), {'priority': 0, 'brid': 1})

    def test_rebuild_request_priority(self):
        response = self.app.post(url('rebuild_request', branch='branch1', format='json'), {'request_id': 1, 'priority': 1}, extra_environ=dict(REMOTE_USER='me'))

        requests = self.get_jobrequests()
        self.assertEquals(len(requests), 1)
        r = requests[0]
        self.assertEquals(r.action, 'rebuild_request')
        self.assertEquals(r.who, 'me')
        self.assertEquals(json.loads(r.what), {'priority': 1, 'brid': 1})

    def test_cancel_running_revision(self):
        response = self.app.delete(url('cancel_revision', branch='branch2', revision='abcdefghi', format='json'), extra_environ=dict(REMOTE_USER='me'))

        requests = self.get_jobrequests()
        self.assertEquals(len(requests), 1)
        r = requests[0]
        self.assertEquals(r.action, 'cancel_revision')
        self.assertEquals(r.who, 'me')
        self.assertEquals(json.loads(r.what), {'branch': 'branch2', 'revision': 'abcdefghi'})

    def test_cancel_pending_revision(self):
        response = self.app.delete(url('cancel_revision', branch='branch1', revision='987654321', format='json'), extra_environ=dict(REMOTE_USER='me'))

        requests = self.get_jobrequests()
        self.assertEquals(len(requests), 1)
        r = requests[0]
        self.assertEquals(r.action, 'cancel_revision')
        self.assertEquals(r.who, 'me')
        self.assertEquals(json.loads(r.what), {'branch': 'branch1', 'revision': '987654321'})

    def _test_cross_branch(self):
        assert False, "TODO: check off-branch requests like cancelBuild/Request/etc."

    def _test_noauth(self):
        auth_methods = [
                ('reprioritize', 'put', {'branch': 'branch1', 'request_id': 1}),
                ('cancel_request', 'delete', {'branch': 'branch1', 'request_id': 1}),
                ('cancel_build', 'delete', {'branch': 'branch1', 'build_id': 1}),
                ('rebuild_build', 'post', {'branch': 'branch1'}),
                ('rebuild_request', 'post', {'branch': 'branch1'}),
                ('cancel_revision', 'delete', {'branch': 'branch1', 'revision': '1234567'}),
                ('new_build_at_rev', 'post', {'branch': 'branch1', 'revision': '1234567'}),
                ('new_build_for_builder', 'post', {'branch': 'branch1', 'builder_name': ' branch1-build'}),
                ]

        for name, method, params in auth_methods:
            method_func = getattr(self.app, method)
            response = method_func(url(name, format='json', **params), status=403)
            self.assertEquals(response.status_int, 403)
            self.assert_("ACCESS DENIED" in response.body)

    def _test_badbranch(self):
        auth_environ = {'extra_environ': {'REMOTE_USER': 'me'}}
        branch_methods = [
                ('reprioritize', 'put', {'request_id': 1}, auth_environ),
                ('cancel_request', 'delete', {'request_id': 1}, auth_environ),
                ('cancel_build', 'delete', {'build_id': 1}, auth_environ),
                ('rebuild_build', 'post', {}, auth_environ),
                ('rebuild_request', 'post', {}, auth_environ),
                ('cancel_revision', 'delete', {'revision': '1234567'}, auth_environ),
                ('new_build_at_rev', 'post', {'revision': '1234567'}, auth_environ),
                ('new_build_for_builder', 'post', {'builder_name': ' branch1-build'}, auth_environ),

                ('branch', 'get', {}, {}),
                ]

        for name, method, params, extra in branch_methods:
            method_func = getattr(self.app, method)
            response = method_func(url(name, branch='badbranch', format='json', **params), status=404, **extra)
            self.assertEquals(response.status_int, 404)
            self.assert_("not found" in response.body)
