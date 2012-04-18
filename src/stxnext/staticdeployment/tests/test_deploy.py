import unittest

from stxnext.staticdeployment.app.util import (RE_WO_1ST_DIRECTORY, RE_CSS_URL,
        RE_CSS_IMPORTS, RE_CSS_IMPORTS_HREF, RE_NOT_BINARY)



class TestRegexPatterns(unittest.TestCase):

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
        raise NotImplementedError()


    def test_re_css_imports_pattern(self):
        """
        Tests RE_CSS_IMPORTS pattern
        """
        raise NotImplementedError()


    def test_re_css_imports_href_pattern(self):
        """
        Tests RE_CSS_IMPORTS_HREF pattern
        """
        raise NotImplementedError()


    def test_not_binary_pattern(self):
        """
        Tests RE_NOT_BINARY pattern
        """
        raise NotImplementedError()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRegexPatterns))
    return suite
