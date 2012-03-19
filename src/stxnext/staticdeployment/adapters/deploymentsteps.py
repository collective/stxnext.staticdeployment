# -*- coding: utf-8 -*-
"""
Deployment step adapters.
"""
from zope.interface import implements

from stxnext.staticdeployment.interfaces import IDeploymentStep

class DeploymentStep(object):
    implements(IDeploymentStep)

    def __init__(self, context):
        self.context = context

    def update(self, deployment_view, modification_date):
        self.request = deployment_view.request
        self.deployment_view = deployment_view
        self.config = deployment_view.config
        self.modification_date = modification_date

    def __call__(self):
        return True
