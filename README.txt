stxnext.staticdeployment
========================

Overview
========

Deploy Plone site to static files.


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

Every website has own configuration (different set of eggs, skin, products etc.) - this I meas as project. But website can have few instances (development, test and production instances). Because of this, configuration is split for two parts: 

 * instance parameters:
  
   - parameters connected to instance - e.g.: domain
   - configured in *Control Panel* - can be edited throw the web (*Site Setup* -> *Static deployment* -> *Settings* tab)
   - form has description and validation - can be used by less experienced users

 * website parameters:
  
   - stored in INI file
   - created by developer of website
   - can be used by many sites
   - `default configuration`_ (included in egg)
   - default configuration can be overriden by file `${buildout:directory}/etc/staticdeployment.ini`


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

.. image:: http://stxnext.pl/open-source/files/stx-next-logo

**STX Next** Sp. z o.o.

http://stxnext.pl

info@stxnext.pl
