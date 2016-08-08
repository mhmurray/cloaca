#!/usr/bin/env python

import functools

import tornadis
import tornado

import db
from cloaca.game import Game
from cloaca.error import GTRDBError

g = Game()
client = db.connect()

#client = tornadis.Client(host='localhost', port=6379, autoconnect=True)
@tornado.gen.coroutine
def set_get():
    result = yield client.store_game(4, g)
    if isinstance(result, tornadis.TornadisException):
        print 'got exception' + str(result)
    yield client.r.call('GET', 'game:4')

@tornado.gen.coroutine
def ping():
    result = yield client.r.call('PING')
    print result

@tornado.gen.coroutine
def register_user(username):
    try:
        #user_id = yield client.register_user(username)
        user_id = yield client.add_user(username, 'password')
    except GTRDBError as e:
        print e.message
    else:
        print 'Registered user', username, 'as user id', user_id
        raise tornado.gen.Return(user_id)

@tornado.gen.coroutine
def eval_sha_error():
    sha = 'ffffffffffffffffffffffffffffffffffffffff'
    result = yield client.r.call('EVALSHA', sha, 0)

    if isinstance(result, tornadis.exceptions.ClientError):
        print 'Error:', result.message
        raise result
    else:
        print 'Result:', result, '(type ', type(result), ')'

@tornado.gen.coroutine
def eval_sha():
    script = 'return false'
    sha = yield client.r.call('SCRIPT', 'LOAD', script)
    print 'Registered "{0}" script with SHA'.format(script), sha
    result = yield client.r.call('EVALSHA', sha, 0)
    print 'Result:', result, '(type ', type(result), ')'


@tornado.gen.coroutine
def main():
    print "Loading scripts"
    yield client.load_scripts()

    #result = yield eval_sha_error()
    #result = yield eval_sha()
    user_id = yield register_user('reasgt')
    user_id = yield register_user('lexus')

if __name__ == '__main__':
    loop = tornado.ioloop.IOLoop.instance()
    loop.run_sync(main)


