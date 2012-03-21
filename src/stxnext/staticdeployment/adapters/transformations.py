# -*- coding: utf-8 -*-
"""
Transformation adapters.
"""
import os, re

from zope.interface import implements
from Products.ATContentTypes.content.image import ATImage

from stxnext.staticdeployment.interfaces import ITransformation

SRC_PATTERN = re.compile(r"<\s*(?:img|a)\s+[^>]*(?:src|href)\s*=\s*([\"']?[^\"' >]+[\"'])", re.IGNORECASE)
FILE_PATTERN = re.compile(r"<\s*(?:a)\s+[^>]*(?:href)\s*=\s*([\"']?[^\"' >]+[\"'])", re.IGNORECASE)

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
        text = text.replace(self.context.REQUEST['BASE1']+'/', '/')
        text = text.replace(self.context.REQUEST['BASE1'], '/')
        return text


class ChangeImageLinksTransformation(Transformation):
    """
    Changes link to image object.
    """

    def __call__(self, text):
        matches = SRC_PATTERN.findall(text)
        for match in set(matches):
            match_path = match.strip('"').strip("'").replace('../', '').replace('%20', ' ').lstrip('/').encode('utf-8')
            obj = self.context.restrictedTraverse(match_path, None)
            if obj and isinstance(obj, ATImage):
                text = text.replace(match, match[:-1] + '/image.%s' % match.rsplit('.', 1)[-1])
            if hasattr(obj, 'getBlobWrapper'):
                if 'image' in obj.getBlobWrapper().getContentType():
                    if match_path.rsplit('.', 1)[-1] in ('png', 'jpg', 'gif', 'jpeg'):
                        text = text.replace(match, os.path.join(match[:-1],
                            'image.%s' % match.rsplit('.', 1)[-1]))
                    else:
                        text = text.replace(match, os.path.join(match[:-1],
                            'image.jpg%s' % match[-1]))
        return text

class ChangeFileLinksTransformation(Transformation):
    """
    Changes link to file object.
    """

    def __call__(self, text):
        matches = FILE_PATTERN.findall(text)
        for match in set(matches):
            match_path = match.strip('"').strip("'").replace('../', '').replace('%20', ' ').lstrip('/').encode('utf-8')
            obj = self.context.restrictedTraverse(match_path, None)
            if hasattr(obj, 'getBlobWrapper'):
                if 'image' not in obj.getBlobWrapper().getContentType():
                    if len(match_path.rsplit('.', 1)) > 1:
                        text = text.replace(match, os.path.join(match[:-1],
                            'file.%s' % match.rsplit('.', 1)[-1]))
                    else:
                        text = text.replace(match, os.path.join(match[:-1],
                            'file%s' % match[-1]))
        return text
