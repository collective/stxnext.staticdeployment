stxnext.staticdeployment
########################

Overview
========

``stxnext.staticdeployment`` is a tool to deploy Plone site to static files. It supporst Plone 3 and Plone 4 (including sites using Diazo themes).


Installation
============

Edit buildout.cfg and append ``stxnext.staticdeployment`` to eggs and zcml parameters in instance section::

	[instance]
	eggs =
	  ...
	  stxnext.staticdeployment
	
	zcml =
	  ...
	  stxnext.staticdeployment

Instance must be rebuild and restarted::

	./bin/buildout
	./bin/instance stop
	./bin/instance start

This product must be also installed inside Plone site. Do do it, go to *Site Setup* -> *Add/Remove Products*, select checkbox near *stxnext.staticdeployment* and click *Install* button.


Configuration
=============
The configuration is stored in the INI file. The default configuration is contained by the package, but it can be easily overrided by creating the custom `staticdeployment.ini` file in the `${buildout:directory}/etc` folder.
  
   - stored in INI file
   - created by developer of website
   - can be used by many sites
   - `default configuration`_ (included in egg)
   - default configuration can be overriden by file `${buildout:directory}/etc/staticdeployment.ini`


`staticdeployment.ini` paramaters
---------------------------------

``deployment-directory`` (string)
    Where to deploy site. Path can be relative or absolute. Default: `./plone-static`

``layer-interface`` (string)
    Default: ``zope.publisher.interfaces.browser.IDefaultBrowserLayer``

``defaultskin-name`` (string)
    Skin which will be used during deploy. Default: `Sunburst Theme`

``deploy-plonesite`` (boolean)
    If enabled home page will be deployed also as `index.html` in root of ``deployment-directory``. Default: ``true``

``deploy-registry-files`` (boolean)
    Deploy registry files (CSS, JS, KSS)? Default: ``true``

``make-links-relative`` (boolean)
    Make all links relative (otherwise they will be absolute). Default: ``false``

``add-index`` (boolean)
    Add `index.html` to all links (that should have `index.html`). Works only when ``make-links-relative`` is enabled. Default: ``false``

``page-types`` (list)
    Page types that should be deployed. For example: ``ATDocument``, ``ATFolder``

``file-types`` (list)
    File types that should be deployed. For example: ``ATBlob``

``skinstool-files`` (list)
    Additional files (from ``plone_skins`` tool) which should be deployed. For example: `plone_images/favicon.ico`

``additional-files`` (list)
    Other files to deploy. For example: `sitemap.xml.gz`

``additional-pages`` (list)
    Other pages that should be deployed. For example: `sitemap`
    
``deployable-review-states`` (list)
    Only pages with review states listed here will be deployed. Default: `published`


Usage
=====

When website is ready to deployment go to *Site Setup* -> *Static deployment* -> *Deployment* tab. Select *Deploy static version of website* checkbox and press *Save* button. Deployment will work for few seconds or minutes (it depends on size of website and server performance).


.. _default configuration: https://svn.plone.org/svn/collective/stxnext.staticdeployment/trunk/src/stxnext/staticdeployment/etc/staticdeployment.ini

Author & Contact
================

:Author:
 * Igor Kupczyński <``igor.kupczynski@stxnext.pl``>
 * Radosław Jankiewicz <``radoslaw.jankiewicz@stxnext.pl``>
 * Wojciech Lichota <``wojciech.lichota@stxnext.pl``>
 * Sebastian Kalinowski <``sebastian.kalinowski@stxnext.pl``>

.. image:: http://stxnext.pl/open-source/files/stx-next-logo

**STX Next** Sp. z o.o.

http://stxnext.pl

info@stxnext.pl
