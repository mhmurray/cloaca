#/usr/bin/env python

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
# How to use two actions to start a building.
# Since this can only be done when there are literally two craftsmen in a row
# or two archtects in a row, we need to be able to accept them as a group.
# Here's when we can get multiple actions to start an out-of-town site:
#   - clientele following lead
#   - clientele doubling via Circus Maximus
#   - two clientele of same role
#   - craftsman actions from Amphitheater
#   - multiple lead/follow via Palace
#   - (ambiguous in the rules?) 1 remaining on the Amphitheater, but also a client.
#     Even with clever rearranging, you might not be allowed to start two OOT sites
#     with an Amphitheater for 3 and a followup craftsman client.
#
# In any case, it's hard to process the craftsmen one at a time.
#
# Out-of-town site Option A:
# When starting an out of town site, don't actually use this craftsman - put it in
# reserve and return from the action. When the next craftsman comes up, attempt to
# start a site. In case this fails (no following craftsman action, no sites),
# we have to abort and roll it back.
# We need to be able to roll back actions to some extent anyway, since we want a 
# reasonable chance to undo misclicks and such.
# We can't stack up all craftsman actions ahead of time, since completing a building
# with one could affect how many craftsmen we get (eg. completing Ludus Magna).
# This makes it difficult to check if a craftsman action is coming up.
#
# Out-of-town site Option B:
# The caller must indicate that an out-of-town is allowed. While we can't stack
# up the craftsman actions, we can indicate that multiple in a row will follow if
# the first one is not used to complete or start a building.
# Here's a breakdown of all the possibilities for having extra craftsmen:
#
# 1) leading craftsman - check if we have craftsman client
# 2) clientele doubling via Circus Maximus - check if we've used the double for this
#    craftsman client, or if we have another client
# 3) performing craftsman client - check if we have another
# 4) peforming Amphitheater craftsman - check if we have at least 1 left after this one
# 5) Multiple lead/follow via Palace - check if we have another lead/follow 
# 6) performing last Amphitheater craftsman - check if we have a client.
#
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

def take_turn(self, player):
  """
  1) Ask for thinker or lead
  2) -->ACTION(thinker), -->ACTION(lead_role)
  """
  pass

def perform_thinker_action(self, thinking_player):
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

def lead_role_action(self, leading_player):
  """
  1) Ask for cards used to lead
  2) Check legal leads using these cards (Palace, petition)
  3) Ask for role clarification if necessary
  4) Move cards to camp, set this turn's role that was led.
  """
  pass

def follow_role_action(self, following_player, role):
  """
  1) Ask for cards used to follow
  2) Check for ambiguity in ways to follow (Crane, Palace, petition)
  3) Ask for clarification if necessary
  4) Move cards to camp
  """
  pass

def perform_lead_role(self, leading_player):
  """
  This is the main part of a player's turn. It figures how many actions
  the player gets from leading or following with a card (or cards).
  It then figures out how many clients get to perform their actions and
  activates them in turn. If the number of clients changes, it must be
  tracked here (eg. the first client finishes a Ludus Magna).
  1) Determine if the player gets to perform multiple actions (Palace)
  2) If the role is architect or craftsman, if the player is going
     to get multiples (Palace, clietele) or the have a Tower, set
     out_of_town_allowed=true
  3) While the player has actions {-->ACTION(perform_<role>_action)}
  4) Check how many clientele the player has (Stockpile, Ludus Magna).
  5) While the player has clientele actions { -->ACTION(perform_clientele_action) }
     Have to forward out_of_town_allowed.
  """
  pass

def perform_clientele_action(self, player, role, out_of_town_allowed):
  """
  This function will activate one client. It makes two actions 
  if the player has a Circus Maximus. This function doesn't keep track
  of which clients have been used.
  1) -->ACTION(perform_<role>_action), forwarding out_of_town_allowed to architect/craftsman
  1) If the player has a Circus Maximus, do it again
  """
  pass


def perform_laborer_action(self, player):
  """
  1) Ask for which card from the pool
  2) Move card from pool
  3) Check for Dock and ask for card from hand
  4) Move card from hand
  """
  pass

def peform_patron_action(self, player):
  """
  1) Abort if clientele full (Insula, Aqueduct)
  2) Ask for which card from pool
  3) Check for Bar and Aqueduct and 
  """
  pass

def peform_craftsman_action(self, player, out_of_town_allowed):
  """
  out_of_town_allowed is indicated by the caller if this craftsman would
  be stacked up with another, so that an out-of-town site may be used.
  In that case, this will return an indication and the caller can nix the
  next craftsman action.
  1) Ask for building to start or material to add.
  2) If out_of_town_allowed is false, don't allow out of town, otherwise
     start the out-of-town site and return the indicator.
  3) Check legality of material, building + site.
  4) Place material or building -->ACTION(place_material) -->ACTION(start_building)
  5) Mark flag for "performed craftsman this turn" for Academy
  """
  pass

def peform_legionary_action(self, player, affected_players):
  """
  affected_players must be determined by the caller, accounting for Pallisade, Wall, Bridge
  1) Ask for card to show for demand
  2) Ask for affected players to give card of material, or say "Glory to Rome!"
  3) If player has coliseum, ask for affected players to select client to send to the lions.
  4) If player has bridge, ask affected players for material from stockpile
  """
  pass

def peform_architect_action(self, player, out_of_town_allowed):
  """
  out_of_town_allowed is indicated by the caller if this architect would
  be stacked up with another, so that an out-of-town site may be used.
  In that case, this will return an indication and the caller can nix the
  next architect action.
  1) Ask for building to start or material to add. (Archway, Stairway)
  2) If out_of_town_allowed is false, don't allow out of town, otherwise
     start the out-of-town site and return the indicator.
  3) Check legality of material, building + site.
  4) Place material or building -->ACTION(place_material) -->ACTION(start_building)
  """
  pass

def peform_merchant_action(self, player):
  """
  Do we log materials? We should in case the display messes up,
  but maybe only until end of turn.
  1) Abort if vault full. Also between each step here. (Market)
  2) Ask player to select material from Stockpile. Reveal and place in vault.
  3) If Basilica, ask player to select from hand. No reveal and vault.
  4) If Atrium, ask player to select top of deck. No reveal and vault.
  """
  pass

def kids_in_pool(self, player, players_with_senate):
  """
  Place cards in camp into the pool.
  1) If Sewer, ask to move cards into stockpile.
  2) If dropping a Jack, ask players_with_senate in order.
  """
  pass

def end_turn(self, player):
  """
  Ask for Academy thinker. Need to figure out whether or not Senate goes first.
  """
  pass

def add_material_to_building(self, player, material, source, building):
  """
  Adds a material to a building and checks if the building is complete
  The caller should make sure it's legal.
  1) Add material to building, indicate Stairway separately.
  2) If building is completed, trigger resolve_<building> action
  """
  pass

def resolve_building(self, player, building):
  """ Placeholder for all building resolutions
  """
  pass

class MVCServer:
  """ Manipulates the game state at the requests of registered clients.
  Maintains the "state" of the game, advancing through phases.
  Handles actions that are enqueued by events or player requests.
  """

  def __init__(self, game_state):
    self.game_state = game_state
    self.state = None
    self.action_stack = []

  def run(self):
    """ Main game loop """
    player = initialize_and_get_starting_player()
    take_turn(leader)




