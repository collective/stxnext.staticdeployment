# -*- coding: utf-8 -*-
import os, re, logging, inspect, traceback
from inspect import ismethod, isfunction
from AccessControl.PermissionRole import rolesForPermissionOn
from AccessControl.SecurityManagement import noSecurityManager
from ConfigParser import ParsingError, NoOptionError
from BeautifulSoup import BeautifulSoup
from DateTime import DateTime
from urllib import unquote
from HTMLParser import HTMLParseError
from urlparse import urlsplit, urlparse

from zope.component import getMultiAdapter, queryMultiAdapter, getAdapters
from zope.component.interfaces import ComponentLookupError
try:
    from zope.app.publisher.interfaces import IResource
except ImportError:
    from zope.component.interfaces import IResource
from zope.contentprovider.interfaces import ContentProviderLookupError
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.publisher.browser import applySkin
from OFS.Image import Pdata, File, Image as OFSImage

try:
    from plone.app.blob.content import ATBlob
    from plone.app.blob.interfaces import IBlobImageField, IBlobField, IBlobWrapper
    PLONE_APP_BLOB_INSTALLED = True
except:
    PLONE_APP_BLOB_INSTALLED = False

from Products.Archetypes.Field import Image as ImageField
from Products.ATContentTypes.content.image import ATImage
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
from Products.statusmessages.interfaces import IStatusMessage

from stxnext.staticdeployment.browser.preferences.staticdeployment import IStaticDeployment
from stxnext.staticdeployment.interfaces import ITransformation, IDeploymentStep, IExtraDeploymentCondition, \
    IPostTransformation, IImageTransformation
from stxnext.staticdeployment.utils import ConfigParser, get_config_path, reset_request


try:
    from plone.resource.file import FilesystemFile
    PLONE_RESOURCE_INSTALLED = True
except ImportError:
    PLONE_RESOURCE_INSTALLED = False

try:
    from plone.resource.interfaces import IResourceDirectory
except:
    from zope.interface import Interface as IResourceDirectory


log = logging.getLogger(__name__)

# gets path without first directory - used in
# SecurityManagement._deploy_skinstool_files
RE_WO_1ST_DIRECTORY = re.compile(r'^(/)?[^/]+?[/](.*)$')
# gets all url() CSS directives
RE_CSS_URL = re.compile(r"""url\(["']?([^\)'"]+)['"]?\)""")
# finds css imports (assumes that '.css' inside url() means @import)
RE_CSS_IMPORTS = re.compile(r"(?<=url\()[\"\']?([a-zA-Z0-9\+\.\-\/\:\_]+\.(?:css))")
# finds css imports in html (<link />)
RE_CSS_IMPORTS_HREF = re.compile(r"(?<=href\=[\'\"])[a-zA-Z0-9\+\.\-\/\:\_]+\.(?:css)")
# matches non-binary files (CSS, JS, TXT, HTML)
RE_NOT_BINARY = re.compile(r'\.css$|\.js$|\.txt$|\.html$')


def _makedirs(path):
    try:
        os.makedirs(os.path.normpath(path))
    except OSError:
        return False
    return True


