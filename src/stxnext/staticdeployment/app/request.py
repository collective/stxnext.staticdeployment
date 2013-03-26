import re

from Acquisition import aq_base
from ZPublisher.BaseRequest import RequestContainer
from logging import getLogger
from posixpath import normpath
from urlparse import urlsplit, urljoin
from urllib import unquote # Python2.4 does not have urlparse.unquote
from zope.globalrequest import getRequest, setRequest

# http://www.w3.org/Protocols/rfc2616/rfc2616-sec9.html
CONDITIONAL_HEADERS = [
    'HTTP_IF_MODIFIED_SINCE',
    'HTTP_IF_UNMODIFIED_SINCE',
    'HTTP_IF_MATCH',
    'HTTP_IF_NONE_MATCH',
    'HTTP_IF_RANGE',
    'HTTP_RANGE', # Not strictly a conditional header, but scrub it anyway
    ]

OTHER_IGNORE = set([
    'ACTUAL_URL',
    'LANGUAGE_TOOL',
    'PARENTS',
    'PARENT_REQUEST',
    'PUBLISHED',
    'SERVER_URL',
    'TraversalRequestNameStack',
    'URL',
    'VIRTUAL_URL',
    'VIRTUAL_URL_PARTS',
    'VirtualRootPhysicalPath',
    'method',
    'traverse_subpath',
    ])

OTHER_IGNORE_RE = re.compile(r'^(?:BASE|URL)\d+$')

logger = getLogger("plone.subrequest")


def fakeRequest(obj, root=None, stdout=None):
    """
    ripped out of plone.subrequest
    """
    try:
        url = obj.absolute_url()
    except AttributeError:
        url = obj.context.absolute_url()
    if isinstance(url, unicode):
        url = url.encode('utf-8')
    _, _, path, query, _ = urlsplit(url)
    parent_request = getRequest()
    assert parent_request is not None, "Unable to get request, perhaps zope.globalrequest is not configured."
    if path.startswith('/'):
        path = normpath(path)
        vurl_parts = parent_request.get('VIRTUAL_URL_PARTS')
        if vurl_parts is not None:
            # Use the virtual host root
            path_past_root = unquote(vurl_parts[-1])
            root_path = parent_request['PATH_INFO'][:-1-len(path_past_root)]
            if root is None:
                path = root_path + path
            else:
                path = '%s/%s%s' % (root_path, root.virtual_url_path(), path)
        elif root is not None:
            path = '/%s%s' % (root.virtual_url_path(), path)
    else:
        try:
            parent_url = parent_request['URL']
            if isinstance(parent_url, unicode):
                parent_url = parent_url.encode('utf-8')
            # extra is the hidden part of the url, e.g. a default view
            extra = unquote(parent_url[len(parent_request['ACTUAL_URL']):])
        except KeyError:
            extra = ''
        here = parent_request['PATH_INFO'] + extra
        path = urljoin(here, path)
        path = normpath(path)
    request = parent_request.clone()
    for name, parent_value in parent_request.other.items():
        if name in OTHER_IGNORE or OTHER_IGNORE_RE.match(name) or name.startswith('_'):
            continue
        request.other[name] = parent_value
    request['PARENT_REQUEST'] = parent_request
    request.other['URL'] = request.other['ACTUAL_URL'] = request.other['VIRTUAL_URL'] = url
    request.other['PUBLISHED'] = obj
    request.other['BASE1'] = parent_request.get('BASE1', '')
    request.other['SERVER_URL'] = parent_request.get('SERVER_URL', '')
    request.other['SERVER_PORT'] = parent_request.get('SERVER_PORT', '')

    try:
        setRequest(request)
        if hasattr(obj, 'aq_chain'):
            request['PARENTS'] = obj.aq_chain[:-1]
        environ = request.environ
        environ['PATH_INFO'] = path
        environ['QUERY_STRING'] = query
        # Clean up the request.
        for header in CONDITIONAL_HEADERS:
            environ.pop(header, None)
        # set headers...
        for key, val in parent_request.response.headers.items():
            request.response.headers[key] = val
    except:
        logger.exception("Error setting request %s" % url)
    return request, parent_request


def restoreRequest(original_request, new_request):
    new_request.clear()
    setRequest(original_request)
