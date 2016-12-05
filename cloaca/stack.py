class Stack(object):
    def __init__(self, stack=None):
        self.stack = stack if stack else []

    def push_frame(self, function_name, *args):
        self.stack.append(Frame(function_name, *args))

    def remove(self, item):
        self.stack.remove(item)

    def __str__(self):
        return str(self.stack)

    def __repr__(self):
        return 'Stack({0!r})'.format(self.stack)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other


class Frame(object):
    def __init__(self, function_name, *args, **kwargs):
        self.function_name = function_name
        self.args = tuple(kwargs.get('args', args))
        self.executed = kwargs.get('executed', False)

    def __str__(self):
        return 'Frame({0})'.format(self.function_name)

    def __repr__(self):
        return 'Frame({0}, args={1})'.format(self.function_name, self.args)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other
