# cloaca

## MHM, 27 Aug

Some structure planning to incorporate the cmd python module as a simple
interpreter.

## Using the cmd python module

Cmd interpreter is used to query for an action. To do it simply, there is a 
loop in the client that waits for our turn, then when it needs to know what 
action to take, it runs the Cmd loop to figure out what we want to do.
In order to preserve command-line history, allow for access to help, 
etc. when we don't have priority, we might leave the Cmd interpreter running, 
but all of the commands check if we have priority before doing anything.

Cmd interpreter : "thinker for a Jack", checks if we have priority, then
calls clienthooks.ThinkerForAJack().

clienthooks appends information like which player is calling
this ThinkerForAJack() method, and makes the request to the server to
take this action.

The server checks the legality of this, does the appropriate action or returns
an error to the client.

The stack trace would look like this:

 #1 cmd.do_thinker()  
 #2 clienthooks.ThinkerForAJack()  
 #3 clienthooks.server_hook.ServerRequest(THINKER_FOR_A_JACK, PLAYER1)  
 #4 server.MoveCardBetweenZones('Jack', gamestate.jackpile, gamestate.players[1].hand)  

## The setup for this model would look like this

### Possibly on a remote machine

server = Server() # Creates new Game object, which makes the gamestate object

### Locally:

```
server_hook = ServerHook(server) # however we connect, maybe ip address, socket  
client_hook = clienthooks.connect(server_hook, player_name)  
cmd_interpreter = CloacaCmd(client_hook)  
cmd_interpreter.cmdloop('Welcome to Cloaca!')  
```

## A more distributed model

Each of the client, server, and command interpreter runs its own loop.

### ClientLoop()

```
while IsNotOurTurn():  
  server_hook.GetPublicGameState()  
while NoCommandProvided():  
  cmd_interpreter_hook.GetCommandRequest()  
server_hook.ExecuteCommand(client_command)  
```
