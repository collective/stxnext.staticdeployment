# -*- coding: utf-8 -*-
"""
Transformation adapters.
"""
from zope.interface import implements

from stxnext.staticdeployment.interfaces import ITransformation
from stxnext.staticdeployment.browser.preferences.staticdeployment import IStaticDeploymentSettings

class Transformation(object):
    implements(ITransformation)

    def __init__(self, context):
        self.context = context

    def __call__(self, text):
        return text


class RemoveDomainTransformation(Transformation):
    """
    Remove domain from text. 
    """

    def __call__(self, text):
        settings = IStaticDeploymentSettings(self.context)
        text = text.replace('http://%s/' % settings.frontend_domain, '/')
        text = text.replace('http://%s' % settings.frontend_domain, '/')
        text = text.replace(self.context.request['BASE1']+'/', '/')
        text = text.replace(self.context.request['BASE1'], '/')
        return text
