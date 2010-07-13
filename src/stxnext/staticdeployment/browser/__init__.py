from Products.Five import BrowserView
from stxnext.staticdeployment.content.store import IDeployedStore

class DeployedBase(BrowserView):
    
    _storage = None
    @property
    def storage(self):
        if self._storage is None:
            self._storage = IDeployedStore(self.context)
        return self._storage