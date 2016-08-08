#!/usr/bin/env python

from cloaca.server import GTRServer
from cloaca.error import GTRError
from cloaca.game_record import GameRecord
from cloaca.message import GameAction, Command
import cloaca.message as m

from test_setup import simple_two_player

import unittest
from uuid import uuid4
import json

class TestServer(unittest.TestCase):
    """Test basic GTRServer functions.
    """

    def test_register_user(self):
        s = GTRServer()
        uid1 = uuid4().int

        s.register_user(uid1, dict(name='p1'))

        userinfo1 = s._userinfo(uid1)
        self.assertEqual(userinfo1['name'], 'p1')


    def test_register_user_twice(self):
        """Overwrites the userinfo dict.
        """
        s = GTRServer()
        uid1 = uuid4().int

        s.register_user(uid1, dict(name='p1'))

        userinfo1 = s._userinfo(uid1)
        self.assertEqual(userinfo1['name'], 'p1')

        s.register_user(uid1, dict(name='p2'))

        userinfo1 = s._userinfo(uid1)
        self.assertEqual(userinfo1['name'], 'p2')


    def test_get_nonexistent_userinfo(self):
        s = GTRServer()

        with self.assertRaises(KeyError):
            s._userinfo(uuid4().int)


    def test_unregister_user(self):
        s = GTRServer()
        uid1 = uuid4().int

        s.register_user(uid1, dict(name='p1'))

        self.assertEqual(s._userinfo(uid1)['name'], 'p1')

        s.unregister_user(uid1)

        with self.assertRaises(KeyError):
            s._userinfo(uid1)


    def test_unregister_nonexistent_user(self):
        """Unregistering a non-existent user is a no-op.
        """
        s = GTRServer()
        uid1 = uuid4().int

        s.unregister_user(uid1)


