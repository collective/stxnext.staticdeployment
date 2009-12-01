# -*- coding: utf-8 -*-
import os, re, logging
from ConfigParser import ParsingError
from BeautifulSoup import BeautifulSoup
from DateTime import DateTime
from urllib import unquote
from HTMLParser import HTMLParseError
from urlparse import urlsplit

from OFS.Image import Pdata, Image as OFSImage
from Products.Archetypes.Field import Image as ImageField
from Products.ATContentTypes.content.image import ATImage
from Products.ATContentTypes.content.file import ATFile
from Products.Archetypes.interfaces import IBaseObject
from Products.CMFCore.FSDTMLMethod import FSDTMLMethod
from Products.CMFCore.FSFile import FSFile
from Products.CMFCore.FSImage import FSImage
from Products.CMFCore.FSPageTemplate import FSPageTemplate
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone import PloneMessageFactory as _
from Products.CMFPlone.Portal import PloneSite
from Products.Five import BrowserView
from Products.PythonScripts.PythonScript import PythonScript
from Products.statusmessages.message import Message

from plone.i18n.normalizer.interfaces import IUserPreferredURLNormalizer
from zope.component import getMultiAdapter, queryMultiAdapter, getAdapters
from zope.component.interfaces import IResource
from zope.interface import Interface
from zope.contentprovider.interfaces import ContentProviderLookupError
from zope.publisher.interfaces import NotFound

from stxnext.staticdeployment.browser.preferences.staticdeployment import IStaticDeploymentSettings
from stxnext.staticdeployment.interfaces import ITransformation, IDeploymentStep
from stxnext.staticdeployment.utils import ConfigParser

log = logging.getLogger(__name__)


RE_WO_1ST_DIRECTORY = re.compile(r'^[^/]+?[/](.*)$')
RE_CSS_URL = re.compile(r"""url\(["']?([^\)'"]+)['"]?\)""")
RE_NOT_BINARY = re.compile(r'\.css$|\.js$|\.txt$|\.html$')


def _makedirs(path):
    try:
        os.makedirs(os.path.normpath(path))
    except OSError:
        return False
    return True


