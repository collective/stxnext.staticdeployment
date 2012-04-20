"""
Transformation adapters for Diazo themes
"""
from plone.app.theming.transform import ThemeTransform
from plone.app.theming.interfaces import IThemeSettings
from plone.registry.interfaces import IRegistry
from zope.component import queryUtility

from transformations import PostTransformation


class ApplyDiazoThemeTransformation(PostTransformation):
    """
    Apply Diazo transform
    """

    def __call__(self, text, file_path=None):
        # don't execute this transform if the theme is not enabled
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IThemeSettings, False)
        if not settings.enabled:
            return text

        context = self.context
        req = context.REQUEST
        # set false BASE url to omit the theme's blacklisted domains
        req['BASE1'] = 'http://apply_diazo_theme.com'
        theme_transform = ThemeTransform(context, req)
        encoding = 'utf-8'
        transformed_text = theme_transform.transformIterable(text, encoding)
        if transformed_text:
            text = transformed_text.serialize()
        return text
