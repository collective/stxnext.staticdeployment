import os
import shutil
import tempfile

from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting
from plone.app.testing import FunctionalTesting
from plone.app.testing import setRoles
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import login
from plone.app.testing import logout

import stxnext.staticdeployment


class StxStaticdeployLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load ZCML
        self.loadZCML(package=stxnext.staticdeployment)
        self.loadZCML(package=stxnext.staticdeployment, name='tests/test.zcml')


    def setUpPloneSite(self, portal):
        setRoles(portal, TEST_USER_ID, ['Manager'])
        login(portal, TEST_USER_NAME)
        wftool =  portal.portal_workflow
        # set default workflow
        wftool.setDefaultChain('simple_publication_workflow')

        # create image object
        portal.invokeFactory('Image', 'i1', title=u'Image 1')
        # create document objects
        portal.invokeFactory('Folder', 'f1', title=u'Folder 1')
        portal.invokeFactory('Folder', 'f2', title=u'Unpublished Folder')
        # publish Document 1
        f1 = portal['f1']
        wftool.doActionFor(f1, 'publish')

        # add nested document inside Unpublished Folder
        f2 = portal['f2']
        f2.invokeFactory('Document', 'nd2',
                title=u'Nested document 2')
        nd2 = f2['nd2']
        # publish it
        wftool.doActionFor(nd2, 'publish')

        # add nested document inside Document 1
        f1.invokeFactory('Document', 'nd1',
                title=u'Nested document 1')
        nd1 = f1['nd1']
        # publish it
        wftool.doActionFor(nd1, 'publish')
        # add nested file object
        f1.invokeFactory('File', 'file-1', title=u'File 1')
        portal.invokeFactory('Folder', 'f3', title=u'Don\'t deploy')
        f3 = portal['f3']
        wftool.doActionFor(f3, 'publish')
        # portal
        # - i1
        # - f1
        #   - nd1
        #   - file-1
        # - f2
        # - nd2
        # - f3
        logout()


    def testSetUp(self):
        """
        Creates temporary dir for deployment and loads test configuration.
        Executed before every test.
        """
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


    def testTearDown(self):
        """
        Removes temporary dir and config. Executed after every test.
        """
        shutil.rmtree(self['tmp_dir'])
        os.remove(self['test_conf_path'])




FIXTURE = StxStaticdeployLayer()
INTEGRATION_TESTING = IntegrationTesting(bases=(FIXTURE, ),
        name="StxStaticdeployLayer:Integration")
FUNCTIONAL_TESTING = FunctionalTesting(bases=(FIXTURE, ),
        name="StxStaticdeployLayer:Functional")
