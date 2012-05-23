# -*- coding: utf-8 -*-
import os, shutil, logging, traceback, thread
from ConfigParser import ParsingError
from datetime import datetime

from AccessControl.SecurityManagement import newSecurityManager
from plone.app.controlpanel.events import ConfigurationChangedEvent
from plone.app.controlpanel.form import ControlPanelForm
from plone.app.form.validators import null_validator
from plone.app.form.widgets import MultiCheckBoxWidget
from plone.protect import CheckAuthenticator
from zope.component import getMultiAdapter, getUtility
from zope.interface import Interface, implements
from zope.event import notify
from zope.formlib.form import Fields, FormFields, action, applyChanges
from zope.schema import TextLine, Bool, Tuple, Choice
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from zope.schema.interfaces import IVocabularyFactory

from Products.CMFCore.utils import getToolByName
from Products.CMFDefault.formlib.schema import ProxyFieldProperty, SchemaAdapterBase
from Products.CMFDefault.formlib.vocabulary import StaticVocabulary
from Products.CMFDefault.formlib.widgets import ChoiceRadioWidget
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from Products.statusmessages.message import decode as message_decode

from stxnext.staticdeployment.interfaces import IStaticDeploymentUtils
from stxnext.staticdeployment.utils import get_config_path, ConfigParser
from stxnext.staticdeployment.browser import DeployedBase

from zope.i18nmessageid import MessageFactory
_ = MessageFactory('stxnext.staticdeployment')

mutex = thread.allocate_lock()
log = logging.getLogger(__name__)


class IStaticdeploymentPloneControlPanelForm(Interface):
    """
    """


class IStaticDeployment(Interface):
    """
    Static deployment manage form.
    """
    section_choice = Tuple(
        title=_('Choose configuration section'),
        required=True,
        missing_value=set(),
        value_type=Choice(
            vocabulary="stxnext.staticdeployment.vocabularies.ConfigSections")
        )
    
    last_triggered = TextLine(
        title=_(u'Last static deployment date'),
        description=_(u'Last static deployment date - format YYYY/MM/DD HH:MM:SS'),
        default=u'',
        required=False,
        )
    
    delete_previous = Bool(
        title=_(u'Remove previously deployed files'),
        description=_(u''),
        )

    deployment = Choice(
        title=_('Deploy static version of website'),
        required=True,
        description=_(u'Choose if you want to deploy all content or update content modified since last static deployment'),
        vocabulary='stxnext.staticdeployment.vocabularies.DeploymentMode',
        )


class StaticDeploymentAdapter(SchemaAdapterBase):
    """
    Storages for particular form fields.
    """
    section_choice = set()
    last_triggered = ProxyFieldProperty(IStaticDeployment['last_triggered'])
    delete_previous = False
    deployment = False

# Vocabularies
available_deployment_modes = (
        (u'full_deployment', 'full_deployment', _(u'Full deployment')),
        (u'update_deployment', 'update_deployment', _(u'Update deployment')),
        )
        
DeploymentModeVocabularyFactory = StaticVocabulary(available_deployment_modes)

class ConfigSectionsVocabulary(object):
    """
    Vocabulary containing all sections defined in config file
    """
    implements(IVocabularyFactory)

    def __call__(self, context):
        """
        """
        config_path = os.path.normpath(get_config_path())
        config_file = open(config_path, 'r')
        config_parser = ConfigParser()
        try:
            config_parser.readfp(config_file)
        except ParsingError, e:
            message = _(u"Error when trying to parse '%s'" % config_path)
            messages = IStatusMessage(context.context.request)
            messages.addStatusMessage(_(e.message), type='error')
            return SimpleVocabulary([])
        sections = [SimpleTerm(section, u'%s' % section) for section in config_parser.sections()]
        if config_parser.defaults():
            sections.insert(0, SimpleTerm('DEFAULT', 'DEFAULT'))
        return SimpleVocabulary(sections)

ConfigSectionsVocabularyFactory = ConfigSectionsVocabulary()

# widgets
class MultiCheckBoxVocabularyWidget(MultiCheckBoxWidget):
    """ 
    Multicheckbox widget.
    """
    def __init__(self, field, request):
        super(MultiCheckBoxVocabularyWidget, self).__init__(field,
            field.value_type.vocabulary, request)

