import logging
import collections

class CircularPausingFilter(logging.Filter):
    """A filter that adds itself to a handler. When the pause() function
    is called, further records are not emitted, but stored in a ring
    buffer.

    When unpause() is called, messages are no longer stored, and all 
    """ 
    def __init__(self, handler, maxsize=0):
        self.dq = collections.deque(maxlen=maxsize)
        self.is_paused = False
        self.handler = handler
        self.handler.addFilter(self)
    
    def pause(self): 
        self.is_paused = True
    
    def unpause(self, emit_queue=True):
        """If emit_queue is False, the messages in the queue are not 
        emitted to the handler immediately. Use flush() to do this
        manually.
        """
        self.is_paused = False
        if emit_queue:
            self.flush()
    
    def flush(self):
        while self.dq:
            self.handler.emit(self.dq.popleft())

    def filter(self, r):
        if self.is_paused:
            self.dq.append(r)
            return False
        else:
            return True

