from twisted.application import internet, service
from twisted.internet import protocol
from twisted.web import resource, server, static
from twisted.protocols.basic import NetstringReceiver
from twisted.python import components
from twisted.internet.protocol import ServerFactory, Protocol
from zope.interface import Interface, implements

from bidict import bidict
from message import GameAction, Command
import message
from server import GTRServer
from error import GTRError, ParsingError, GameActionError
from interfaces import IGTRService, IGTRFactory
import db

import sys
import cgi
import json
import logging
import logging.config
import os
from pickle import dumps
from uuid import uuid4

# For websocket test
sys.path.append("sockjs-twisted")
from txsockjs.factory import SockJSFactory

lg = logging.getLogger('twisted-server')

# Set up logging. See logging.json for config
def setup_logging(
        default_path='logging.json',
        default_level=logging.INFO,
        env_key='GTR_LOG_CFG'):
    """Setup logging configuration
    """
    path = default_path
    value = os.getenv(env_key, None)
    if value is not None:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

class GTRProtocol(NetstringReceiver):
    MESSAGE_ERROR_THRESHOLD = 5

    def __init__(self):
        self.message_errors = 0
        self.uid = None

    def stringReceived(self, request):
        """Receives Command objects of the form <game, action>.
        
        Expects the first command on this protocol to be LOGIN.

        If there is a parsing error, a SERVERERROR command is
        send to the client, but after a number of errors, the
        connection will be closed.
        """
        try:
            command = Command.from_json(request)
        except (ParsingError, GameActionError), e:
            self.message_errors+=1
            if self.message_errors >= self.MESSAGE_ERROR_THRESHOLD:
                self.transport.loseConnection()
            else:
                self.send_command(
                        Command(None, GameAction(message.SERVERERROR, 
                                'Error parsing message.')))
            return

        if self.uid is None:
            if command.action.action == message.LOGIN:
                session_id = command.action.args[0]
                self.uid = self.factory.register(self, session_id)

            if self.uid is None:
                lg.warning('Ignoring message from unauthenticated user')
                return
        else:
            self.factory.handle_command(self.uid, command)

    def send_command(self, command):
        """Send a Command to the client."""
        self.sendString(command.to_json())


class GTRService(service.Service):
    """Service to handle one instance of a GTRServer.
    """
    implements(IGTRService)

    def __init__(self, database):
        self.server = GTRServer(database)
        self.db = database

        self.factory = None
        self.server.send_command =\
                lambda user, command : self.send_command(user, command)

    def register_user(self, uid, userinfo):
        self.server.register_user(uid, userinfo)

    def unregister_user(self, uid, userinfo):
        self.server.unregister_user(uid)

    def send_command(self, user, command):
        """Sends a message to the user if the user exists.
        """
        if self.factory is not None:
            self.factory.send_command(user, command)

    def handle_command(self, user, command):
        return self.server.handle_command(user, command)


class GTRFactoryFromService(protocol.ServerFactory):
    """Handles the connections to clients via GTRProtocol intances.

    Keeps a reference to a factory object that implements IGTRFactory.
    This object is used to communicate with the clients via the method
    GTRFactory.send_command(user, command).
    """

    implements(IGTRFactory)

    protocol = GTRProtocol

    def __init__(self, service):
        self.service = service
        self.service.factory = self

        self.user_to_protocol = {}

    def protocol_from_user(self, user):
        try:
            return self.user_to_protocol[user]
        except KeyError:
            return None

    def register(self, proto, session_id):
        """Register protocol with a session.

        If session id is invalid, return None.
        """
        uid = self.service.db.retrieve_session(session_id)
        if uid is None:
            lg.info('Session id not found: {0!s}'.format(session_id))
            return None
        else:
            lg.debug('Registering uid {0!s}'.format(uid))

        user = self.service.db.retrieve_user(uid)
        try:
            username = user['username']
        except KeyError:
            lg.info('User not found: {0!s}'.format(uid))
            return None

        self.user_to_protocol[uid] = proto
        lg.debug('Registering uid {0!s} as {1!s}'
                .format(uid, username))
        self.service.register_user(uid, {'name': username})

        return uid

    def send_command(self, uid, command):
        """Sends an action to the specified user.
        """
        proto = self.protocol_from_user(uid)
        if proto is None:
            lg.error('Error. Server tried to send a command to user {0!s} '
                    'but the user is not connected.'
                    .format(uid))
        else:
            proto.send_command(command)

    def handle_command(self, uid, command):
        self.service.handle_command(uid, command)


setup_logging()

database = db.connect()
database.store_user('reasgt', 'reasgt')
database.store_user('lexus', 'lexus')

components.registerAdapter(GTRFactoryFromService, IGTRService, IGTRFactory)

application = service.Application('gtr')
s = GTRService(database)
serviceCollection = service.IServiceCollection(application)

root = resource.Resource()

class FormPage(static.File):
    #def render_GET(self, request):
    #    return static.File('./index.html')
    
    def render_POST(self, request):
        return '<html><body>You submitted: %s</body></html>' % (cgi.escape(str(request.args)),)


class GetUser(resource.Resource):

    def __init__(self, db):
        resource.Resource.__init__(self)
        self.db = db

    def render_GET(self, request):
        session_id = request.getSession().uid
        uid = self.db.retrieve_session(session_id)
        lg.debug('User info request from session {0!s}, user {1!s}.'
                .format(session_id, uid))
        return str(uid) if uid is not None else ''


class NoPassLogin(resource.Resource):

    def __init__(self, db):
        resource.Resource.__init__(self)
        self.db = db

    def render_POST(self, request):
        username = cgi.escape(str(request.args['user'][0]))
        lg.info('Login request: {0}'.format(username))

        uid = username
        session = request.getSession()
        self.db.store_session(session.uid, uid)
        lg.debug('Set session id: {0!s} for user {1} ({2!s})'
                .format(session.uid, username, uid))
        session.notifyOnExpire(lambda: self._onExpire(session))
        return username

    def _onExpire(self, session):
        try:
            lg.debug('Expired session {0!s}'
                    .format(session.uid))
            self.db.remove_session(self, session.uid)

        except KeyError:
            lg.debug('Couldn\'t remove session with uid {0!s}'
                    .format(session.uid))


class Logout(resource.Resource):

    def __init__(self, db):
        resource.Resource.__init__(self)
        self.db = db

    def render_GET(self, request):
        session = request.getSession()
        self.db.remove_session(self, session.uid)
        session.expire()
        return 'Logged out session '+ session.uid

root.putChild('hello', SockJSFactory(IGTRFactory(s)))
root.putChild("index", static.File('site/index.html'))
root.putChild("style.css", static.File('site/style.css'))
root.putChild("favicon.ico", static.File('site/favicon.ico'))
root.putChild("js", static.File('site/js'))
root.putChild('user', GetUser(database))
root.putChild('login', NoPassLogin(database))
root.putChild('logout', Logout(database))
site = server.Site(root)

#reactor.listenTCP(5050, site)
#reactor.run()


internet.TCPServer(5000, site).setServiceParent(serviceCollection)
#internet.TCPServer(5000, SockJSFactory(IGTRFactory(s))).setServiceParent(serviceCollection)
#internet.TCPServer(5000, IGTRFactory(s)).setServiceParent(serviceCollection)


# vim: set filetype=python:
