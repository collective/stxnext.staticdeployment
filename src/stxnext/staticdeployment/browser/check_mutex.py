# -*- coding: utf-8 -*-
from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName

from stxnext.staticdeployment.browser.preferences.staticdeployment import mutex 

class CheckMutexAction(BrowserView):
    
    def check_mutex(self):
       """
       """
       if mutex.locked():
           return False
       return True