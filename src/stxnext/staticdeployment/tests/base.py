import os
import tempfile

from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting
from plone.app.testing import FunctionalTesting


class StxStaticdeployLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load ZCML
        import stxnext.staticdeployment
        try:
            import plone.app.theming
            self.loadZCML(package=plone.app.theming)
            self.HAVE_THEMING = True
        except ImportError:
            self.HAVE_THEMING = False
        self.loadZCML(package=stxnext.staticdeployment)

        #prepare and load test configuration for stxnext.staticdeployment 
        self['resources_dir'] = os.path.join(os.path.dirname(__file__),
                'resources')
        self['tmp_dir'] = tempfile.mkdtemp()
        conf = open(os.path.join(self['resources_dir'], 'test.ini')).read()
        conf = conf % self['tmp_dir']
        test_conf_fd, self['test_conf_path'] = tempfile.mkstemp()
        test_conf_file = open(self['test_conf_path'], 'w')
        test_conf_file.write(conf)
        test_conf_file.close()

        stxnext.staticdeployment.app.util.get_config_path = \
                lambda: self['test_conf_path']



FIXTURE = StxStaticdeployLayer()
INTEGRATION_TESTING = IntegrationTesting(bases=(FIXTURE, ),
        name="StxStaticdeployLayer:Integration")
FUNCTIONAL_TESTING = FunctionalTesting(bases=(FIXTURE, ),
        name="StxStaticdeployLayer:Functional")
