import random
from time import time
from datetime import datetime
from zope.interface import Interface, implements, Attribute
from persistent import Persistent
from persistent.dict import PersistentDict
from zope.annotation.interfaces import IAnnotations
from BTrees.OOBTree import OOBTree
from Products.Five import BrowserView

ANNOTATION_KEY = 'stxnext.staticdeployment.store'

def date_to_id(date):
    return '%s_%s' % (date.strftime('%Y_%m_%d_%H_%M_%S'), random.randrange(10000))

class DEPLOYMENT_STATUS(object):
    ERROR = 0
    DONE = 1

class IDeployedEntry(Interface):
    date = Attribute("(tz-naive) datetime.datetime object")
    user = Attribute("user performing export action")
    id = Attribute("id of the object generated from date")
    status = Attribute("status, one of DONE, ERROR")
    action = Attribute("action that was performed")
    clear = Attribute("removing previous version was performed")
    full = Attribute("full deployment or update was performed")
    error = Attribute("error description or None")
    
    def setDone(self):
        """ set state do DONE """
    
    def setError(self, msg):
        """ set state to ERROR, save error message """
    
class DeployedEntry(Persistent):
    
    implements(IDeployedEntry)
    
    def __init__(self, date, user, action, clear, full, status, errmsg=None):
        self.date = date
        self.user = user
        self.id = date_to_id(self.date)
        self.status = status
        self.action = action
        self.clear = clear
        self.full = full
        self.error = errmsg
        
    def __str__(self):
        return '<Deployment "%s"@%s created %s>' % (self.action, self.date, self.creation_date)    

class IDeployedStore(Interface):
    """ Interface for deployed entries storage """
    
    def __iter__(self):
        """ iterate over all entries """
        
    def done(self):
        """ iterate over done entries """
        
    def add(self, date, user, action, clear, full, status, errmsg=None):
        """ add new entry to the store and return it
        @rtype: IDeployedEntry
        """
        
    def get(self, id):
        """ return stored entry with given id
        @rtype: IDeployedEntry
        """
        
    def remove(self, id):
        """ remove stored entry with given id """
        
class iteration_with_status(object):
    """ method decorator """
    def __init__(self, status):
        self.status = status
        
    def __call__(self, func):
        def inner(this):
            for entry in this:
                if entry.status == self.status:
                    yield entry
        inner.__name__ = func.__name__
        return inner
    
class DeployedStore(Persistent):
    """ Deployed entries storage """
    
    implements(IDeployedStore)

    store_length = 10
    
    def __init__(self):
        self._entries = OOBTree()
        self.busy = False
        
    def __iter__(self):
        return reversed([i for i in self._entries.itervalues()])
        
    def add(self, date, user, action, clear, full, status, errmsg=None):
        entry = DeployedEntry(date, user, action, clear, full, status, errmsg)
        self._entries[entry.id] = entry
        if len(self._entries) > self.store_length:
            del self._entries[self._entries.minKey()]
    
    def remove(self, id):
        del self._entries[id]
    
    def get(self, id):
        return self._entries[id]
    
    @iteration_with_status(DEPLOYMENT_STATUS.DONE)
    def done(self): pass
    
    @iteration_with_status(DEPLOYMENT_STATUS.ERROR)
    def error(self): pass
    
def DeployedAdapter(site):
    """ returns DeployedStore of site """
    annotations = IAnnotations(site)
    if not annotations.has_key(ANNOTATION_KEY):
        annotations[ANNOTATION_KEY] = DeployedStore()
    return annotations[ANNOTATION_KEY]

class DeployedClear(BrowserView):
    """ removes deployed store from annotations """
    
    def __call__(self):
        """ """
        annotations = IAnnotations(self.context)
        if annotations.has_key(ANNOTATION_KEY):
            del annotations[ANNOTATION_KEY]
            return "CLEARED"
        else:
            return "NOTHING TO CLEAR"