class TestServerCommands(unittest.TestCase):

    def get_response(self, i):
        """Get the i'th response and return (user, game, action, args).

        Like list indices, if i is negative, it counts from the end of the list
        backwards.
        """
        try:
            tup = self.responses[i]
        except IndexError:
            print "Response", i, "doesn't exist."
            raise

        return tup[0], tup[1].game, tup[1].action.action, tup[1].action.args


    def setUp(self):
        """Set up a server with two players registered.

        The server's send command is redirected to a buffer self.responses.
        Entries are tuples of (user, command).
        """
        self.s = GTRServer()
        self.uid1 = uuid4().int
        self.uid2 = uuid4().int

        self.s.register_user(self.uid1, dict(name='p1'))
        self.s.register_user(self.uid2, dict(name='p2'))

        self.responses = []
        self.s.send_command = lambda user, resp: self.responses.append((user,resp))


    def test_gamelist(self):
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQGAMELIST)))

        user, game, action, args = self.get_response(0)

        self.assertEqual(user, self.uid1)
        self.assertIsNone(game)
        self.assertEqual(action, m.GAMELIST)
        self.assertEqual(len(args), 1)

        records = json.loads(args[0])

        self.assertEqual(records, [])


    def test_create_game(self):
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQCREATEGAME)))
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQGAMELIST)))

        user, game, action, args = self.get_response(0)

        self.assertEqual(user, self.uid1)
        self.assertEqual(game, 0)
        self.assertEqual(action, m.JOINGAME)
        self.assertEqual(len(args), 0)

        user, game, action, args = self.get_response(1)

        self.assertEqual(user, self.uid1)
        self.assertIsNone(game)
        self.assertEqual(action, m.GAMELIST)
        self.assertEqual(len(args), 1)

        records = map(lambda t: GameRecord(**t), json.loads(args[0]))
        
        self.assertEqual(len(records), 1)

        record = records[0]

        self.assertEqual(record.game_id, 0)
        self.assertEqual(record.players, ['p1'])
        self.assertEqual(record.started, False)
        self.assertEqual(record.host, self.uid1)


    def test_create_two_games(self):
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQCREATEGAME)))
        self.s.handle_command(self.uid2, Command(None, GameAction(m.REQCREATEGAME)))
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQGAMELIST)))

        user, game, action, args = self.get_response(-1)

        self.assertEqual(user, self.uid1)
        self.assertIsNone(game)
        self.assertEqual(action, m.GAMELIST)
        self.assertEqual(len(args), 1) # one JSON string

        records = map(lambda t: GameRecord(**t), json.loads(args[0]))
        
        self.assertEqual(len(records), 2) # two games

        record = records[0]

        self.assertEqual(record.game_id, 0)
        self.assertEqual(record.players, ['p1'])
        self.assertEqual(record.started, False)

        record = records[1]

        self.assertEqual(record.game_id, 1)
        self.assertEqual(record.players, ['p2'])
        self.assertEqual(record.started, False)


    def test_join_game(self):
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQCREATEGAME)))
        self.s.handle_command(self.uid2, Command(0, GameAction(m.REQJOINGAME)))

        user, game, action, args = self.get_response(-1)

        self.assertEqual(user, self.uid2)
        self.assertEqual(game, 0)
        self.assertEqual(action, m.JOINGAME)
        self.assertEqual(args, [])

        self.s.handle_command(self.uid2, Command(0, GameAction(m.REQGAMELIST)))

        user, game, action, args = self.get_response(-1)

        records = map(lambda t: GameRecord(**t), json.loads(args[0]))
        
        self.assertEqual(len(records), 1)

        record = records[0]

        self.assertEqual(record.game_id, 0)
        self.assertEqual(record.players, ['p1', 'p2'])
        self.assertEqual(record.started, False)


    def test_start_game(self):
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQCREATEGAME)))
        self.s.handle_command(self.uid1, Command(0, GameAction(m.REQSTARTGAME)))

        # REQSTARTGAME has two respones: STARTGAME then GAMESTATE
        user, game, action, args = self.get_response(-2)

        self.assertEqual(user, self.uid1)
        self.assertEqual(game, 0)
        self.assertEqual(action, m.STARTGAME)

        user, game, action, args = self.get_response(-1)

        self.assertEqual(user, self.uid1)
        self.assertEqual(game, 0)
        self.assertEqual(action, m.GAMESTATE)
        self.assertEqual(len(args), 1) # GameState JSON
        gs_dict = json.loads(args[0]) # Ensure valid JSON

        self.s.handle_command(self.uid1, Command(0, GameAction(m.REQGAMELIST)))

        user, game, action, args = self.get_response(-1)

        records = map(lambda t: GameRecord(**t), json.loads(args[0]))
        
        self.assertEqual(len(records), 1)

        record = records[0]

        self.assertEqual(record.game_id, 0)
        self.assertEqual(record.players, ['p1'])
        self.assertEqual(record.started, True)

    
    def test_gamestate(self):
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQCREATEGAME)))
        self.s.handle_command(self.uid1, Command(0, GameAction(m.REQSTARTGAME)))
        self.s.handle_command(self.uid1, Command(0, GameAction(m.REQGAMESTATE)))

        user, game, action, args = self.get_response(-1)

        self.assertEqual(user, self.uid1)
        self.assertEqual(game, 0)
        self.assertEqual(action, m.GAMESTATE)
        self.assertEqual(len(args), 1)

        gs_dict = json.loads(args[0])
        self.assertEqual(gs_dict['turn_number'], 1)


    def test_join_nonexistent_game(self):
        self.s.handle_command(self.uid2, Command(0, GameAction(m.REQJOINGAME)))

        user, game, action, args = self.get_response(0)

        self.assertEqual(user, self.uid2)
        self.assertIsNone(game)
        self.assertEqual(action, m.SERVERERROR)


    def test_join_full_game(self):
        uids = [uuid4().int for i in range(5)]
        for i, uid in enumerate(uids):
            self.s.register_user(uid, {'name': 'p'+str(i+1)})

        self.s.handle_command(uids[0], Command(None, GameAction(m.REQCREATEGAME)))
        for uid in uids[1:]:
            self.s.handle_command(uid, Command(0, GameAction(m.REQJOINGAME)))

        self.s.handle_command(self.uid1, Command(0, GameAction(m.REQJOINGAME)))
        user, game, action, args = self.get_response(-1)

        self.assertEqual(user, self.uid1)
        self.assertIsNone(game)
        self.assertEqual(action, m.SERVERERROR)


    def test_join_running_game(self):
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQCREATEGAME)))
        self.s.handle_command(self.uid1, Command(0, GameAction(m.REQSTARTGAME)))

        self.s.handle_command(self.uid2, Command(0, GameAction(m.REQJOINGAME)))

        user, game, action, args = self.get_response(-1)

        self.assertEqual(user, self.uid2)
        self.assertIsNone(game)
        self.assertEqual(action, m.SERVERERROR)


    def test_join_game_twice(self):
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQCREATEGAME)))

        self.s.handle_command(self.uid1, Command(0, GameAction(m.REQJOINGAME)))

        user, game, action, args = self.get_response(-1)

        self.assertEqual(user, self.uid1)
        self.assertIsNone(game)
        self.assertEqual(action, m.SERVERERROR)


    def test_start_game_not_host(self):
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQCREATEGAME)))
        self.s.handle_command(self.uid2, Command(0, GameAction(m.REQJOINGAME)))
        self.s.handle_command(self.uid2, Command(0, GameAction(m.REQSTARTGAME)))

        user, game, action, args = self.get_response(-1)

        self.assertEqual(user, self.uid2)
        self.assertIsNone(game)
        self.assertEqual(action, m.SERVERERROR)


    def test_start_game_already_started(self):
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQCREATEGAME)))
        self.s.handle_command(self.uid2, Command(0, GameAction(m.REQJOINGAME)))
        self.s.handle_command(self.uid1, Command(0, GameAction(m.REQSTARTGAME)))
        self.s.handle_command(self.uid1, Command(0, GameAction(m.REQSTARTGAME)))

        user, game, action, args = self.get_response(-1)

        self.assertEqual(user, self.uid1)
        self.assertIsNone(game)
        self.assertEqual(action, m.SERVERERROR)


    def test_start_game_not_joined(self):
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQCREATEGAME)))
        self.s.handle_command(self.uid2, Command(0, GameAction(m.REQSTARTGAME)))

        user, game, action, args = self.get_response(-1)

        self.assertEqual(user, self.uid2)
        self.assertIsNone(game)
        self.assertEqual(action, m.SERVERERROR)

    
    def test_handle_action(self):
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQCREATEGAME)))
        self.s.handle_command(self.uid1, Command(0, GameAction(m.REQSTARTGAME)))

        user, game, action, args = self.get_response(-1)

        self.assertEqual(user, self.uid1)
        self.assertEqual(game, 0)
        self.assertEqual(action, m.GAMESTATE)
        self.assertEqual(len(args), 1)

        gs_dict = json.loads(args[0])
        self.assertEqual(gs_dict['expected_action'], m.THINKERORLEAD)

        a = GameAction(m.THINKERORLEAD, True)
        self.s.handle_command(self.uid1, Command(0, a))

        user, game, action, args = self.get_response(-1)

        self.assertEqual(user, self.uid1)
        self.assertEqual(game, 0)
        self.assertEqual(action, m.GAMESTATE)
        self.assertEqual(len(args), 1)

        gs_dict = json.loads(args[0])
        self.assertEqual(gs_dict['expected_action'], m.THINKERTYPE)


    def test_handle_bad_action(self):
        """A bad action will send a SERVERERROR and then the GAMESTATE.
        """
        self.s.handle_command(self.uid1, Command(None, GameAction(m.REQCREATEGAME)))
        self.s.handle_command(self.uid1, Command(0, GameAction(m.REQSTARTGAME)))

        a = GameAction(m.PATRONFROMDECK, True)
        self.s.handle_command(self.uid1, Command(0, a))

        user, game, action, args = self.get_response(-2)

        self.assertEqual(user, self.uid1)
        self.assertEqual(action, m.SERVERERROR)
        self.assertIsNone(game)


    def test_handle_invalid_actions(self):
        """The server doens't handle GAMESTATE, CREATEGAME, etc.
        Those are exclusively server responses sent to the client.
        """
        for game, action, args in [
                (None, m.CREATEGAME, []),
                (0, m.JOINGAME, []),
                (None, m.GAMESTATE, ['notagamestate']),
                (None, m.GAMELIST, ['notagamelist']),
                (None, m.LOGIN, ['0']),
                (0, m.STARTGAME, [])]:

            self.s.handle_command(self.uid1,
                    Command(game, GameAction(action, *args)))

            user, game, action, args = self.get_response(-1)

            self.assertEqual(user, self.uid1)
            self.assertEqual(action, m.SERVERERROR)
            self.assertIsNone(game)


if __name__ == '__main__':
    unittest.main()
