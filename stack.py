class Stack(object):
    def __init__(self, stack=None):
        self.stack = stack if stack else []

    def push_frame(self, function_name, *args):
        self.stack.append(Frame(function_name, *args))

class Frame(object):
    def __init__(self, function_name, *entry_args):
        self.function_name = function_name
        self.entry_args = entry_args
        self.executed = False

    def __str__(self):
        return 'Frame({0})'.format(self.name)

