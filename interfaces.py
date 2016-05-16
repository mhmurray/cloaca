from zope.interface import Interface, implements


class IGTRService(Interface):

    def handle_command(user, command):
        """Submit a GameAction to the server
        """

    def register_user(uid, userinfo):
        """Register a dictionary userinfo (eg. dict(name='my_username'))
        with the server.
        """

    def unregister_user(uid, userinfo):
        """Unegister a user id with the server. (Delete user.)
        """


class IGTRFactory(Interface):

    def handle_command(uid, command):
        """Submit a GameAction"""

    def register_user(uid, userinfo):
        """Register a user id with a userinfo dict.
        """

    def unregister_user(uid):
        """Delete a user.
        """

    def register(protocol, session_id):
        """Register a protocol with a specific user
        identified by the session_id using the users database.
        """

    def unregister(protocol):
        """Remove the user and protocol from the protocol-user map.
        """

    def send_command(uid, command):
        """Send a command to a user via the associated protocol instance."""
