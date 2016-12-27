import cloaca.message
from cloaca.message import Command, GameAction
from cloaca.error import ParsingError, GTRDBError, GTRError
from cloaca.server import GTRServer
from cloaca.game_record import GameRecord
import cloaca.db
import cloaca.encode_binary as encode

import tornado
from tornado.web import RequestHandler
from tornado.websocket import WebSocketHandler
from tornado import gen, escape
from tornado.process import cpu_count

from concurrent.futures import ThreadPoolExecutor

import os
import os.path
import logging
import time
import json
import binascii
import bcrypt
import re

SESSION_AUTH_LENGTH_BYTES = 16
SESSION_MAX_AGE_DAYS = 1

lg = logging.getLogger(__name__)

pool = ThreadPoolExecutor(cpu_count())

APPDIR = os.path.dirname(__file__)

class BaseHandler(RequestHandler):
    def initialize(self, database):
        self.db = database

    # RequestHandler.get_current_user cannot be a coroutine so we use
    # prepare to set self.current_user
    # self.current_user is a dictionary with the same fields
    # as the user:<user_id> hash in the database.
    # It is non-None if the user is logged in.
    # Session expiration is handled via expiring Tornado secure cookies.
    @gen.coroutine
    def prepare(self):
        lg.info('Current user: ' + str(self.current_user))
        if self.current_user is not None:
            lg.debug('Current user logged in {0}'.format(self.current_user['username']))
            return
        else:
            lg.debug('Not logged in.')
            cookie_session_auth = self.get_secure_cookie('session_auth',
                    max_age_days=SESSION_MAX_AGE_DAYS)
            if not cookie_session_auth:
                lg.debug('No cookie available')
                return

            user_id = yield self.db.retrieve_userid_from_session_auth(cookie_session_auth)
            if user_id is not None:
                lg.debug('User id from cookie session: {0}'.format(user_id))
                user_session_auth = yield self.db.retrieve_user_session_auth(user_id)
                if cookie_session_auth == user_session_auth:
                    # Cookie matches stored session - load user info
                    user_dict = yield self.db.retrieve_user(user_id)
                    self.current_user = user_dict
                    self.current_user['user_id'] = user_id
                    lg.debug('Set current user {0}'.format(self.current_user['username']))

                    # Update login time.
                    yield self.db.update_user_last_login(
                            user_id,
                            int(time.mktime(time.gmtime()))
                            )
                    return


class CreateGameHandler(BaseHandler):
    def initialize(self, database, server):
        super(CreateGameHandler, self).initialize(database)
        self.server = server


    @tornado.web.authenticated
    @gen.coroutine
    def get(self):
        user_id = self.current_user['user_id']
        game_id = yield self.server.create_game(user_id)

        self.redirect('/')
        return


class JoinGameHandler(BaseHandler):
    def initialize(self, database, server):
        super(JoinGameHandler, self).initialize(database)
        self.server = server


    @tornado.web.authenticated
    @gen.coroutine
    def get(self, game_id):
        user_id = self.current_user['user_id']
        game_id = yield self.server.join_game(user_id, game_id)

        self.redirect('/')
        return


class StartGameHandler(BaseHandler):
    def initialize(self, database, server):
        super(StartGameHandler, self).initialize(database)
        self.server = server


    @tornado.web.authenticated
    @gen.coroutine
    def get(self, game_id):
        user_id = self.current_user['user_id']

        game = yield self.server.start_game(user_id, game_id)

        for p in game.players:
            try:
                client_cxn = GameWSHandler.client_cxn_by_user_id[p.uid]
            except KeyError:
                pass
            else:
                resp = Command(game_id, None, GameAction(cloaca.message.STARTGAME))
                client_cxn.send_command(resp)

        self.redirect('/')
        return


class GameHandler(BaseHandler):
    """Handler to serve HTML for a single game.

    The path to minified CSS and JS files can be provided, but by default
    the cloaca/site/main.js will be used for data-main with require.js.
    """
    def initialize(self, database, server, websocket_uri,
            stylesheet_path=None, js_main_path=None):
        super(GameHandler, self).initialize(database)
        self.server = server
        self.websocket_uri = websocket_uri
        self.stylesheet_path = '/style.css' if stylesheet_path is None else stylesheet_path
        self.js_main_path = '/js/main' if js_main_path is None else js_main_path


    @tornado.web.authenticated
    @gen.coroutine
    def get(self, game_id):
        user_id = self.current_user['user_id']

        # Render with ws-uri so that a proxy will re-write the websocket URI.
        self.render('site/templates/game.html',
                game_id=game_id,
                username=self.current_user['username'],
                websocket_uri=self.websocket_uri,
                data_main_path=self.js_main_path,
                stylesheet_path=self.stylesheet_path
                )


