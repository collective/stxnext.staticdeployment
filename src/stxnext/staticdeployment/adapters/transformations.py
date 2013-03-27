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

try:
    from plone.app.blob.interfaces import IBlobWrapper
    PLONE_APP_BLOB_INSTALLED = True
except:
    PLONE_APP_BLOB_INSTALLED = False

from stxnext.staticdeployment.utils import relpath
from stxnext.staticdeployment.interfaces import (IPostTransformation,
        IStaticDeploymentUtils, ITransformation)
from HTMLParser import HTMLParseError
from BeautifulSoup import BeautifulSoup
from plone.app.imaging.interfaces import IImageScaling


SRC_PATTERN = re.compile(r"<\s*(?:img|a)\s+[^>]*(?:src|href)\s*=\s*([\"']?[^\"' >]+[\"'])", re.IGNORECASE)
FILE_PATTERN = re.compile(r"<\s*(?:a)\s+[^>]*(?:href)\s*=\s*([\"']?[^\"' >]+[\"'])", re.IGNORECASE)
LINK_PATTERN = re.compile(r"<\s*[^>]*(?:src|href)\s*=\s*([\"']?[^\"' >]+[\"'])", re.IGNORECASE)
CSS_LINK_PATTERN = re.compile(r"@import\s*(?:url)\s*\(\s*(.*)[\)]", re.IGNORECASE)
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
        domain = urlunparse((domain[0], domain[1], '', '', '', ''))
        text = text.replace(domain + '/', '/')
        text = text.replace(domain, '/')
        return text


class ChangeRSSLinksTransformation(PostTransformation):
    """
    Changes link to image object.
    """

    def __call__(self, text, file_path=None):
        return text.replace('/RSS"', '/RSS.xml"')


class ChangeImageLinksTransformation(PostTransformation):
    """
    Changes link to image object.
    """

    def __call__(self, text, file_path=None):
        matches = SRC_PATTERN.findall(text)
        for match in set(matches):
            match_path = match.strip('"').strip("'").replace('../', '').replace('%20', ' ').lstrip('/')
            if type(match_path) == unicode:
                match_path = match_path.encode('utf-8')
            obj = self.context.unrestrictedTraverse(match_path, None)
            ext = match_path.split('.')[-1].lower()
            ext = ext in ('png', 'jpg', 'gif', 'jpeg') and ext or 'jpg'
            if obj and isinstance(obj, ATImage):
                text = text.replace(match_path, match_path + '/image.%s' % ext)
            if hasattr(obj, 'getBlobWrapper'):
                if 'image' in obj.getBlobWrapper().getContentType():
                    text = text.replace(match_path, match_path + '/image.%s' % ext)
            if not obj:
                try:
                    path, filename = match_path.rsplit('/', 1)
                except ValueError:
                    continue
                fieldname = filename.split('_', 1)[0]
                obj = self.context.restrictedTraverse('/'.join((path, fieldname)), None)
                if not obj:
                    # not all fields are traversable
                    obj = self.context.restrictedTraverse(path, None)
                    if IImageScaling.providedBy(obj):
                        # we can't do anything with the @@images view yet here...
                        obj = None
                    if obj and hasattr(obj, 'getField'):
                        field = obj.getField(fieldname)
                        if field:
                            obj = field.get(obj)
                if PLONE_APP_BLOB_INSTALLED and IBlobWrapper.providedBy(obj):
                    text = text.replace(match_path, match_path + '/image.jpg')
                if not obj:
                    if '/@@images/' in match_path:
                        parent_path, image_name = match_path.split('/@@images/')
                        spl_img_name = image_name.split('/')
                        if len(spl_img_name) == 1:
                            # no scalename in path
                            uid = spl_img_name[0]
                            if '-' in uid:
                                # seems to be actual uid for a custom scale here...
                                # it should written out as [uid].[ext]
                                new_path = '/'.join((parent_path, uid))
                            else:
                                # just use original if we can't figure this out...
                                new_path = '/'.join((parent_path, 'image.%s' % ext))
                        else:
                            # scalename in path 
                            fieldname, scalename = spl_img_name
                            new_path = '/'.join((parent_path, '_'.join((fieldname, scalename))))
                            new_path = new_path + '/image.jpg'
                        text = text.replace(match_path, new_path)

        # XXX hack to fix issue when images
        # are listed twice and transformed diff both times...
        for scalename in ('large', 'preview', 'mini', 'thumb',
                          'tile', 'icon', 'listing', 'leadimage'):
            text = text.replace('/image.jpg/image_%s' % scalename, '/image_%s/image.jpg' % scalename)

        return text


class ChangeFileLinksTransformation(PostTransformation):
    """
    Changes link to file object.
    """

    def __call__(self, text, file_path=None):
        matches = FILE_PATTERN.findall(text)
        for match in set(matches):
            match_path = match.strip('"').strip("'").replace('../', '').replace('%20', ' ').lstrip('/')
            if type(match_path) == unicode:
                match_path = match_path.encode('utf-8')
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
        matches = LINK_PATTERN.findall(text) + CSS_LINK_PATTERN.findall(text)

        for match in set(matches):
            clean_match = match.strip('"').strip("'").encode('utf-8')
            # links to "home page"
            if not clean_match == '/':
                clean_match = clean_match.lstrip('/')
                target = os.path.join(main_dir, clean_match)
            else:
                target = main_dir
            match_path = clean_match.replace('../', '').replace('%20', ' ')
            if self.is_same_domain(clean_match, file_path):
                obj = self.context.restrictedTraverse(match_path, None)
                if obj and not isinstance(obj, (FSObject, File)) and add_index:
                    target = os.path.join(target, 'index.html')
                text = text.replace(match, self.get_relative_url(target, file_path))
        return text


    @staticmethod
    def get_relative_url(destination, source):
        """ Returns relative url """
        #http://stackoverflow.com/a/7469668
        if not destination.strip('#'):
            return destination
        u_dest = urlsplit(destination)
        u_src = urlsplit(source)
        _relpath = relpath(u_dest[2], posixpath.dirname(u_src[2]))
        return urlunsplit(('', '', _relpath, u_dest[3],
            u_dest[4]))


    @staticmethod
    def is_same_domain(destination, source):
        """ Checks if given urls belonges to the same domain """
        u_dest = urlsplit(destination)
        u_src = urlsplit(source)

        _uc1 = urlunsplit(u_dest[:2] + tuple('' for i in range(3)))
        _uc2 = urlunsplit(u_src[:2] + tuple('' for i in range(3)))

        if _uc1 != _uc2:
            ## This is a different domain
            return False
        return True
