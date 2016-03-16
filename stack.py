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


class Frame(object):
    def __init__(self, function_name, *args):
        self.function_name = function_name
        self.args = args
        self.executed = False

    def __str__(self):
        return 'Frame({0})'.format(self.function_name)

    def __repr__(self):
        return 'Frame({0}, {1})'.format(self.function_name, self.args)
