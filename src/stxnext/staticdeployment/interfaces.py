# -*- coding: utf-8 -*-
"""
Interfaces used in project.
"""
from zope.interface import Interface

class IStaticDeploymentUtils(Interface):
    """
    Functnions neccesery to deploy static content
    """


class IImageTransformation(Interface):
    """
    Transformation of some image.
    """

    def __call__(filename, image):
        """
        Transform given image.
        """


class ITransformation(Interface):
    """
    Transformation of some text.
    """

    def __call__(text):
        """
        Transform given text.
        """


class IPostTransformation(Interface):
    """
    Transformation of some text after dropping objects to the file.
    """

    def __call__(text, file_path):
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


class IExtraDeploymentCondition(Interface):
    """
    Allow defining extra conditions for deploying content.
    
    It can be used as plugin, that extends standard functionality
    of stxnext.staticdeployment.
    """

    def __call__(obj):
        """
        Check condition.
        """
