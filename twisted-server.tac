from twisted.application import internet, service
from twisted.internet import protocol
from twisted.web import resource, server, static
from twisted.web.util import redirectTo, Redirect
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

setup_logging()

# Bi-directional mapping between user id (uid) and session id
users = {};

# Bi-directional mapping between username and user id (uid)
usernames = bidict()

def _username_from_uid(uid):
    global usernames
    return usernames[uid]

def _uid_from_username(username):
    global usernames
    return usernames.inverse[username]

def new_user(uid, username):
    global usernames
    if uid in usernames:
        raise KeyError('UID', uid, 'is already registered'
                'with username', _username_from_uid(uid))
    elif username in usernames.inverse:
        raise KeyError('Username', username, 'is already registered'
                'with uid', _uid_from_username(username))
    else:
        usernames[uid] = username


class GTRProtocol(NetstringReceiver):
    MESSAGE_ERROR_THRESHOLD = 5

    def __init__(self):
        self.message_errors = 0

    def connectionMade(self):
        pass

    def connectionLost(self, reason):
        self.factory.unregister(self)

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

        uid = self.factory.user_from_protocol(self)

        if uid is None:
            if command.action.action == message.LOGIN:
                session_id = command.action.args[0]
                uid = self.factory.register(self, session_id)

            if uid is None:
                lg.warning('Ignoring message from unauthenticated user')
                return
        else:
            self.factory.handle_command(uid, command)

    def send_command(self, command):
        """Send a Command to the client."""
        self.sendString(command.to_json())


class GTRService(service.Service):
    """Service to handle one instance of a GTRServer.
    """
    implements(IGTRService)

    def __init__(self, backup_file=None, load_backup_file=None):
        self.server = GTRServer(backup_file, load_backup_file)

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

        # Bidirectional mapping user-to-protocol. The inverse
        # dictionary has a list of users with the same protocol
        self.user_to_protocol = bidict()
        self.session_user_dict = {}

    def user_from_protocol(self, protocol):
        try:
            return self.user_to_protocol.inverse[protocol][0]
        except KeyError:
            return None

    def protocol_from_user(self, user):
        try:
            return self.user_to_protocol[user]
        except KeyError:
            return None

    def register(self, protocol, session_id):
        """Register protocol as associated with the specified user id.
        This replaces the old protocol silently.
        """
        global users
        try:
            uid = users[session_id]
        except KeyError:
            uid = None
        else:
            self.user_to_protocol[uid] = protocol

        try:
            username = _username_from_uid(uid)
        except KeyError as e:
            lg.exception(e.message)
            return None

        self.service.register_user(uid, {'name': username})

        return uid

    def unregister(self, protocol):
        uid = self.user_from_protocol(protocol)
        if uid is not None:
            del self.user_to_protocol[uid]

    def send_command(self, uid, command):
        """Sends an action to the specified user.
        """
        protocol = self.protocol_from_user(uid)
        if protocol is None:
            username = _username_from_uid(uid)
            lg.error('Error. Server tried to send a command to {0!s}'
                    '({1!s}) but the user is not connected.'
                    .format(username, uid))
        else:
            protocol.send_command(command)

    def handle_command(self, uid, command):
        self.service.handle_command(uid, command)


components.registerAdapter(GTRFactoryFromService, IGTRService, IGTRFactory)

application = service.Application('gtr')
#s = GTRService('tmp/twistd_backup.dat', 'tmp/test_backup2.dat')
s = GTRService('/tmp/twistd_backup.dat', None)
serviceCollection = service.IServiceCollection(application)

root = resource.Resource()

class FormPage(static.File):
    #def render_GET(self, request):
    #    return static.File('./index.html')
    
    def render_POST(self, request):
        return '<html><body>You submitted: %s</body></html>' % (cgi.escape(str(request.args)),)


class GetUser(resource.Resource):
    def render_GET(self, request):
        session_id = request.getSession().uid
        global users
        try:
            uid = users[session_id]
            username = _username_from_uid(uid)
        except KeyError as e:
            lg.exception(e.message)
            return ''

        return username

