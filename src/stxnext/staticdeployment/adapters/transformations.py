# -*- coding: utf-8 -*-
"""
Transformation adapters.
"""
from zope.interface import implements

from stxnext.staticdeployment.interfaces import ITransformation

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
        text = text.replace(self.context.request['BASE1']+'/', '/')
        text = text.replace(self.context.request['BASE1'], '/')
        return text
