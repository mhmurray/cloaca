class InitializationError(Exception):
    """ An exception class for StateMachine.
    """
    pass


class StateMachine(object):
    """ A class to represent a Finite State Machine.
    """


    def __init__(self):
        self.handlers = {}
        self.arrival_handlers = {}
        self.endStates = []
        self.state = None

    def add_state(self, name, arrival_handler, handler, end_state=False):
        name = name.upper()
        self.arrival_handlers[name] = arrival_handler
        self.handlers[name] = handler
        if end_state:
            self.endStates.append(name)

    def set_start(self, name):
        self.state = name.upper()

    def pump(self, cargo):
        if self.state in self.endStates:
            print('Done already!')
            return

        try:
            handler = self.handlers[self.state]
        except:
            raise InitializationError('No transition for state ' + str(self.state))
        if not self.endStates:
            raise  InitializationError('Must have at least one end_state.')
    
        try:
            new_state = handler(cargo)
        except:
            print 'Failed to make choice in state {0}'.format(self.state)
            return

        self.state = new_state
        try:
            arrival_handler = self.arrival_handlers[self.state]
        except:
            raise InitializationError('No arrival handler for state ' + str(self.state))
        if arrival_handler is not None:
            arrival_handler()