# form
class StaticDeploymentForm(ControlPanelForm, DeployedBase):
    """
    Static deployment form.
    """
    
    template = ViewPageTemplateFile('staticdeployment-control-panel.pt')
    
    implements(IStaticdeploymentPloneControlPanelForm)
    label = _('Static deployment')
    description = _(u'')
    id = u'static-deployment-form'
    form_name = _(u'Static deployment panel')
    form_fields = FormFields(IStaticDeployment)
    form_fields['section_choice'].custom_widget = MultiCheckBoxVocabularyWidget
    form_fields['deployment'].custom_widget = ChoiceRadioWidget
    
    def getAllEntries(self):
        """ """
        return self.storage.__iter__()
    
    def store(self, date, username, action, clear, full, status, errmsg=None):
        return self.storage.add(date, username, action, clear, full, status, errmsg)
    
    def setUpWidgets(self, ignore_request=False):
        super(StaticDeploymentForm, self).setUpWidgets(ignore_request=ignore_request)
        self.widgets['deployment']._displayItemForMissingValue = False

    def status(self):
        msg_code = self.request.get('msg')
        if msg_code:
            msg = message_decode(msg_code.decode('base64'))
            return msg[0].message

        ## do not show default message
        return ''

    @action(_(u'label_save', default=u'Save'), name=u'save')
    def handle_edit_action(self, action, data):
        CheckAuthenticator(self.request)
        if applyChanges(self.context, self.form_fields, data, self.adapters):
            notify(ConfigurationChangedEvent(self, data))
            return self._on_save(data)

    @action(_(u'label_cancel', default=u'Cancel'), validator=null_validator, name=u'cancel')
    def handle_cancel_action(self, action, data):
        messages = IStatusMessage(self.request)
        messages.addStatusMessage(_("Changes canceled."), type="info")
        url = getMultiAdapter((self.context, self.request), name='absolute_url')()
        return self.request.response.redirect(url + '/plone_control_panel')

    def _locked_on_save(self, data):
        """
        Do static deployment.
        """
        messages = IStatusMessage(self.request)
        username = getToolByName(self.context, 'portal_membership').getMemberInfo().get('username', '')
        
        config_path = os.path.normpath(get_config_path())
        config_file = open(config_path, 'r')
        config_parser = ConfigParser()
        try:
            config_parser.readfp(config_file)
        except ParsingError, e:
            message = _(u"Error when trying to parse '%s'" % config_path)
            messages.addStatusMessage(message, type='error')
            return
        
        sections = data.get('section_choice', None)
        if not sections:
            return
        
        # deleting deployed files for paths given in config file
        if data['delete_previous']:
            for section in sections:
                path = config_parser.get(section, 'deployment-directory').strip()
                try:
                    shutil.rmtree(path)
                except OSError, e:
                    log.exception('Removing previously deployed files for path: %s' % path)
                else:
                    log.info(u'Files from path %s have been succesfully removed.' % path)
        
        if data['deployment']:
            deployment_utils = getUtility(IStaticDeploymentUtils)
            
            # setting debug mode for resource tools
            initial_debugmode = deployment_utils.initial_resources_tools_mode(self.context)
            
            # deploy only objects modified since given date
            if data['deployment'] == 'update_deployment':
                date = data['last_triggered']
            else:
                date = None

            try:
                for section in sections:
                    try:
                        deployment_utils.deploy(self.context, self.request, section, date)
                        message = _(u'Succesfull deployment for section %s' % section)
                        messages.addStatusMessage(message, type='info')
                        self.store(datetime.now(), username, section, data['delete_previous'], data['deployment'], 1)
                        
                    except Exception, e:
                        log.error('Error while deploying section %s: \n %s' % (section, traceback.format_exc()))
                        message = _(u'Error while deploying section %s: %s' % (section, e))
                        messages.addStatusMessage(message, type='error')
                        self.store(datetime.now(), username, section, data['delete_previous'], data['deployment'], 0, str(e))

            # reverting initial resource tools settings and request modifications  
            finally:
                skins_tool = getToolByName(self.context, 'portal_skins')
                deployment_utils.revert_resources_tools_mode(self.context, initial_debugmode)
                deployment_utils.revert_request_modifications(self.context, self.request)
                user = self.request.get('AUTHENTICATED_USER')
                newSecurityManager(self.request, user)

    def _on_save(self, data):
        """
        """
        if not mutex.locked():
            try:
                mutex.acquire()
                self._locked_on_save(data)
            finally:
                mutex.release()
            
