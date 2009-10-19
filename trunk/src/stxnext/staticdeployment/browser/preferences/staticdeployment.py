# -*- coding: utf-8 -*-
import os, shutil, logging, re

from plone.app.controlpanel.events import ConfigurationChangedEvent
from plone.app.controlpanel.form import ControlPanelForm
from plone.app.form.validators import null_validator
from plone.fieldsets.fieldsets import FormFieldsets
from plone.protect import CheckAuthenticator
from zope.component import getMultiAdapter
from zope.event import notify
from zope.formlib.form import Fields, FormFields, action, Fields, applyChanges
from zope.interface import Interface
from zope.schema import TextLine, Bool, ValidationError

from Products.CMFDefault.formlib.schema import ProxyFieldProperty, SchemaAdapterBase
from Products.CMFPlone import PloneMessageFactory as _
from Products.statusmessages.interfaces import IStatusMessage
from Products.statusmessages.message import decode as message_decode

log = logging.getLogger(__name__)


RE_DOMAIN = re.compile(r'^[a-z0-9-]+(\.[a-z0-9-]+)*\.([a-z]{2,6})(:[0-9]{1,5})?$')

class NotDomain(ValidationError):
    __doc__ = u'Incorrect domain.'

def isDomain(value, dont_raise=False):
    if not RE_DOMAIN.match(value):
        if dont_raise: return False
        raise NotDomain(value)
    return True


class IStaticDeploymentSettings(Interface):
    """
    Static deployment settings.
    """
    frontend_domain = TextLine(
        title=_(u'Front-end domain'),
        description=_(u''),
        default=u'preview.example.com',
        constraint=isDomain,
        required=True,
        )

    backend_domain = TextLine(
        title=_(u'Back-end domain'),
        description=_(u''),
        default=u'admin.example.com',
        constraint=isDomain,
        required=True,
        )

    deployment_directory = TextLine(
        title=_(u'Deployment directory'),
        description=_(u''),
        default=u'/var/www/example.com/html',
        required=True,
        )

    last_triggered = TextLine(
        title=_(u'Last static deployment date'),
        description=_(u'Last static deployment date - format RRRR/MM/DD'),
        default=u'',
        required=False,
        )


class IStaticDeployment(Interface):
    """
    Static deployment.
    """
    delete_previous = Bool(
        title=_(u'Remove previously deployed files'),
        description=_(u''),
        )

    full_deployment = Bool(
        title=_('Deploy static version of website'),
        description=_(u''),
        )

    update_deployment = Bool(
        title=_(u'Update previously deployed files'),
        description=_(u''),
        )


class StaticDeploymentSettingsAdapter(SchemaAdapterBase):
    """
    Settings storage (as site_properties in portal_properties).
    """
    frontend_domain = ProxyFieldProperty(IStaticDeploymentSettings['frontend_domain'])
    backend_domain = ProxyFieldProperty(IStaticDeploymentSettings['backend_domain'])
    deployment_directory = ProxyFieldProperty(IStaticDeploymentSettings['deployment_directory'])
    last_triggered = ProxyFieldProperty(IStaticDeploymentSettings['last_triggered'])


class StaticDeploymentAdapter(SchemaAdapterBase):
    """
    No specific storage.
    """
    delete_previous = False
    full_deployment = False
    update_deployment = False


deployment_fieldset = FormFieldsets(IStaticDeployment)
deployment_fieldset.id = 'deployment'
deployment_fieldset.label = _(u'Deployment')
deployment_fieldset.description = _(u'Static deployment')

settings_fieldset = FormFieldsets(IStaticDeploymentSettings)
settings_fieldset.id = 'settings'
settings_fieldset.label = _(u'Settings')
settings_fieldset.description = _(u'Static deployment settings')


class StaticDeploymentForm(ControlPanelForm):
    """
    Static deployment form.
    """
    form_fields = FormFieldsets(deployment_fieldset, settings_fieldset)

    label = _('Static deployment')
    description = _(u'')

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

    def _on_save(self, data):
        """
        Do static deployment.
        """
        settings = IStaticDeploymentSettings(self.context)
        messages = IStatusMessage(self.request)
        if data['delete_previous']:
            path = os.path.normpath(settings.deployment_directory)
            try:
                shutil.rmtree(path)
            except OSError, e:
                log.exception('Removing previously deployed files:')
                message = _(u"Couldn't remove previously deployed files!")
                messages.addStatusMessage(message, type='error')
            else:
                message = _(u'Previously deployed files had been removed.')
                messages.addStatusMessage(message, type='info')

        if data['full_deployment']:
            return self.request.response.redirect('http://%s/@@staticdeployment/full' % settings.frontend_domain)

        if data['update_deployment']:
            return self.request.response.redirect('http://%s/@@staticdeployment/update' % settings.frontend_domain)
