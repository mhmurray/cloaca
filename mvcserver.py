#!/usr/bin/env python

""" Controls the game state and directs the game.

Handles the basic loop of gameplay - asking for input from the active
player, evaluating the legality of the requested actions, and
manipulating the game state to take that action.
"""

# A state machine - each node is the next spot that the server
# needs input from the client. 
#
# An action stack - in game states, we can stack up actions
# via game rules or special abilities of buildings.
# In particular, since everything happens immediately, actions need
# to be able to handle having other actions triggered within their
# resolution.
#
# A horrible example of this is finishing a Garden with a Bath
# and a Bar in play. The Garden allows many patron actions.
# During each patron action, a client is selected from the pool
# and then it performs its action, potentially completing other
# buildings. After this, the Bar allows another patron to
# enter the clientele, again potentially completing buildings.
#
# In light of this, it's not really an action stack where an action is popped
# off as it resolves. Each action
# is a function, which calls other actions within it. A better 
# description might be an action stack frame. After each action is
# resolved, we back out to the previous frame.
#
# Some reasons not to use the Python stack inspection and instead implement
# our own stack mangement:
#   - Make the path easier to track. The viewer will want to know what's
#     going on.
#
# STATE:
#   1 which player to query
#   2 what info to get
#   3 what to do with that info (stack up game actions)
#   4 how to select the next state
#   5 hooks to tack actions onto this state
#
#   The possible next states can be manipulated by the player input and action 
#   (eg. the leader thinks and there is no option to follow, or a building 
#   is built whose action requires more input from players).
#
#   The hooks let us trigger on being in a specific game state (eg. academy lets
#   you think at the end of the turn)
#
#   Not sure if we need to be able to dynamically change the state objects, like
#   setting the destination state, etc. Ideally, the states are roughly
#   deterministic, looping through people's turns.
#
#
# Example:
#
# STATE(start_of_turn):
#   1 Query active player
#   2 Get action (think or role and cards to lead)
#   3 If lead, place card(s) in camp
#     If thinker, enqueue ACTION(thinker)
#   4 If think, -->STATE(end_turn)
#     If lead, -->STATE(player_follow)
#
#   Because we need to be able to trigger specifically on thinker actions,
#   perform_thinker is a separate action. In principle this could happen
#   to make different atoms. For instance, an ACTION for deciding to think or
#   lead, then states for picking the type of thinker and a state for picking
#   which role to lead. It's a fluid definition.
#
# ACTION(perform_thinker):
#   1 must specify player
#   2 Ask for thinker type. Give them cards.
#   3 hooks : Latrine, Tribunal
#
#
# 
# List of all states and actions:
#
# STATE(start_of_turn) : gets lead or thinker from active player
# STATE(inactive_players_follow) : gets follow or thinker from inactive players
# STATE(role_action) : a player performing his follow/lead.
# STATE(end_turn) : enqueue kids_in_pool
#
# ACTION(lead_role)
# ACTION(perform_thinker)
# ACTION(client_action)
# ACTION(perform_laborer)
# ACTION(perform_craftsman)
# ACTION(perform_merchant)
# ACTION(perform_patron)
# ACTION(perform_legionnary)
# ACTION(perform_architect)
# ACTION(resolve_school) : enqueue a bunch of ACTION(perform_thinker)
# ACTION(resolve_<buildings>) : etc. for all buildings
# ACTION(kids_in_pool) : senate, sewer hooks into this

class Action:
  """ A game action to be performed.
  Do we even need a base class?
  """

  def do_action(self):
    """ Placeholder for subclasses. Should return a status code 
    (or raise an exception).
    """
    pass

class PerformThinkerAction(Action):
  """ Handles thinker action """

  def __init__(self, thinking_player):
    self.thinking_player=thinking_player

  def do_action(self):
    """
    1) If thinking_player has a Latrine, ask for discard.
    2) If thinking_player has a Vomitorium, ask for discard.
    3) Determine # cards that would be drawn. Check hand size,
       Temple, and Shrine. Also check if jacks are empty,
       and if drawing cards would end the game.
    3) Ask thinking_player for thinker type (jack or # cards)
    4) Draw cards for player.
    """
    pass

class LeadRoleAction(Action):
  """ Handles leading a role """
  
  def __init__(self, leading_player):
    self.leading_player = leading_player

  def do_action(self):
    """
    1) Ask for cards used to lead
    2) Check legal leads using these cards (Palace, petition)
    3) Ask for role clarification if necessary
    4) Move cards to camp, set this turn's role that was led.
    """
    pass

class FollowRoleAction(Action):
  """ Handles following a role """

  def __init__(self, following_player, led_role):
    self.following_player = following_player
    self.led_role = led_role

  def do_action(self):
    """
    1) Ask for cards used to follow
    2) Check for ambiguity in ways to follow (Crane, Palace, petition)
    3) Ask for clarification if necessary
    4) Move cards to camp
    """

class PerformLaborerAction(Action):
  """ Performs a laborer action. """

  def __init__(self, player):
    self.player = player

  def do_action(self):
    """
    1) Ask for which card from the pool
    2) Move card from pool
    3) Check for Dock and ask for card from hand
    4) Move card from hand
    """

class PeformPatromAction(Action):
  """ Performs a patron action """

  def __init__(self, player):
    self.player = player

  def do_action(self):
    """
    1) Abort if clientele full (Insula, Aqueduct)
    2) Ask for which card from pool
    3) Check for Bar and Aqueduct and 



class MVCServer:
  """ Manipulates the game state at the requests of registered clients.
  Maintains the "state" of the game, advancing through phases.
  Handles actions that are enqueued by events or player requests.
  """


  def __init__(self, game_state):
    self.game_state = game_state
    self.state = None
    self.action_stack = []