class GameListHandler(BaseHandler):

    @tornado.web.authenticated
    @gen.coroutine
    def get(self):
        N_GAMES_TO_RETRIEVE = 100
        game_ids = yield self.db.retrieve_latest_games(N_GAMES_TO_RETRIEVE)
        games_encoded = yield self.db.retrieve_games(game_ids)

        records = []
        for game_encoded in games_encoded:
            if game_encoded is None:
                continue
            try:
                game = encode.str_to_game(game_encoded)
            except encode.GTREncodingError as e:
                lg.debug('Error decoding game JSON.')
                continue

            players = [p.name for p in game.players]
            started = game.started
            host = game.host
            records.append(GameRecord(game.game_id, players, started, host))

        self.render('site/templates/game_list.html',
                username=self.current_user['username'],
                game_records=records)


class LoginPageHandler(BaseHandler):
    def get(self):
        error = self.get_argument('error', None)
        error_msg = escape.url_unescape(error) if error else ''
        self.render('site/templates/tornado_login_form.html', error=error_msg)


class RegisterHandler(BaseHandler):
    @gen.coroutine
    def post(self):
        try:
            username = self.get_argument('username')

            # TODO: replace with JWT from OpenID Connect
            auth = self.get_argument('auth')
            authrepeat = self.get_argument('authrepeat')
        except tornado.web.MissingArgumentError:
            self.write('Must specify username and auth.')
            return

        error = None
        if re.match('^[\w-]+$', username) is None:
            error = 'Usernames may only be letters, numbers, hyphens and underscores.'

        elif len(username) > 20 or len(username) < 3:
            error = 'Usernames must be between 3 and 20 characters long.'

        elif auth != authrepeat:
            error = 'Passwords do not match.'

        if error is not None:
            self.redirect('/login?error={0}'.format(escape.url_escape(error)))
            return

        user_id = yield self.db.retrieve_user_id_from_username(username)
        if user_id is not None:
            self.redirect('/login?error={0}'
                    .format(escape.url_escape('Username {0} already in use.'
                            .format(username))))
            return
        else:
            hashed_auth = yield pool.submit(
                    bcrypt.hashpw, auth.encode('utf-8'), bcrypt.gensalt())

            user_id = yield self.db.add_user(username, hashed_auth)
            if user_id is None:
                self.redirect('/login?error={0}'
                        .format(escape.url_escape('Username {0} already in use.'
                                .format(username))))
            else:
                session_auth = generate_session_token()
                yield self.db.update_user_session(user_id, session_auth)
                self.set_secure_cookie('session_auth', session_auth,
                        expires_days=SESSION_MAX_AGE_DAYS)
                self.redirect('/')


class AuthenticateHandler(BaseHandler):
    @gen.coroutine
    def post(self):
        try:
            username = self.get_argument('username')

            # TODO: replace with JWT from OpenID Connect
            auth = self.get_argument('auth')
        except tornado.web.MissingArgumentError:
            self.write('Must specify username and auth.')
            return

        user_id = yield self.db.retrieve_user_id_from_username(username)
        if user_id is None:
            self.redirect('/login?error={0}'
                    .format(escape.url_escape('Unknown username or password.')))
        else:
            user_auth = yield self.db.retrieve_user_auth(user_id)
            hashed_auth = yield pool.submit(
                    bcrypt.hashpw, auth.encode('utf-8'), user_auth.encode('utf-8'))

            if user_auth == hashed_auth:
                session_auth = yield self.db.retrieve_user_session_auth(user_id)
                self.set_secure_cookie('session_auth', session_auth,
                        expires_days=SESSION_MAX_AGE_DAYS)
                self.redirect('/')
            else:
                self.redirect('/login?error={0}'
                        .format(escape.url_escape(
                            'Unknown username or password.')))


