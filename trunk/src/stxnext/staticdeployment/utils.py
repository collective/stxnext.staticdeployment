import logging
from ConfigParser import Error as ConfigParserError, ConfigParser as GenericConfigParser

DEFAULT_INI_SECTION = 'DEFAULT'

log = logging.getLogger(__name__)


class ConfigParser(GenericConfigParser):
    """
    Extended config parser.
    """

    def get_as_list(self, parameter, section=DEFAULT_INI_SECTION):
        try:
            raw_data = self.get(section, parameter).strip()
        except ConfigParserError:
            log.warning("Can not find param '%s', section '%s'." % (parameter, section))
            return []
        if not raw_data:
            return []
        return [i.strip() for i in raw_data.split('\n')]
