import os, logging
from posixpath import curdir, sep, pardir, join, abspath, commonprefix
from ConfigParser import (Error as ConfigParserError,
        ConfigParser as GenericConfigParser, NoOptionError)

DEFAULT_INI_SECTION = 'DEFAULT'

log = logging.getLogger(__name__)

def get_config_path():
    """
    Returns the path to the configuration file.
    If not overriden in localization ${buildout:directory}/etc/staticdeployment.ini,
    the path to the default stxntext.staticdeployment module's configuration file is returned:
    ${buildout:directory}/eggs/stxnext.staticdeployment/stxnext/staticdeployment/etc/staticdeployment.ini
    """
    #CLIENT_HOME will be populated by Plone
    config_path = os.path.join(CLIENT_HOME, '..', '..', 'etc', 'staticdeployment.ini')
    if not os.path.isfile(config_path):
        config_path = os.path.join(os.path.dirname(__file__), 'etc', 'staticdeployment.ini')
    return config_path

def relpath(path, start=curdir):
    """Return a relative version of a path"""
    if not path:
        raise ValueError("no path specified")
    start_list = abspath(start).split(sep)
    path_list = abspath(path).split(sep)
    # Work out how much of the filepath is shared by start and path.
    i = len(commonprefix([start_list, path_list]))
    rel_list = [pardir] * (len(start_list)-i) + path_list[i:]
    if not rel_list:
        return curdir
    return join(*rel_list)

def reset_request(fn):
    """
    Decorator function for resetting the request variables
    that may be added in the rendered templates
    """
    def wrapped(*args, **kwargs):
        req = args[0].request
        req['disable_plone.leftcolumn'] = None
        req['disable_plone.rightcolumn'] = None
        return fn(*args, **kwargs)
    return wrapped


class ConfigParser(GenericConfigParser):
    """
    Extended config parser.
    """
    def getboolean(self, section, parameter, default=None):
        """
        Patched ConfigParser.getboolean - returns 'default' if provided,
        otherwise raises NoOptionError
        """
        try:
            #ConfigParser is an old-style class
            return GenericConfigParser.getboolean(self, section, parameter)
        except NoOptionError:
            if default is not None:
                return default
            else:
                raise

    def get_as_list(self, parameter, section=DEFAULT_INI_SECTION):
        """
        Returns parameter values (one per line) as a list
        """
        try:
            raw_data = self.get(section, parameter).strip()
        except ConfigParserError:
            log.warning("Can not find param '%s', section '%s'." % (parameter, section))
            return []
        if not raw_data:
            return []
        return [i.strip() for i in raw_data.split('\n')]
