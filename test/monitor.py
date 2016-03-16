from weakref import WeakKeyDictionary
from cPickle import dumps

""" This module defines the Monitor class.
"""

class Monitor():
    """ A class to monitor whether an object has changed.

    Uses pickle.dumps() to convert the object to a string
    and stores it in a (weak-reference) dictionary for
    later comparison. Example:

    >>> obj = MyObject()
    >>> monitor = Monitor()
    >>>
    >>> # Start tracking obj
    >>> print monitor.modified(obj) # False
    >>> obj.change_me()
    >>>
    >>> # Test for changes, and update reference
    >>> print monitor.modified(obj) # True
    >>> print monitor.modified(obj) # False
    """
    def __init__(self):
        self.objects = WeakKeyDictionary()
    def modified(self, obj):
        current_pickle = dumps(obj, -1)
        changed = False
        if obj in self.objects:
            changed = current_pickle != self.objects[obj]

        self.objects[obj] = current_pickle
        return changed
