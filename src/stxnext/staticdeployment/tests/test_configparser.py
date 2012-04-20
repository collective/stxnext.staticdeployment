from ConfigParser import NoOptionError, NoSectionError
import StringIO
import unittest

from stxnext.staticdeployment.utils import ConfigParser


SECTION = 'TEST-SECTION'
WRONG_SECTION = 'OTHER-SECTION'
INI = StringIO.StringIO("""[%s]
bool-option-t-1 = true
bool-option-t-2 = 1
bool-option-t-3 = yes
bool-option-t-4 = on
bool-option-f-1 = false
bool-option-f-2 = 0
bool-option-f-3 = no
bool-option-f-4 = off
wrong-bool-option = X
list-option-1 = 
    abc
    bcd
    cde
    def
list-option-2 =
    one-element
wrong-list-option = 
""" % SECTION)

LIST_VALUES = ['abc', 'bcd', 'cde', 'def']

class TestConfigParser(unittest.TestCase):
    """
    Test our ConfigParser features
    """
    def setUp(self):
        """
        Provide sample .ini file-like object
        """
        self.config = ConfigParser()
        INI.seek(0)
        self.config.readfp(INI)

    def test_bool_correct_formats(self):
        """
        Tests reading correct formats of boolean values
        """
        #true
        self.assertTrue(self.config.getboolean(SECTION, 'bool-option-t-1'))
        self.assertTrue(self.config.getboolean(SECTION, 'bool-option-t-2'))
        self.assertTrue(self.config.getboolean(SECTION, 'bool-option-t-3'))
        self.assertTrue(self.config.getboolean(SECTION, 'bool-option-t-4'))
        #false
        self.assertFalse(self.config.getboolean(SECTION, 'bool-option-f-1'))
        self.assertFalse(self.config.getboolean(SECTION, 'bool-option-f-2'))
        self.assertFalse(self.config.getboolean(SECTION, 'bool-option-f-3'))
        self.assertFalse(self.config.getboolean(SECTION, 'bool-option-f-4'))

    def test_bool_incorrect_format(self):
        """
        Tests if ConfigParser correctly raises ValueError when trying to read
        incorrect boolean value format
        """
        self.assertRaises(ValueError, self.config.getboolean, SECTION,
            'wrong-bool-option')

    def test_bool_nonexistiong_section(self):
        """
        Test if correct exceptions will be raised when trying to get bool
        option from nonexisting section
        """
        self.assertRaises(NoSectionError, self.config.getboolean, WRONG_SECTION,
                'bool-option')

    def test_existing_bool_with_default(self):
        """
        Tests if boolean values will be returned correctly when using default
        parameter
        """
        #true
        self.assertTrue(self.config.getboolean(SECTION, 'bool-option-t-1', True))
        self.assertTrue(self.config.getboolean(SECTION, 'bool-option-t-1', False))
        #false
        self.assertFalse(self.config.getboolean(SECTION, 'bool-option-f-1', True))
        self.assertFalse(self.config.getboolean(SECTION, 'bool-option-f-1', False))

    def test_existing_bool_without_default(self):
        """
        Tests if boolean values will be returned correctly whitout default
        parameter
        """
        #true
        self.assertTrue(self.config.getboolean(SECTION, 'bool-option-t-1'))
        self.assertTrue(self.config.getboolean(SECTION, 'bool-option-t-1'))
        #false
        self.assertFalse(self.config.getboolean(SECTION, 'bool-option-f-1'))
        self.assertFalse(self.config.getboolean(SECTION, 'bool-option-f-1'))

    def test_nonexisting_bool_with_default(self):
        """
        Tests if ConfigParser will return default value when trying to get
        nonexisting option when default value is provided
        """
        self.assertTrue(self.config.getboolean(SECTION, 'some-bool', True))
        self.assertFalse(self.config.getboolean(SECTION, 'some-bool', False))

    def test_nonexisting_bool_without_default(self):
        """
        Tests if ConfigParser will raise an exception when trying to get
        nonexisting option without providing default value
        """
        self.assertRaises(NoOptionError, self.config.getboolean, SECTION, 'some-bool')

    def test_list_with_correct_section_provided(self):
        """
        Test if ConfigParser.get_as_list will return correct values when
        section will be passed as argument
        """
        self.assertEqual(self.config.get_as_list('list-option-1',
            section=SECTION), LIST_VALUES)

    def test_list_with_incorrect_section_provided(self):
        """
        Test if ConfigParser.get_as_list will return empty list (False) when
        trying to get option from incorrect section
        """
        self.assertFalse(self.config.get_as_list('list-option-1',
            section=WRONG_SECTION))

    def test_list_with_one_value(self):
        """
        Test if ConfigParser.get_as_list will return list with one element
        correctly
        """
        self.assertEqual(self.config.get_as_list('list-option-2',
            section=SECTION), ['one-element'])


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestConfigParser))
    return suite
