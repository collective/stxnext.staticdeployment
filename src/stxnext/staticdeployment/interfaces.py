# -*- coding: utf-8 -*-
"""
Interfaces used in project.
"""
from zope.interface import Interface

class IStaticDeploymentUtils(Interface):
    """
    Functnions neccesery to deploy static content
    """
    

class ITransformation(Interface):
    """
    Transformation of some text.
    """

    def __call__(text):
        """
        Transform given text.
        """


class IDeploymentStep(Interface):
    """
    Deploy content.
    
    It can be used as plugin, that extends standard functionality
    of stxnext.staticdeployment.
    """

    def __call__(text):
        """
        Run deployment.
        """