class LogoutHandler(BaseHandler):

    @gen.coroutine
    def get(self):
        if self.current_user is not None:
            new_session_auth = generate_session_token()
            yield self.db.update_user_session(
                    self.current_user['user_id'], new_session_auth)

        self.redirect('/')


def generate_session_token():
    return binascii.hexlify(os.urandom(SESSION_AUTH_LENGTH_BYTES))


class GameWSHandler(WebSocketHandler):
    MESSAGE_ERROR_THRESHOLD = 5

    # Mapping user ID to instance of this class.
    client_cxn_by_user_id = {}

    #TODO: This is repeated in BaseHandler. Can we mix it in for WSs and regular requests?
    # RequestHandler.get_current_user cannot be a coroutine so we use
    # prepare to set self.current_user
    # self.current_user is a dictionary with the same fields
    # as the user:<user_id> hash in the database.
    # It is non-None if the user is logged in.
    # Session expiration is handled via expiring Tornado secure cookies.
    @gen.coroutine
    def prepare(self):
        if self.current_user is not None:
            lg.debug('Current user logged in {0}'.format(self.current_user['username']))
            return
        else:
            lg.debug('Not logged in.')
            cookie_session_auth = self.get_secure_cookie('session_auth',
                    max_age_days=SESSION_MAX_AGE_DAYS)
            if not cookie_session_auth:
                lg.debug('No cookie available')
                return

            user_id = yield self.db.retrieve_userid_from_session_auth(cookie_session_auth)
            if user_id is not None:
                lg.debug('User id from cookie session: {0}'.format(user_id))
                user_session_auth = yield self.db.retrieve_user_session_auth(user_id)
                if cookie_session_auth == user_session_auth:
                    # Cookie matches stored session - load user info
                    user_dict = yield self.db.retrieve_user(user_id)
                    self.current_user = user_dict
                    self.current_user['user_id'] = user_id
                    lg.debug('Set current user {0}'.format(self.current_user['username']))

                    # Update login time.
                    yield self.db.update_user_last_login(
                            user_id,
                            int(time.mktime(time.gmtime()))
                            )
                    return


    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        if self.current_user is None:
            self.set_status(401)
            self.finish("Unauthorized")
        else:
            super(GameWSHandler, self).get(*args, **kwargs)


    def initialize(self, server, database):
        self.message_error_count = 0
        self.server = server
        self.db = database


    def open(self):
        user_id = self.current_user['user_id']
        GameWSHandler.client_cxn_by_user_id[user_id] = self


    def on_close(self):
        user_id = self.current_user['user_id']
        del GameWSHandler.client_cxn_by_user_id[user_id]


    @gen.coroutine
    def on_message(self, message):
        lg.debug('WS handler received message: '+str(message))
        try:
            commands = Command.from_json(message)
        except ParsingError as e:
            self.message_error_count += 1
            if self.message_error_count >= self.MESSAGE_ERROR_THRESHOLD:
                self.close()
            else:
                self.send_command(
                        Command(None, None, GameAction(cloaca.message.SERVERERROR, 
                                'Error parsing message: '+e.message)))
            return
        else:
            user_id = self.current_user['user_id']
            game_id = commands[0].game
            if commands[0].action.action == cloaca.message.LOGIN:
                lg.debug('Ignoring deprecated LOGIN message.')
            elif commands[0].action.action == cloaca.message.REQGAMESTATE:
                lg.debug('Received request for game {0!s}.'.format(game_id))
                try:
                    game_encoded = yield self.server.get_game_data(user_id, game_id)
                except GTRError as e:
                    lg.debug('Sending error')
                    self.send_error(e.message)
                else:
                    resp = Command(game_id, None, GameAction(cloaca.message.GAMESTATE, game_encoded))
                    lg.debug('Sending game '+str(game_id))
                    self.send_command(resp)
            elif commands[0].action.action == cloaca.message.REQGAMELOG:
                lg.debug('Received request for log game {0!s}.'.format(game_id))
                n_messages, n_start = commands[0].action.args
                yield self.server.retrieve_and_send_log_messages(
                        user_id, game_id, n_messages, n_start)
            else:
                yield self.server.handle_game_actions(
                        game_id, user_id, [[c.number, c.action] for c in commands])


    def send_command(self, command):
        self.write_message(command.to_json())

    def send_error(self, msg):
        resp = Command(None, None, GameAction(cloaca.message.SERVERERROR, msg))
        self.send_command(resp)
