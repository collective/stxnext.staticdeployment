# -*- coding: utf-8 -*-
import os
from setuptools import setup, find_packages

version = open('src/stxnext/staticdeployment/version.txt').read()

setup (
    name='stxnext.staticdeployment',
    version=version,
    author='STX Next Sp. z o.o, Igor Kupczyński, Radosław Jankiewicz, ' \
            'Wojciech Lichota, Sebastian Kalinowski',
    author_email='info@stxnext.pl',
    description='Deploy Plone site to static files.',
    long_description=open("README.rst").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
    keywords='plone static deploy',
    platforms=['any'],
    url='http://www.stxnext.pl/open-source',
    license='Zope Public License, Version 2.1 (ZPL)',
    packages=find_packages('src'),
    include_package_data=True,
    package_dir={'':'src'},
    namespace_packages=['stxnext'],
    zip_safe=False,

    install_requires=[
        'setuptools',
        'BeautifulSoup',
       ],

    extras_require = {
    'test': [
            'plone.app.testing',
        ]
    },

    entry_points="""
    [z3c.autoinclude.plugin]
    target = plone
    """,

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Zope2',
        'Framework :: Plone',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Zope Public License',
        'Natural Language :: English',
        'Programming Language :: Python',
        ]
    )
