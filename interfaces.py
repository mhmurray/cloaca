from zope.interface import Interface, implements


class IGTRService(Interface):

    def handle_action(user, game, action):
        """Submit a GameAction to the server
        """


class IGTRFactory(Interface):

    def handle_action(user, game, action):
        """Submit a GameAction"""

    def register(protocol, user):
        """Log a user in by registering the protocol."""

    def send_action(user, action):
        """Send a command to a user via the associated protocol instance."""