class StaticDeploymentUtils(object):
    """
    View for static deployment.
    """

    def _apply_request_modifications(self):
        """
        Apply proper skin name and five skinlayer.
        """
        skins_tool = getToolByName(self.context, 'portal_skins')
        request_varname = skins_tool.request_varname

        layer_interface_path = self.layer_interface.split('.')
        layer_interface_module = __import__('.'.join(layer_interface_path[:-1]), {}, {}, layer_interface_path[-1])
        applySkin(self.request, getattr(layer_interface_module, layer_interface_path[-1], None))
        self.context.changeSkin(self.defaultskin_name, self.request)
        self.request.set(request_varname, self.defaultskin_name)
        self.request.method = 'GET'
        self.request.set('PUBLISHED', None)
        
        self.base_dir = os.path.normpath(self.deployment_directory)
        self.deployed_resources = []


    def revert_request_modifications(self, context, request):
        """
        Apply plone default skin name and five skinlayer.
        """
        skins_tool = getToolByName(context, 'portal_skins')
        request_varname = skins_tool.request_varname
        applySkin(request, IDefaultBrowserLayer)
        context.changeSkin(None, request)
        request.set(request_varname, None)


    def _read_config(self, section):
        """
        Read config from .ini file.
        """
        # get path to config file and read it
        config_path = os.path.normpath(get_config_path())
        config_file = open(config_path, 'r')
        # parse file in ConfigParser
        self.config = ConfigParser()
        try:
            self.config.readfp(config_file)
        except ParsingError, e:
            log.exception("Error when trying to parse '%s'" % config_path)
            return
        # non required params
        # list-like params
        self.page_types = self.config.get_as_list('page-types', section=section)
        self.file_types = self.config.get_as_list('file-types', section=section)
        self.skinstool_files = self.config.get_as_list('skinstool-files', section=section)
        self.additional_files = self.config.get_as_list('additional-files', section=section)
        self.additional_pages = self.config.get_as_list('additional-pages', section=section)
        self.deployment_steps = self.config.get_as_list('deployment-steps', section=section)
        self.additional_directories = self.config.get_as_list('additional-directories', section=section)
        # params with default values
        # boolean params
        self.relative_links = self.config.getboolean(section,
                'make-links-relative', False)
        self.add_index = self.config.getboolean(section, 'add-index', False)
        self.deploy_plonesite = self.config.getboolean(section,
                'deploy-plonesite', True)
        self.deploy_registry_files = self.config.getboolean(section,
                'deploy-registry-files', True)
        # list param
        self.deployable_review_states = self.config.get_as_list('deployable-review-states', section=section)
        if not self.deployable_review_states:
            self.deployable_review_states = ['published']
        # required params
        try:
            self.deployment_directory = self.config.get(section, 'deployment-directory').strip()
            self.layer_interface = self.config.get(section, 'layer-interface').strip()
            self.defaultskin_name = self.config.get(section, 'defaultskin-name').strip()
        except NoOptionError, e:
            messages = IStatusMessage(self.request)
            messages.addStatusMessage(_(e.message), type='error')
            raise e


    def _apply_transforms(self, html):
        """
        Apply transforms to output html.
        """
        #get all registered "standard" transformations
        transformations = getAdapters((self.context, ), ITransformation)

        for t_name, t in transformations:
            log.debug('Processing %s transformation' % t_name)
            html = t(html)
        return html


    def _apply_post_transforms(self, html, file_path=None):
        """
        Apply post transforms to output html.
        """
        #get all registered "late/post" transformations
        transformations = getAdapters((self.context,), IPostTransformation)

        for t_name, t in transformations:
            # Condition added to keep compatibility with
            # existing transformations after the change in API
            log.debug('Processing %s post-transformation' % t_name)
            try:
                if len(inspect.getargspec(t.__call__)[0]) == 3:
                    html = t(html, file_path)
                else:
                    html = t(html)
            except:
                if not file_path:
                    file_path = ''
                log.error('error in %s post-transformation(%s)\n%s' % (
                    t_name, file_path, traceback.format_exc()
                    ))
        return html


    def _apply_image_transforms(self, filename, image):
        """
        Apply transforms to output image.
        """
        #get all registered image transformations
        transformations = getAdapters((self.context,), IImageTransformation)

        for t_name, t in transformations:
            log.debug('Processing %s image transformation for %s' % (t_name,
                filename))
            filename, image = t(filename, image)
        return filename, image


    def _parse_date(self, last_triggered):
        """
        Parse modification date passed in request.
        """
        if not last_triggered:
            return None
        try:
            last_triggered_date = DateTime(last_triggered)
            if last_triggered_date.isFuture():
                raise DateTime.DateError
        except (SyntaxError, DateTime.DateError), e:
            messages = IStatusMessage(self.request)
            message = _(u'Wrong format of last static deployment date.')
            messages.addStatusMessage(message, type='error')
            raise e

        return last_triggered_date


    def initial_resources_tools_mode(self, context):
        """
        Set debug mode for css and js tools and returns initial values
        """
        css_tool = getToolByName(context, 'portal_css')
        js_tool = getToolByName(context, 'portal_javascripts')
        kss_tool = getToolByName(context, 'portal_kss')
        initial_debugmode = (css_tool.getDebugMode(), js_tool.getDebugMode(),
                kss_tool.getDebugMode())
        #if DebugMode was enabled, disable it
        if initial_debugmode[0]: css_tool.setDebugMode(False)
        if initial_debugmode[1]: js_tool.setDebugMode(False)
        if initial_debugmode[2]: kss_tool.setDebugMode(False)
        return initial_debugmode


    def revert_resources_tools_mode(self, context,
            initial_debugmode=(True, True, True)):
        """
        Set initial mode for css and js tools.
        """
        css_tool = getToolByName(context, 'portal_css')
        js_tool = getToolByName(context, 'portal_javascripts')
        kss_tool = getToolByName(context, 'portal_kss')
        # if DebugMode was enabled for resource, enable it
        if initial_debugmode[0]: css_tool.setDebugMode(True)
        if initial_debugmode[1]: js_tool.setDebugMode(True)
        if initial_debugmode[2]: kss_tool.setDebugMode(True)


    @staticmethod
    def _available_for_anonymous(obj):
        """
        Checks if object is available for anonymous users
        """
        chain = obj.aq_chain
        # is object and its parents are available for anonymous?
        for subobj in chain:
            if IBaseObject.providedBy(subobj) or isinstance(subobj, PloneSite):
                if not 'Anonymous' in rolesForPermissionOn('View', subobj):
                    return False
        return True


    def _extra_deployment_conditions_passed(self, obj, modification_date):
        """
        Checks if object passed extra deployment conditions
        """
        extra_dep_conds = getAdapters((self.context, ), IExtraDeploymentCondition)
        for cond_name, condition in extra_dep_conds:
            condition.update(self, modification_date)
            if not condition(obj):
                return False
        return True


    def _applay_extra_deployment_steps(self, modification_date):
        """
        Applays extra deployment steps
        """
        steps = getAdapters((self.context,), IDeploymentStep)
        for step_name, step in steps:
            if step_name in self.deployment_steps:
                # update step's vars
                step.update(self, modification_date)
                log.debug('Calling additional deployment step: %s' % step_name)
                # call it
                step()


    def deploy(self, context, request, section, last_triggered=None):
        """
        Deploy whole site as static content.
        """
        # get content for Anonymous users, not authenticated
        noSecurityManager()
        # assigning values
        self.context = context
        self.request = request
        self.section = section

        self._read_config(section)
        self._apply_request_modifications()

        # when last deployment took place
        modification_date = self._parse_date(last_triggered)

        ## Deploy registry files
        if self.deploy_registry_files:
            self._deploy_registry_files('portal_css', 'styles', 'styles')
            self._deploy_registry_files('portal_javascripts', 'scripts', 'scripts')
            self._deploy_registry_files('portal_kss', 'kss', 'kineticstylesheets')

        # Deploy plone_skins files (if any)
        self._deploy_skinstool_files(self.skinstool_files)
        # Deploy additional files and pages
        self._deploy_views(self.additional_files, is_page=False)
        self._deploy_views(self.additional_pages, is_page=True)

        ## Deploy Plone Site
        if self.deploy_plonesite:
            self._deploy_site(self.context)

        ## Deploy folders and pages
        catalog = getToolByName(self.context, 'portal_catalog')
        brains = catalog(meta_type=self.page_types + self.file_types,
                         modified={'query': [modification_date, ], 'range': 'min'},
                         effectiveRange = DateTime(),
                         )
        for brain in brains:
            if not brain.review_state or brain.review_state in self.deployable_review_states:
                obj = brain.getObject()
                # we want only objects available for anonyous users 
                if not self._available_for_anonymous(obj):
                    continue
                # check extra deployment conditions
                if not self._extra_deployment_conditions_passed(obj,
                        modification_date):
                    continue
                # check if object is a normal page
                is_page = brain.meta_type in self.page_types
                try:
                    self._deploy_content(obj, is_page=is_page)
                except:
                    log.error("error exporting object: %s\n%s" % (
                        '/'.join(obj.getPhysicalPath()),
                        traceback.format_exc())
                    )

        ## find and run additional deployment steps
        self._applay_extra_deployment_steps(modification_date)
        # update last triggered date info
        settings = IStaticDeployment(self.context)
        settings.last_triggered = unicode(DateTime().strftime('%Y/%m/%d %H:%M:%S'))


    def _deploy_registry_files(self, registry_type, resource_name, resource_type):
        """
        Deploy registered resources.
        """
        registry_view = getMultiAdapter((self.context, self.request), name='resourceregistries_%s_view' % resource_name)
        registry = registry_view.registry()
        resources = getattr(registry_view, resource_type)()
        for resource in resources:
            filename = urlparse(resource['src'])[2]
            try:
                content = registry.getResourceContent(os.path.basename(filename), self.context)
            except TypeError:
                log.exception("File '%s' not found when deploying '%s'!" % (filename, registry_type))
                continue
            # so html isn't added...
            self._write(filename, content, omit_transform=True)


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
                filename = match.group(2)

            content = fs_file._readFile(None)

            path = urlparse(self.context.portal_url())[2]
            filename = '/'.join((path, filename))

            if isinstance(fs_file, FSImage):
                filename, content = self._apply_image_transforms(filename, content)
            self._write(filename, content)

    @reset_request
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

            # plone.resource file system resource
            if IResourceDirectory.providedBy(context):
                content_obj = context[view_name]
            else:
                content_obj = context.restrictedTraverse(view_name, None)

            # get object's view content 
            if ismethod(content_obj) or isfunction(content_obj):
                view = queryMultiAdapter((context, self.request), name=view_name)
                content_obj = view.context()
            content = self._render_obj(content_obj)
            if content is None:
                continue

            filename = fullview_name
            if is_page:
                filename = os.path.join(filename, 'index.html')
            # where to write view content (based on view path)
            path = urlparse(self.context.portal_url())[2]
            filename = '/'.join((path, filename))
            # write view content on the disk
            self._write(filename, content, fullview_path)


    @reset_request
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
        if hasattr(obj, 'aq_chain'):
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

            if mt in self.file_types or isinstance(obj, (ImageField, OFSImage, Pdata, File)):
                return self._render_obj(obj.data)

            if PLONE_RESOURCE_INSTALLED and isinstance(obj, FilesystemFile):
                if not obj.request:
                    obj.request = self.request
                    return obj().read()

            if PLONE_APP_BLOB_INSTALLED and IBlobWrapper.providedBy(obj):
                return obj.data

            if IBaseObject.providedBy(obj) or isinstance(obj, PloneSite):
                def_page_id = obj.getDefaultPage()
                if def_page_id:
                    def_page = obj[def_page_id]
                    return self._render_obj(def_page)

                view_name = obj.getLayout()
                view = queryMultiAdapter((obj, self.request), name=view_name)
                if view_name == 'language-switcher':
                    lang = self.request.get('LANGUAGE')
                    def_page = getattr(obj, lang, None)
                    if def_page:
                        return self._render_obj(def_page)
                if view:
                    try:
                        return view.context()
                    except (ContentProviderLookupError, TypeError):
                        pass

                view = obj.restrictedTraverse(view_name, None)
                if view:
                    try:
                        return view.context()
                    except (AttributeError, TypeError):
                        try:
                            return view()
                        except Exception, error:
                            log.warning("Unable to render view: '%s'! Error occurred: %s" % (view, error))
                            pass

                else:
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

        path = urlparse(self.context.portal_url())[2]
        self._write('/'.join((path, 'index.html')), content)


    def _deploy_blob_image_field(self, obj, field):
        """
        Deploys Blob Image field
        """
        sizes = field.getAvailableSizes(field)
        scalenames = sizes.keys()
        scalenames.append(None)
        for scalename in scalenames:
            image = field.getScale(obj, scale=scalename)
            if image:
                #store original image
                if scalename is None:
                    filename = image.filename
                    image = image.data
                else:
                    filename = image.getId()
                dir_path = obj.absolute_url_path().lstrip('/')
                if filename.rsplit('.', 1)[-1] in ('png', 'jpg', 'gif', 'jpeg'):
                    objpath = os.path.join(filename, 'image.%s' %
                            filename.rsplit('.', 1)[-1])
                else:
                    objpath = os.path.join(filename, 'image.jpg')

                file_path = os.path.join(dir_path, objpath)
                content = self._render_obj(image)
                if content:
                    file_path, content = self._apply_image_transforms(file_path, content)
                    self._write(file_path, content)
                    # add as already deployed resource to avoid
                    # redeployment in _deploy_resources
                    self.deployed_resources.append(file_path)


    def _deploy_blob_file_field(self, obj, field):
        """
        Deploys Blob File field
        """
        file_instance = field.getAccessor(obj)()
        if file_instance:
            filename = field.getName()
            dir_path = obj.absolute_url_path().lstrip('/')
            file_path = os.path.join(dir_path, 'at_download', filename)
            if hasattr(file_instance, 'data'):
                content = self._render_obj(str(file_instance.data))
                if content:
                    self._write(file_path, content)


    def _deploy_image_field(self, obj, field):
        """
        Deploys normal Image field
        """
        sizes = field.getAvailableSizes(field)
        scalenames = sizes.keys()
        scalenames.append(None)
        for scalename in scalenames:
            image =  field.getScale(obj, scale=scalename)
            if image:
                filename = image.getId()
                dir_path = obj.absolute_url_path().lstrip('/')
                file_path = os.path.join(dir_path, filename)
                content = self._render_obj(image)
                if content:
                    file_path, content = self._apply_image_transforms(file_path, content)
                    self._write(file_path, content)


    def _deploy_file_field(self, obj, field):
        """
        Deploys normal File field
        """
        file_instance = field.getAccessor(obj)()
        if file_instance:
            filename = field.getName()
            dir_path = obj.absolute_url_path().lstrip('/')
            file_path = os.path.join(dir_path, filename)
            if hasattr(file_instance, 'data'):
                content = self._render_obj(str(file_instance.data))
                if content:
                    self._write(file_path, content)


    def _deploy_content(self, obj, is_page=True):
        """
        Deploy object as page.
        """
        content = self._render_obj(obj)
        if content is None:
            return

        filename = obj.absolute_url_path().lstrip('/')
        # deploy additional views for content type
        if PLONE_APP_BLOB_INSTALLED and isinstance(obj, ATBlob):
            self._deploy_views([os.path.join(filename, 'view'), ],
                    is_page=True)

        if is_page:
            filename = os.path.join(filename, 'index.html')
        elif isinstance(obj, ATImage) or hasattr(obj, 'getBlobWrapper') and 'image' in obj.getBlobWrapper().getContentType():
            # create path to dump ATImage in original size
            if filename.rsplit('.', 1)[-1] in ('png', 'jpg', 'gif', 'jpeg'):
                filename = os.path.join(filename, 'image.%s' % filename.rsplit('.', 1)[-1])
            else:
                filename = os.path.join(filename, 'image.jpg')
            filename, content = self._apply_image_transforms(filename, content)
        elif (hasattr(obj, 'getBlobWrapper') and 'image' not in
                obj.getBlobWrapper().getContentType()):
            # create path like for ATImage
            if len(filename.rsplit('.', 1)) > 1:
                filename  = os.path.join(filename, 'file.%s' % filename.rsplit('.', 1)[-1])
            else:
                filename = os.path.join(filename, 'file')

        self._write(filename, content)

        # deploy all sizes of images uploaded for the object
        if not getattr(obj, 'schema', None):
            return

        for field in obj.Schema().fields():
            if PLONE_APP_BLOB_INSTALLED and IBlobImageField.providedBy(field):
                self._deploy_blob_image_field(obj, field)
            elif PLONE_APP_BLOB_INSTALLED and IBlobField.providedBy(field):
                self._deploy_blob_file_field(obj, field)
            elif field.type == 'image':
                self._deploy_image_field(obj, field)
            elif field.type == 'file' and obj.meta_type not in self.file_types:
                self._deploy_file_field(obj, field)
            else:
                continue


    def _deploy_resources(self, urls, base_path):
        """
        Deploy resources linked in HTML or CSS.
        """
        portal_url = getToolByName(self.context, 'portal_url')()
        for url in urls:
            url = url.strip()
            scheme, netloc, path, query, fragment = urlsplit(url)
            if not path:
                ## internal anchor
                continue

            if netloc and netloc != portal_url:
                ## external link
                continue
            elif path.startswith('image/svg+xml;base64') or \
                 path.startswith('image/png;base64'):
                ## images defined in css
                continue
            if path.startswith('/'):
                objpath = path[1:]
            else:
                objpath = os.path.join(base_path, path)

            if isinstance(objpath, unicode):
                objpath = objpath.encode('utf-8')

            # PloneSite with id 'plone' case problems during
            # restrictedTraverse() so we cut it
            objpath_spl = objpath.split('/', 1)
            if objpath_spl[0] == 'plone' and len(objpath_spl) > 1:
                objpath = objpath_spl[1]
            # fix "../" in paths
            objpath = os.path.normpath(objpath)

            if objpath in self.deployed_resources:
                continue
            obj = self.context.unrestrictedTraverse(objpath, None)
            if objpath.rsplit('/', 1)[-1].split('.')[0] == 'image':
                obj = self.context.restrictedTraverse(objpath.rsplit('.', 1)[0], None)
            if not obj:
                obj = self.context.restrictedTraverse(unquote(objpath), None)
            if not obj:
                parent_obj = self.context.restrictedTraverse(unquote(objpath.rsplit('/', 1)[0]), None)
                if parent_obj:
                    image_name = objpath.rsplit('/', 1)[-1]
                    if hasattr(parent_obj, 'schema'):
                        for field in parent_obj.schema.fields():
                            fieldname = field.getName()
                            if image_name.startswith(fieldname):
                                scalename = image_name[len(fieldname) + 1:]
                                obj = field.getScale(parent_obj, scalename)
                                objpath = os.path.join(objpath, 'image.jpg')
                                continue
            if not obj:
                if '/@@images/' in objpath:
                    parent_path, image_name = objpath.split('/@@images/')
                    parent_obj = self.context.unrestrictedTraverse(unquote(parent_path), None)
                    if parent_obj:
                        spl_img_name = image_name.split('/')
                        if len(spl_img_name) == 1:
                            # no scalename in path
                            fieldname = spl_img_name[0]
                            scalename = None
                            objpath = '/'.join((parent_path, 'image.jpg'))
                        else:
                            fieldname, scalename = spl_img_name
                            objpath = os.path.join(parent_path, '_'.join((fieldname, scalename)), 'image.jpg')
                        try:
                            images_view = getMultiAdapter((parent_obj, self.request), name='images')
                            field = images_view.field(fieldname)
                            if field:
                                obj = field.getScale(parent_obj, scalename)
                        except ComponentLookupError:
                            pass
            if not obj:
                log.warning("Unable to deploy resource '%s'!" % objpath)
                continue
            if isinstance(obj, ATImage) or hasattr(obj, 'getBlobWrapper') and 'image' in obj.getBlobWrapper().getContentType():
                # create path to dump ATImage in original size
                if objpath.rsplit('.', 1)[-1] in ('png', 'jpg', 'gif', 'jpeg'):
                    objpath = os.path.join(objpath, 'image.%s' % objpath.rsplit('.', 1)[-1])
                else:
                    objpath = os.path.join(objpath, 'image.jpg')

            content = self._render_obj(obj)
            if content is None:
                continue

            if isinstance(obj, (FSImage, OFSImage, ATImage)) or hasattr(obj, 'getBlobWrapper') and \
                'image' in obj.getBlobWrapper().getContentType():
                objpath, content = self._apply_image_transforms(objpath, content)

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

        # deploying resources only from local domain (the path don't contain external address) 
        urls = [tag['src'] for tag in soup.findAll(['img', 'input', 'embed', 'script'], src=True) if not urlparse(tag['src'])[0]]
        css_imports = RE_CSS_IMPORTS.findall(html)
        css_imports += RE_CSS_IMPORTS_HREF.findall(html)
        css_imports = [link for link in css_imports if not urlparse(link)[0]]
        local_styles = RE_CSS_URL.findall(html)
        urls = urls + css_imports + local_styles
        self._deploy_resources(urls, unquote(base_path))


    def _parse_css(self, content, base_path=''):
        """
        Save all resources used in CSS file.
        """
        self._deploy_resources(RE_CSS_URL.findall(content), unquote(base_path))


    def _write(self, filename, content, dir_path=None, omit_transform=False):
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

        if RE_NOT_BINARY.search(filename) and not omit_transform and \
                not filename.endswith('.js') and not filename.endswith('.css'):
            pre_transformated_content = self._apply_transforms(content)
            post_transformated_content = self._apply_post_transforms(
                    pre_transformated_content, file_path=file_path)
        else:
            pre_transformated_content = post_transformated_content = content
        try:
            try:
                content_file.write(post_transformated_content)
            except UnicodeEncodeError:
                content_file.write(post_transformated_content.encode('utf-8'))
        finally:
            content_file.close()

        log.debug("[*] '%s' saved." % filename)

        if filename.endswith('.css'):
            self._parse_css(pre_transformated_content, os.path.dirname(filename))

        if filename.endswith('.html'):
            self._parse_html(pre_transformated_content, os.path.dirname(filename))
