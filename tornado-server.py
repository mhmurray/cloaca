#!/usr/bin/env python

import cloaca.message
from cloaca.message import Command, GameAction
from cloaca.error import ParsingError, GTRDBError
from cloaca.server import GTRServer
import cloaca.db

import tornado.ioloop
from tornado.web import RequestHandler, StaticFileHandler
from tornado.websocket import WebSocketHandler
from tornado import gen
from tornado import escape
from tornado.process import cpu_count
from concurrent.futures import ThreadPoolExecutor

import os
import os.path
import logging
import logging.config
import base64
import datetime
import time
import json
import binascii
import bcrypt
import re

SESSION_AUTH_LENGTH_BYTES = 16

lg = logging.getLogger('twisted-server')

pool = ThreadPoolExecutor(cpu_count())

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
            cookie_session_auth = self.get_secure_cookie('session_auth')
            if not cookie_session_auth:
                lg.debug('No cookie available')
                return

            user_id = yield self.db.retrieve_userid_from_session_auth(cookie_session_auth)
            if user_id is not None:
                lg.debug('User id from cookie session: {0}'.format(user_id))
                user_session_auth = yield self.db.retrieve_user_session_auth(user_id)
                if cookie_session_auth == user_session_auth:
                    # Cookie matches stored session - load user info
                    user_hash_list = yield self.db.retrieve_user(user_id)
                    # Tornadis returns a list of strings, like Redis does, without
                    # converting to a dictionary.
                    self.current_user = dict(zip(user_hash_list[::2], user_hash_list[1::2]))
                    self.current_user['user_id'] = user_id
                    lg.debug('Set current user {0}'.format(self.current_user['username']))

                    # Update login time.
                    yield self.db.update_user_last_login(
                            user_id,
                            int(time.mktime(time.gmtime()))
                            )
                    return


class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.write('<html><body>')
        self.write('Hello, {0}!<br>'.format(self.current_user['username']))
        self.write('<a href="/logout">Logout</a>')


class LoginPageHandler(BaseHandler):
    def get(self):
        error = self.get_argument('error', None)
        error_msg = escape.url_unescape(error) if error else ''
        self.render('tornado_login_form.html', error=error_msg)


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
                expires = int(time.mktime(time.gmtime())) + 86400
                self.set_secure_cookie('session_auth', session_auth, expires=expires)
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
                expires = int(time.mktime(time.gmtime())) + 86400
                self.set_secure_cookie('session_auth', session_auth,
                        expires=expires)
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


class MyWSHandler(WebSocketHandler):
    MESSAGE_ERROR_THRESHOLD = 5

    def initialize(self, service):
        self.message_error_count = 0
        self.uid = None

        self.service = service

    def on_message(self, message):
        try:
            command = Command.from_json(message)
        except ParsingError as e:
            self.message_error_count += 1
            if self.message_error_count >= self.MESSAGE_ERROR_THRESHOLD:
                self.close()
            else:
                self.send_command(
                        Command(None, GameAction(message.SERVERERROR, 
                                'Error parsing message.')))
            return
        else:
            if command.action.action == message.LOGIN:
                self.handle_login(command)
            else:
                self.server.handle_command(self.uid, command)


    def on_close(self):
        pass


    def handle_login(self, command):
        session_id = command.action.args[0]
        self.uid = self.service.register(self, session_id)

        if self.uid is None:
            lg.warning('Ignoring message from unauthenticated user')

    def send_command(self, command):
        self.write_message(command.to_json())


def make_app():
    path = os.path.dirname(__file__)
    site_path = os.path.join(path, 'site')
    database = cloaca.db.connect()
    ioloop = tornado.ioloop.IOLoop.current()
    ioloop.run_sync(database.load_scripts)

    service = GTRServer(database)
    return tornado.web.Application([
        (r'/(favicon.ico)', tornado.web.StaticFileHandler, {'path':site_path}),
        (r'/', MainHandler, {'database':database}),
        (r'/', MyWSHandler),
        (r'/register', RegisterHandler, {'database': database}),
        (r'/login', LoginPageHandler, {'database': database}),
        (r'/auth', AuthenticateHandler, {'database': database}),
        (r'/register', RegisterHandler, {'database': database}),
        (r'/logout', LogoutHandler, {'database': database}),
        ],
        cookie_secret='__TODO:_GENERATE_COOKIE_SECRET__',
        login_url='/login',
        xsrf_cookies=True)

if __name__ == '__main__':
    app = make_app()
    app.listen(5001)
    tornado.ioloop.IOLoop.current().start()
