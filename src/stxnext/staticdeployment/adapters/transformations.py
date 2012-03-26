# -*- coding: utf-8 -*-
"""
Transformation adapters.
"""
import os
import posixpath
import re
from urlparse import urlparse, urlunparse, urlsplit, urlunsplit

from OFS.Image import File
from Products.ATContentTypes.content.image import ATImage
from Products.CMFCore.FSObject import FSObject
from zope.component import getUtility
from zope.interface import implements

from stxnext.staticdeployment.interfaces import (IPostTransformation,
        IStaticDeploymentUtils, ITransformation)


SRC_PATTERN = re.compile(r"<\s*(?:img|a)\s+[^>]*(?:src|href)\s*=\s*([\"']?[^\"' >]+[\"'])", re.IGNORECASE)
FILE_PATTERN = re.compile(r"<\s*(?:a)\s+[^>]*(?:href)\s*=\s*([\"']?[^\"' >]+[\"'])", re.IGNORECASE)
LINK_PATTERN = re.compile(r"<\s*[^>]*(?:src|href)\s*=\s*([\"']?[^\"' >]+[\"'])", re.IGNORECASE)
BASE_PATTERN = re.compile(r"<\s*base\s+[^>]*href\s*=\s*[\"\']([^\"\'>]+)[\"\']", re.IGNORECASE)


class Transformation(object):
    implements(ITransformation)

    def __init__(self, context):
        self.context = context

    def __call__(self, text):
        return text


class PostTransformation(object):
    implements(IPostTransformation)

    def __init__(self, context):
        self.context = context

    def __call__(self, text, file_path=None):
        return text


class RemoveDomainTransformation(Transformation):
    """
    Remove domain from text.
    """

    def __call__(self, text):
        domain = urlparse(self.context.portal_url())
        domain = urlunparse((domain.scheme, domain.netloc, '', '', '', ''))
        text = text.replace(domain + '/', '/')
        text = text.replace(domain, '/')
        return text


class ChangeImageLinksTransformation(PostTransformation):
    """
    Changes link to image object.
    """

    def __call__(self, text, file_path=None):
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


class ChangeFileLinksTransformation(PostTransformation):
    """
    Changes link to file object.
    """

    def __call__(self, text, file_path=None):
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


class RelativeLinksPostTransformation(PostTransformation):
    """
    Changes all internal links from absolute to relative.
    """
    implements(IPostTransformation)

    def __call__(self, text, file_path=None):
        dutils = getUtility(IStaticDeploymentUtils)
        if not dutils.relative_links:
            return text
        main_dir = dutils.deployment_directory
        add_index = dutils.add_index
        #fix <base> tag
        text = BASE_PATTERN.sub('<base', text)
        matches = LINK_PATTERN.findall(text)

        for match in set(matches):
            clean_match = match.strip('"').strip("'").encode('utf-8')
            # links to "home page"
            if not clean_match == '/':
                clean_match = clean_match.lstrip('/')
                target = os.path.join(main_dir, clean_match)
            else:
                target = main_dir
            match_path = clean_match.replace('../', '').replace('%20', ' ')
            if self.same_domain(clean_match, file_path):
                obj = self.context.restrictedTraverse(match_path, None)
                if obj and not isinstance(obj, (FSObject, File)) and add_index:
                    target = os.path.join(target, 'index.html')
                text = text.replace(match, self.relative_url(target, file_path))
        return text


    @staticmethod
    def relative_url(destination, source):
        """ Returns relative url """
        #http://stackoverflow.com/a/7469668
        if not destination.strip('#'):
            return destination
        u_dest = urlsplit(destination)
        u_src = urlsplit(source)
        _relpath = posixpath.relpath(u_dest.path, posixpath.dirname(u_src.path))

        return urlunsplit(('', '', _relpath, u_dest.query,
            u_dest.fragment))


    @staticmethod
    def same_domain(destination, source):
        """ Checks if given urls belonges to the same domain """
        u_dest = urlsplit(destination)
        u_src = urlsplit(source)

        _uc1 = urlunsplit(u_dest[:2] + tuple('' for i in range(3)))
        _uc2 = urlunsplit(u_src[:2] + tuple('' for i in range(3)))

        if _uc1 != _uc2:
            ## This is a different domain
            return False
        return True