class StaticDeploymentView(BrowserView):
    """
    View for static deployment.
    """
    def __init__(self, context, request):
        super(StaticDeploymentView, self).__init__(context, request)
        self._read_config()
        settings = IStaticDeploymentSettings(context)
        self.base_dir = os.path.normpath(settings.deployment_directory)
        self.frontend_domain = self.request['BASE1']
        if settings.backend_domain.startswith('http'):
            self.backend_domain = settings.backend_domain + '/'
        else:
            self.backend_domain = 'http://%s/' % settings.backend_domain
        self.deployed_resources = []

    def _read_config(self):
        """
        Read config from .ini file.
        """
        config_path = os.path.join(CLIENT_HOME, '..', '..', 'etc', 'staticdeployment.ini')
        if not os.path.isfile(config_path):
            config_path = os.path.join(os.path.dirname(__file__), '..', 'etc', 'staticdeployment.ini')

        config_file = open(config_path, 'r')
        self.config = ConfigParser()
        try:
            self.config.readfp(config_file)
        except ParsingError, e:
            log.exception("Error when trying to parse '%s'" % config_path)
            return

        self.page_types = self.config.get_as_list('page-types')
        self.file_types = self.config.get_as_list('file-types')
        self.skinstool_files = self.config.get_as_list('skinstool-files')
        self.additional_files = self.config.get_as_list('additional-files')
        self.additional_pages = self.config.get_as_list('additional-pages')

    def _apply_transforms(self, html):
        """
        Apply transforms to output html.
        """
        transformations = getAdapters((self.context,), ITransformation)

        for t_name, t in transformations:
            html = t(html)
        return html

    def update(self):
        """
        Update action.
        """
        settings = IStaticDeploymentSettings(self.context)

        last_triggered = settings.last_triggered
        if not last_triggered:
            return self.full()
        try:
            last_triggered_date = DateTime(last_triggered)
            if last_triggered_date.isFuture():
                raise DateTime.DateError
        except (SyntaxError, DateTime.DateError):
            msg = Message(_(u'Last triggered date is in wrong format!'), type='error')
            msg = msg.encode().encode('base64').strip()
            return self.request.response.redirect(self.backend_domain + "@@staticdeployment-controlpanel?msg=" + msg)

        return self.full(last_triggered_date)

    def full(self, modification_date=None):
        """
        Deploy whole site as static content.
        """
        ## turn off debug mode, but remember state first
        css_tool = getToolByName(self.context, 'portal_css')
        js_tool = getToolByName(self.context, 'portal_javascripts')
        initial_debugmode = css_tool.getDebugMode(), js_tool.getDebugMode()

        if initial_debugmode[0]: css_tool.setDebugMode(False)
        if initial_debugmode[1]: js_tool.setDebugMode(False)

        self._deploy_registry_files('portal_css', 'styles')
        self._deploy_registry_files('portal_javascripts', 'scripts')
        self._deploy_skinstool_files(self.skinstool_files)
        self._deploy_views(self.additional_files, is_page=False)
        self._deploy_views(self.additional_pages, is_page=True)

        ## Deploy Plone Site
        self._deploy_site(self.context)

        ## Deploy folders and pages
        catalog = getToolByName(self.context, 'portal_catalog')
        brains = catalog(meta_type=self.page_types, modified={'query':[modification_date], 'range':'min'})
        for brain in brains:
            obj = brain.getObject()
            self._deploy_content(obj, is_page=True)

        brains = catalog(meta_type=self.file_types, modified={'query':[modification_date], 'range':'min'})
        for brain in brains:
            obj = brain.getObject()
            self._deploy_content(obj, is_page=False)

        ## find and run additional deployment steps
        steps = getAdapters((self.context,), IDeploymentStep)
        for step_name, step in steps:
            step.update(self, modification_date)
            step()

        settings = IStaticDeploymentSettings(self.context)
        settings.last_triggered = unicode(DateTime().strftime('%Y/%m/%d %H:%M:%S'))

        ## turn debug mode to initial state
        if initial_debugmode[0]: css_tool.setDebugMode(True)
        if initial_debugmode[1]: js_tool.setDebugMode(True)

        ## lets return to backend
        msg = Message(_(u'Deployment finished!'), type='info')
        msg = msg.encode().encode('base64').strip()
        return self.request.response.redirect(self.backend_domain + "@@staticdeployment-controlpanel?msg=" + msg)

    def _deploy_registry_files(self, registry_type, resource_type):
        """
        Deploy registered resources.
        """
        registry_view = getMultiAdapter((self.context, self.request), name='resourceregistries_%s_view' % resource_type)
        registry = registry_view.registry()
        resources = getattr(registry_view, resource_type)()

        for resource in resources:
            if not resource['src'].startswith(self.frontend_domain):
                continue

            filename = resource['src'].replace(self.frontend_domain, '')
            try:
                content = registry.getResourceContent(os.path.basename(filename), self.context)
            except TypeError:
                log.exception("File '%s' not found when deploying '%s'!" % (filename, registry_type))
                continue

            self._write(filename, content)

    def _deploy_skinstool_files(self, files):
        """
        Deploy files from portal_skins but not registered in portal_css or portal_js.
        """
        skins_tool = getToolByName(self.context, 'portal_skins')

        for fs_file_path in files:
            fs_file = skins_tool.getSkinByPath(fs_file_path)
            if not fs_file:
                log.warning("File '%s' not found in portal_skins!" % fs_file_path)
                continue

            filename = fs_file_path
            match = RE_WO_1ST_DIRECTORY.match(filename)
            if match:
                filename = match.group(1)

            content = fs_file._readFile(None)
            self._write(filename, content)

    def _deploy_views(self, views, is_page=False):
        """
        Deploy views of context as pages.
        """
        for fullview_name in views:
            
            fullview_path = None
            fullview_name_args = fullview_name.split('|')
            if len(fullview_name_args) > 1:
                fullview_name = fullview_name_args[0]
                fullview_path = fullview_name_args[1]
            
            context = self.context
            context_path = os.path.dirname(fullview_name)
            view_name = os.path.basename(fullview_name)
            if context_path:
                context = self.context.restrictedTraverse(context_path, None)
                if not context:
                    log.warning("Unable traverse to '%s'!" % context_path)
                    continue

            content_obj = context.restrictedTraverse(view_name, None)
            content = self._render_obj(content_obj)
            if content is None:
                continue

            filename = fullview_name
            if is_page:
                filename = os.path.join(filename, 'index.html')

            self._write(filename, content, fullview_path)

    def _render_obj(self, obj):
        """
        Render object to string.
        """
        if isinstance(obj, basestring):
            return obj

        ## 'plone.global_sections' viewlet uses request['URL'] highlight
        ## selected tab, so it must be overridden but only for a while
        initial_url = self.request['URL']
        try:
            obj_url = obj.absolute_url()
        except AttributeError:
            try:
                obj_url = obj.context.absolute_url()
            except AttributeError:
                obj_url = None

        if obj_url:
            self.request['URL'] = obj_url

        ## breadcrumb implementation in quills uses 'PARENTS', so it must
        ## be overriden but ony for a while 
        initial_parents = self.request['PARENTS']
        self.request['PARENTS'] = obj.aq_chain

        try:
            if IResource.providedBy(obj):
                try:
                    f = open(obj.context.path)
                    result = f.read()
                    f.close()
                except IOError:
                    log.error("Couldn't open '%s' file with resource" % obj.context.path)
                    return None

                return result

            if isinstance(obj, (BrowserView, FSPageTemplate, PythonScript)):
                try:
                    return obj()
                except NotFound:
                    log.error("Resource '%s' not found" % repr(obj))
                    return None

            if isinstance(obj, (FSFile, FSImage)):
                return self._render_obj(obj._readFile(None))

            if isinstance(obj, FSDTMLMethod):
                return self._render_obj(obj.read())

            mt = None
            try:
                mt = obj.aq_base.meta_type
            except AttributeError:
                pass

            if mt in self.file_types or isinstance(obj, (ImageField, OFSImage, Pdata)):
                return self._render_obj(obj.data)

            if IBaseObject.providedBy(obj) or isinstance(obj, PloneSite):
                def_page_id = obj.getDefaultPage()
                if def_page_id:
                    def_page = obj[def_page_id]
                    return self._render_obj(def_page)

                view_name = obj.getLayout()
                view = queryMultiAdapter((obj, self.request), name=view_name)
                if view:
                    try:
                        return view()
                    except ContentProviderLookupError:
                        pass

                view = obj.restrictedTraverse(view_name, None)
                if view:
                    return view()

                try:
                    return obj()
                except AttributeError:
                    pass

        finally:
            ## back to initial url
            if obj_url:
                self.request['URL'] = initial_url

            ## back to initial parents
            self.request['PARENTS'] = initial_parents

        log.warning("Not recognized object '%s'!" % repr(obj))
        return None

    def _deploy_site(self, obj):
        """
        Deploy object as page.
        """
        content = self._render_obj(obj)
        if content is None:
            return

        self._write('index.html', content)

    def _deploy_content(self, obj, is_page=True):
        """
        Deploy object as page.
        """
        content = self._render_obj(obj)
        if content is None:
            return

        filename = obj.absolute_url_path().lstrip('/')
        if is_page:
            filename = os.path.join(filename, 'index.html')

        self._write(filename, content)
        
        # deploy all sizes of images uploaded for the object
        if not getattr(obj, 'schema', None):
            return
         
        for field in obj.schema.fields():
            if field.type != 'image':
                continue
            sizes = field.getAvailableSizes(field)
            for scalename in sizes.keys():
                image =  field.getScale(obj, scale=scalename)
                if image:
                    filename = image.getId()
                    dir_path = obj.absolute_url_path().lstrip('/')
                    file_path = os.path.join(dir_path, filename)
                    content = self._render_obj(image)
                    if content:
                        self._write(file_path, content)

    def _deploy_resources(self, urls, base_path):
        """
        Deploy resources linked in HTML or CSS.
        """
        base_path = base_path
        for url in urls:
            url = url.strip()
            scheme, netloc, path, query, fragment = urlsplit(url)
            if not path:
                ## internal anchor
                continue

            if netloc and netloc != self.frontend_domain:
                ## external link
                continue

            if path.startswith('/'):
                objpath = path[1:]
            else:
                objpath = os.path.join(base_path, path)

            if isinstance(objpath, unicode):
                objpath = objpath.encode('utf-8')

            if objpath in self.deployed_resources:
                continue

            obj = self.context.restrictedTraverse(objpath, None)
            if not obj:
                log.warning("Unable to deploy resource '%s'!" % objpath)
                continue

            content = self._render_obj(obj)
            if content is None:
                continue

            self._write(objpath, content)

            self.deployed_resources.append(objpath)

    def _parse_html(self, html, base_path=''):
        """
        Save all resources used in HTML file.
        """
        try:
            soup = BeautifulSoup(html)
        except HTMLParseError:
            return

        urls = [tag['src'] for tag in soup.findAll(['img', 'input', 'embed'], src=True)]
        self._deploy_resources(urls, unquote(base_path))

    def _parse_css(self, content, base_path=''):
        """
        Save all resources used in CSS file.
        """
        self._deploy_resources(RE_CSS_URL.findall(content), unquote(base_path))

    def _write(self, filename, content, dir_path=None):
        """
        Write content to file.
        """
        filename = filename.lstrip('/')

        if not content:
            log.warning("File '%s' is empty." % filename)

        if dir_path is None:
            dir_path = self.base_dir

        file_path = os.path.join(dir_path, filename)
        file_path = unquote(file_path)
        _makedirs(os.path.dirname(file_path))

        try:
            content_file = open(file_path, "w")
        except IOError:
            log.exception("Error trying to dump data to '%s' file!" % filename)
            return

        if RE_NOT_BINARY.search(filename):
            content = self._apply_transforms(content)

        try:
            content_file.write(content)
        finally:
            content_file.close()

        log.debug("[*] '%s' saved." % filename)

        if filename.endswith('.css'):
            self._parse_css(content, os.path.dirname(filename))

        if filename.endswith('.html'):
            self._parse_html(content, os.path.dirname(filename))