class NoPassLogin(resource.Resource):
    def render_POST(self, request):
        global users
        username = cgi.escape(str(request.args['user'][0]))
        lg.info('Login request: {0}'.format(username))

        try:
            uid = _uid_from_username(username)
        except KeyError:
            uid = uuid4().int
            lg.debug('Assigning uid to new user: {0!s}'.format(uid))
            try:
                new_user(uid, username)
            except KeyError as e:
                lg.exception(e.message)
                return

        session = request.getSession()
        users[session.uid] = uid
        lg.debug('Set session id: {0!s} for user {1} ({2!s})'
                .format(session.uid, username, uid))
        session.notifyOnExpire(lambda: self._onExpire(session))
        return username

    def _onExpire(self, session):
        global users
        try:
            lg.debug('Expired session {0!s} for user {1!s}'
                    .format(session.uid, users[session.uid]))
            del users[session.uid]
        except KeyError:
            lg.debug('Couldn\'t remove session with uid {0!s}'
                    .format(session.uid))

class MockAuthServerPage(resource.Resource):
    """Fake auth server to test OIDC."""

    def render_POST(self, request):
        resp_type = request.args['response_type'][0]
        client_id = request.args['client_id'][0]
        redirect_uri = request.args['redirect_uri'][0]
        response_mode = request.args['response_mode'][0]
        scope = request.args['scope'][0]
        state = request.args['state'][0]
        nonce = request.args['nonce'][0]

        print str(request.args)
        if scope.find('openid') == -1:
            return 'Error forming OpenID request : scope does not contain "openid"'
        else:
            jwt = 'test token'

            page = ('<h1>OpenID Connect Request</h1><p>{0} requests access to {1}. Okay?</p>'
                    '<form action="{2}", method="post">'
                        '<input type="submit" value="Allow access"></input>'
                        '<input type="hidden" name="id_token" value="{3}"</input>'
                        '<input type="hidden" name="state" value="{4}"</input>"'
                    '</form>'
                    .format(client_id, scope, redirect_uri, jwt, state))

            print page
            return page

    render_GET = render_POST

class MockLoginPage(resource.Resource):
    """Login page that uses OIDC on the simulated MockAuthServerPage."""
    
    def render_GET(self, request):
        state = 'gen_random_state'
        nonce = 'gen_random_nonce'

        url = ('/mockauth'
            '?client_id=MockLogin'
            '&response_type=id_token'
            '&scope=openid email'
            '&redirect_uri=/mocklogincallback'
            '&response_mode=form_post'+\
            '&state={0}'
            '&nonce={1}'
            .format(state, nonce))

        return redirectTo(url, request)

class MockLoginCallbackPage(resource.Resource):
    """Callback for the mock OIDC auth provider to send the JWT."""

    def render_POST(self, request):
        print str(request.args)
        id_token = request.args['id_token'][0]
        state = request.args['state'][0]

        if state != 'get_random_state':
            return ('Got token, but state does not match.'
                    '<br>token: {0}<br>state: {1}'
                    .format(id_token, state))
        else:
            return ('Got token, and valid "state".'
                    '<br>token: {0}<br>state: {1}'
                    .format(id_token, state))

class Logout(resource.Resource):
    def render_GET(self, request):
        global users
        session = request.getSession()
        session.expire()
        return 'Logged out session '+ session.uid

root.putChild('hello', SockJSFactory(IGTRFactory(s)))
root.putChild("index", static.File('site/index.html'))
root.putChild("style.css", static.File('site/style.css'))
root.putChild("favicon.ico", static.File('site/favicon.ico'))
root.putChild("js", static.File('site/js'))
root.putChild('user', GetUser())
root.putChild('login', NoPassLogin())
root.putChild('logout', Logout())
root.putChild('mockauth', MockAuthServerPage())
root.putChild('mocklogin', MockLoginPage())
root.putChild('mocklogincallback', MockLoginCallbackPage())

site = server.Site(root)

#reactor.listenTCP(5050, site)
#reactor.run()


internet.TCPServer(5000, site).setServiceParent(serviceCollection)
#internet.TCPServer(5000, SockJSFactory(IGTRFactory(s))).setServiceParent(serviceCollection)
#internet.TCPServer(5000, IGTRFactory(s)).setServiceParent(serviceCollection)


# vim: set filetype=python:
