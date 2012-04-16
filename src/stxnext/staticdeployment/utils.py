import os, logging
from ConfigParser import Error as ConfigParserError, ConfigParser as GenericConfigParser

DEFAULT_INI_SECTION = 'DEFAULT'

log = logging.getLogger(__name__)

def get_config_path():
    """
    Returns the path to the configuration file.
    If not overriden in localization ${buildout:directory}/etc/staticdeployment.ini,
    the path to the default stxntext.staticdeployment module's configuration file is returned:
    ${buildout:directory}/eggs/stxnext.staticdeployment/stxnext/staticdeployment/etc/staticdeployment.ini
    """
    config_path = os.path.join(CLIENT_HOME, '..', '..', 'etc', 'staticdeployment.ini')
    if not os.path.isfile(config_path):
        config_path = os.path.join(os.path.dirname(__file__), 'etc', 'staticdeployment.ini')
    return config_path


class ConfigParser(GenericConfigParser):
    """
    Extended config parser.
    """

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
