from buildapi.tests import *

class TestPendingController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='pending', action='index'))
        # Test response...
