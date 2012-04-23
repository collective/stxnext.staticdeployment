from ConfigParser import NoSectionError
import unittest

from zope.component import getUtility

from stxnext.staticdeployment.app.util import (RE_WO_1ST_DIRECTORY, RE_CSS_URL,
        RE_CSS_IMPORTS, RE_CSS_IMPORTS_HREF, RE_NOT_BINARY)
from stxnext.staticdeployment.interfaces import IStaticDeploymentUtils
from stxnext.staticdeployment.tests.base import INTEGRATION_TESTING

# http://www.w3.org/TR/CSS2/syndata.html#value-def-uri
CSS = """
@import url('/css/layout.css');

@import url(css/style.css);

@import url("styles/style.css");

body { background: url("yellow") }

div { background: url("http://www.example.com/pinkish.png") }

div.wrapper { background: url('pinkish.png') }

li { list-style: url(http://www.example.com/redball.png) disc }
"""

HTML = """
<style type="text/css">@import url('/css/layout.css');</style>
<style type="text/css">@import url(css/style.css);</style>
<style type="text/css" media="screen">@import url("styles/style.css");</style>


<link rel="stylesheet" type="text/css" href="/css/layout.css" />
<link rel="stylesheet" type="text/css" href="css/style.css" />
<link rel='stylesheet' type='text/css' href='styles/style.css' />
"""

CSS_IMPORTS = ['/css/layout.css', 'css/style.css', 'styles/style.css']

CSS_URLS = ['yellow', 'http://www.example.com/pinkish.png', 'pinkish.png',
    'http://www.example.com/redball.png']



class TestRegexPatterns(unittest.TestCase):
    """
    Tests regex patterns used in StaticDeploymentUtils
    """

    def test_re_wo_1st_directory_pattern(self):
        """
        Tests RE_WO_1ST_DIRECTORY pattern
        """
        path = 'first_dir/second_dir/some_file.txt'
        path_wo_1st_dir = 'second_dir/some_file.txt'

        #path without leading /
        match = RE_WO_1ST_DIRECTORY.match(path)
        self.assertTrue(match is not None)
        self.assertEqual(match.group(2), path_wo_1st_dir)

        #path with leading /
        path = '/' + path
        match = RE_WO_1ST_DIRECTORY.match(path)
        self.assertTrue(match is not None)
        self.assertEqual(match.group(2), path_wo_1st_dir)


    def test_re_css_url_pattern(self):
        """
        Tests RE_CSS_URL pattern
        """
        # will find all url() - including @import
        self.assertEqual(RE_CSS_URL.findall(CSS), CSS_IMPORTS + CSS_URLS)


    def test_re_css_imports_pattern(self):
        """
        Tests RE_CSS_IMPORTS pattern
        """
        # find @import inside CSS
        css_imports = RE_CSS_IMPORTS.findall(CSS)
        self.assertEqual(css_imports, CSS_IMPORTS)
        # find @import inside HTML
        html_css_imports = RE_CSS_IMPORTS.findall(HTML)
        self.assertEqual(html_css_imports, CSS_IMPORTS)


    def test_re_css_imports_href_pattern(self):
        """
        Tests RE_CSS_IMPORTS_HREF pattern
        """
        self.assertEqual(RE_CSS_IMPORTS_HREF.findall(HTML), CSS_IMPORTS)
        # will find nothing => [] => False
        self.assertFalse(RE_CSS_IMPORTS_HREF.findall(CSS))


    def test_not_binary_pattern(self):
        """
        Tests RE_NOT_BINARY pattern
        """
        # non-binary files (HTML, TXT, CSS)
        filename_1 = 'first_dir/second_dir/some_file.txt'
        self.assertTrue(RE_NOT_BINARY.search(filename_1) is not None)
        filename_2 = 'dir/some_file.css'
        self.assertTrue(RE_NOT_BINARY.search(filename_2) is not None)
        filename_3 = '/first_dir/some_file.html'
        self.assertTrue(RE_NOT_BINARY.search(filename_3) is not None)
        filename_4 = 'some_file.js'
        self.assertTrue(RE_NOT_BINARY.search(filename_4) is not None)
        # "binary" files
        filename_5 = 'first_dir/second_dir/some_file'
        self.assertTrue(RE_NOT_BINARY.search(filename_5) is None)
        filename_6 = 'some_file.tar'
        self.assertTrue(RE_NOT_BINARY.search(filename_6) is None)


class TestStaticDeploymentUtils(unittest.TestCase):

    layer = INTEGRATION_TESTING
    SECTION = 'PLONE'

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        self.sdutils = getUtility(IStaticDeploymentUtils)
        self.sdutils.request = self.request


    def test_read_config(self):
        """
        Tests StaticDeploymentUtils._read_config method
        """
        self.sdutils._read_config(self.SECTION)
        # is using temporary dir to deploy site?
        self.assertEqual(self.sdutils.deployment_directory,
                self.layer['tmp_dir'])


    def test_read_config_invalid_section(self):
        """
        Tests StaticDeploymentUtils._read_config with invalid section provided
        """
        self.assertRaises(NoSectionError, self.sdutils._read_config,
                'INVALID-SECTION')


    def test_available_for_anonymous(self):
        """
        Tests StaticDeploymentUtils._available_for_anonymous method
        """
        # object is published => avaialbe for anonymous user
        self.assertTrue(self.sdutils._available_for_anonymous(
            self.portal['f1']))
        # object is not published -> not avaialbe for anonymous user
        self.assertFalse(self.sdutils._available_for_anonymous(
            self.portal['f2']))
        # object is published but parent object isn't -> not avaialbe for
        # anonymous user
        self.assertFalse(self.sdutils._available_for_anonymous(
            self.portal['f2']['nd2']))



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRegexPatterns))
    suite.addTest(unittest.makeSuite(TestStaticDeploymentUtils))
    return suite
