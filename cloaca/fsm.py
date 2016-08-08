class FSMError(Exception):
    """An exception class for StateMachine.
    """
    def __init__(self, msg):
        self.msg = msg


class StateMachine(object):
    """ A class to represent a Finite State Machine.
    """
    def __init__(self):
        self.handlers = {}
        self.arrival_handlers = {}
        self.endStates = []
        self.state = None
        self.adapter = None
        self.pump_return_value = None

    def add_adapter(self, func):
        """ Adds an adapter function that takes the cargo
        passed to each state and does something with it.

        This is a function that takes a single argument that
        is the same as the transition functions, and returns
        what the transmission functions want to receive.
        """
        self.adapter = func

    def add_state(self, name, arrival_handler, handler, end_state=False):
        name = name.upper()
        self.arrival_handlers[name] = arrival_handler
        self.handlers[name] = handler
        if end_state:
            self.endStates.append(name)

    def set_start(self, name):
        self.state = name.upper()

    def pump(self, cargo):
        """Feed a value to the state machine. This is handled by the
        handler method associated with the current state. Potentially,
        this moves us to a new state which is returned by the handler.

        If a value is to be returned by pump(), then it can be set
        in the property pump_return_value. This will be accessed
        before the arrival_handler for the new state but returned
        after the arrival_handler
        """
        if self.state in self.endStates:
            return

        try:
            handler = self.handlers[self.state]
        except IndexError:
            raise FSMError('No transition for state ' + str(self.state))
        if not self.endStates:
            raise  FSMError('Must have at least one end_state.')

        if self.adapter is not None:
            cargo = self.adapter(cargo)
    
        new_state = handler(cargo)

        return_value, self.pump_return_value = self.pump_return_value, None

        self.state = new_state
        try:
            arrival_handler = self.arrival_handlers[self.state]
        except IndexError:
            raise FSMError('No arrival handler for state ' + str(self.state))
        if arrival_handler is not None:
            arrival_handler()

        return return_value
