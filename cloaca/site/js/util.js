define(['jquery', 'jqueryui'],
function($){
    var util = {
        _cardDictionary: {},
        _cardList: [],

        Action: {}
    };

    /* "Turn off" the jQuery objects provided.
     * For Buttons, this is .prop('disabled', true), and
     * for all elements it's .off('click').
     */
    util.off = function() {
        for(var i=0; i<arguments.length; i++) {
            var o = arguments[i];
            if(o.prop('tagName') === 'BUTTON') {
                o.prop('disabled', true);
            }
            o.off('click');
        }
    };

    /* Taking a jQuery Object of card elements with
     * ids corresponding to eg. 'card15', return
     * an array of ids as integers.
     */
    util.extractCardIds = function($cards) {
        return $.map($cards, function(item) {
            return $(item).data('ident');
        });
    };

    /* Taking a jQuery Object of card elements with
     * ids corresponding to eg. 'card15', return
     * an array of card names as strings.
     */
    util.extractCardNames = function($cards) {
        return $.map($cards, function(item) {
            return $(item).data('name');
        });
    };

    /* Taking a jQuery Object of card elements with
     * ids corresponding to eg. 'card15', return
     * an array of card properties dictionaries.
     */
    util.extractCardProperties = function($cards) {
        return $.map($cards, function(item) {
            return util.cardProperties($(item).data('name'));
        });
    };

    util.roleToMaterial = function(role) {
        return {
            Laborer: 'Rubble',
            Craftsman: 'Wood',
            Architect: 'Concrete',
            Legionary: 'Brick',
            Merchant: 'Stone',
            Patron: 'Marble'
        }[role];
    }

    util.materialToRole = function(material) {
        return {
            Rubble: 'Laborer',
            Wood: 'Craftsman',
            Concrete: 'Architect',
            Brick: 'Legionary',
            Stone: 'Merchant',
            Marble: 'Patron'
        }[material];
    }

    util.materialToValue = function(material) {
        return {
            Rubble: 1,
            Wood: 1,
            Concrete: 2,
            Brick: 2,
            Stone: 3,
            Marble: 3
        }[material];
    }

    /* Return the card name corresponding to this ident number.
     */
    util.cardName = function(ident) {
        if(ident < 0) {
            return 'Orders';
        } else {
            return util._cardList[ident];
        }
    };

    // Return card properties dictionary for key (card name or ident)
    util.cardProperties = function(card) {
        if(typeof(card) === 'string') {
            return util._cardDictionary[card];
        } else {
            return util._cardDictionary[util.cardName(card)];
        }
    };

    // Return a jQuery object representing a card-zone.
    util.makeCardZone = function (id_, title) {
        var $container = $('<div />', {
            id: id_,
            class: 'card-container'
        });
        var $zone = $('<div />', {
            class: 'card-zone',
            text: title
        });
        $zone.append($container);
        return $zone;
    };

    util.makeSite = function(material) {
        return $('<div />', {
            class: 'site ' + material.toLowerCase(),
        }).text(material[0].toUpperCase() + material.slice(1));
    };


    util.playerHasActiveBuilding = function(game, player_index, building) {
        // Player's complete buildings
        var player = game.players[player_index];
        var completeBuildings = [];
        for(var i=0; i<player.buildings.length; i++) {
            if(player.buildings[i].complete) {
                completeBuildings.push(util.cardName(player.buildings[i].foundation));
            }
        }
        var hasComplete = completeBuildings.indexOf(building) > -1;
        if(hasComplete) {return true;}

        // Any player's stairwayed buildings
        var stairwayBuildings = [];
        for(var i=0; i<game.players.length; i++) {
            for(var j=0; j<game.players[i].buildings.length; j++) {
                var the_building = game.players[i].buildings[j];
                if(the_building.stairway_materials.length>0) {
                    stairwayBuildings.push(util.cardName(the_building.foundation));
                }
            }
        }
        var hasStairway = stairwayBuildings.indexOf(building) > -1;
        if(hasStairway) {return true;}
        
        // Player has incomplete marble and gate in above 2
        if(completeBuildings.indexOf('Gate') > -1 || stairwayBuildings.indexOf('Gate') > -1) {
            var buildingIsMarble = util.cardProperties(building).material == 'Marble';

            var marbleMaterials = false;
            for(var i=0; i<player.buildings.length; i++) {
                if(util.cardName(player.buildings[i].foundation) == building) {
                    if(buildingIsMarble) {
                        return true;
                    }
                    for(var j=0; j<player.buildings[i].materials.length; j++) {
                        var material = player.buildings[i].materials[j];
                        if(util.cardProperties(material).material == 'Marble') {
                            marbleMaterials = true;
                            break;
                        }
                    }
                }
            }
            if(marbleMaterials) {return true;}
        }

        return false;
    };

    // Cards are passed by ident as integers.
    util.makeBuilding = function(
        id_, foundation, site, materials, stairwayMaterials, complete) {

        var $container = $('<div />', {
            id: id_,
            class: 'building',
        });

        var cardName = util.cardName(foundation);
        var $foundationCard = util.makeCard(foundation);
        $container.append($foundationCard);

        var foundationMaterial = util.cardProperties(foundation).material;
        var siteMaterial = site;
        var siteClass = site.toLowerCase();

        $container.data({
            ident: foundation,
            materials: [foundationMaterial, siteMaterial],
            complete: complete
        });

        if(typeof(materials) === 'undefined') {
            n_materials = 0
        } else {
            n_materials = materials.length;
        }

        $site = util.makeSite(siteMaterial);
        $site.text(n_materials+'/'+util.materialToValue(site));
        $container.append($site);

        if(typeof(materials) !== 'undefined') {
            $.each(materials, function(i, card) {
                $container.append($('<div />', {
                    class: 'material',
                }).text(util.cardName(card.ident)).addClass(siteClass));
            });
        }
        
        if(typeof(stairwayMaterials) !== 'undefined') {
            $.each(stairwayMaterials, function(i, card) {
                $container.append($('<div />', {
                    class: 'material stairway',
                }).text(util.cardName(card.ident)).addClass(siteClass));
            });
        }
        
        return $container;
    };

    util.makeSitesStack = function(_id, material, nInTown, nOutOfTown) {
        var material_lower = material.toLowerCase();
        return $('<div />', {
                id: _id,
                class: 'site ' + material_lower,
                data: {material: material, inTown : nInTown, outOfTown: nOutOfTown}
        }).append($('<span/>').text(material).addClass('site-title'),
                  $('<span/>').text(nInTown+'/'+nOutOfTown).addClass('site-count'));
    };

    // Return a jQuery object representing a card.
    util.makeCard = function(ident) {
        var $card;
        var name = util.cardName(ident);
        if(ident < 0) {
            $card = $('<div />', {text: 'Card', class: 'card orders'});
        } else if(ident < 6) {
            $card = $('<div />', {id: 'card'+ident, text: 'Jack', class: 'card jack'});
        } else {
            var material = util.cardProperties(name).material.toLowerCase();
            $card = $('<div />', {
                id: 'card'+ident,
                text: name,
                class: 'card ' + material,
            });
        }

        $card.data({ident: ident, name: name})

        return $card;
    };

    util.Action = {
        THINKERORLEAD   :  0,
        USELATRINE      :  1,
        USEVOMITORIUM   :  2,
        PATRONFROMPOOL  :  3,
        BARORAQUEDUCT   :  4,
        PATRONFROMDECK  :  5,
        PATRONFROMHAND  :  6,
        USEFOUNTAIN     :  7,
        FOUNTAIN        :  8,
        LEGIONARY       :  9,
        GIVECARDS       : 10,
        THINKERTYPE     : 11,
        SKIPTHINKER     : 12,
        USESEWER        : 13,
        USESENATE       : 14,
        LABORER         : 15,
        STAIRWAY        : 16,
        ARCHITECT       : 17,
        CRAFTSMAN       : 18,
        MERCHANT        : 19,
        LEADROLE        : 20,
        FOLLOWROLE      : 21,
        REQGAMESTATE    : 22,
        GAMESTATE       : 23,
        SETPLAYERID     : 24,
        REQJOINGAME     : 25,
        JOINGAME        : 26,
        REQCREATEGAME   : 27,
        CREATEGAME      : 28,
        LOGIN           : 29,
        REQSTARTGAME    : 30,
        STARTGAME       : 31,
        REQGAMELIST     : 32,
        GAMELIST        : 33,
        SERVERERROR     : 34,
        PRISON          : 35,
        TAKEPOOLCARDS   : 36
    };

    util._cardDictionary = {
        Orders: {
            text: '',
            material: null,
            value: 0,
            role: null
        },
        Jack: {
            text: 'May be used as any role.',
            material: null,
            value: 0,
            role: null
        },
        Academy: {
            text: 'May perform one THINKER action after turn during which you performed CRAFTSMAN action', 
            material: 'Brick',
            value: 2,
            role: 'Legionary'
        }, 
        Amphitheatre: {
            text: 'May perform one CRAFTSMAN action for each INFLUENCE', 
            material: 'Concrete',
            value: 2,
            role: 'Architect'
        }, 
        Aqueduct: {
            text: 'When performing PATRON action may take client from HAND.  Maximum CLIENTELE x 2', 
            material: 'Concrete',
            value: 2,
            role: 'Architect'
        }, 
        Archway: {
            text: 'When performing ARCHITECT action may take material from POOL', 
            material: 'Brick',
            value: 2,
            role: 'Legionary'
        }, 
        Atrium: {
            text: 'When performing MERCHANT action may take from DECK (do not look at card)', 
            material: 'Brick',
            value: 2,
            role: 'Legionary'
        }, 
        Bar: {
            text: 'When performing PATRON action may take card from DECK', 
            material: 'Rubble',
            value: 1,
            role: 'Laborer'
        }, 
        Basilica: {
            text: 'When performing MERCHANT action may take material from HAND', 
            material: 'Marble',
            value: 3,
            role: 'Patron'
        }, 
        Bath: {
            text: 'When performing PATRON action each client you hire may perform its action once as it enters CLIENTELE', 
            material: 'Brick',
            value: 2,
            role: 'Legionary'
        }, 
        Bridge: {
            text: 'When performing LEGIONARY action may take material from STOCKPILE.  Ignore Palisades.  May take from all opponents', 
            material: 'Concrete',
            value: 2,
            role: 'Architect'
        }, 
        Catacomb: {
            text: 'Game ends immediately.  Score as usual', 
            material: 'Stone',
            value: 3,
            role: 'Merchant'
        }, 
        Circus: {
            text: 'May play two cards of same role as JACK', 
            material: 'Wood',
            value: 1,
            role: 'Craftsman'
        }, 
        'Circus Maximus': {
            text: 'Each client may perform its action twice when you lead or follow its role', 
            material: 'Stone',
            value: 3,
            role: 'Merchant'
        }, 
        Coliseum: {
            text: "When performing LEGIONARY action may take opponent's client and place in VAULT as material",
            material: 'Stone',
            value: 3,
            role: 'Merchant'
        }, 
        Dock: {
            text: 'When performing LABORER action may take material from HAND', 
            material: 'Wood',
            value: 1,
            role: 'Craftsman'
        }, 
        Forum: {
            text: 'One client of each role wins game', 
            material: 'Marble',
            value: 3,
            role: 'Patron'
        }, 
        Foundry: {
            text: 'May perform one LABORER action for each INFLUENCE', 
            material: 'Brick',
            value: 2,
            role: 'Legionary'
        }, 
        Fountain: {
            text: 'When performing CRAFTSMAN action may use cards from DECK.  Retain any unused cards in HAND', 
            material: 'Marble',
            value: 3,
            role: 'Patron'
        }, 
        Garden: {
            text: 'May perform one PATRON action for each INFLUENCE', 
            material: 'Stone',
            value: 3,
            role: 'Merchant'
        }, 
        Gate: {
            text: 'Incomplete MARBLE structures provide FUNCTION', 
            material: 'Brick',
            value: 2,
            role: 'Legionary'
        }, 
        Insula: {
            text: 'Maximum CLIENTELE + 2', 
            material: 'Rubble',
            value: 1,
            role: 'Laborer'
        }, 
        Latrine: {
            text: 'Before performing THINKER action may discard one card to POOL', 
            material: 'Rubble',
            value: 1,
            role: 'Laborer'
        }, 
        'Ludus Magna': {
            text: 'Each MERCHANT client counts as any role', 
            material: 'Marble',
            value: 3,
            role: 'Patron'
        }, 
        Market: {
            text: 'Maximum VAULT + 2', 
            material: 'Wood',
            value: 1,
            role: 'Craftsman'
        }, 
        Palace: {
            text: 'May play multiple cards of same role in order to perform additional actions', 
            material: 'Marble',
            value: 3,
            role: 'Patron'
        }, 
        Palisade: {
            text: 'Immune to LEGIONARY', 
            material: 'Wood',
            value: 1,
            role: 'Craftsman'
        }, 
        Prison: {
            text: "May exchange INFLUENCE for opponent's completed structure", 
            material: 'Stone',
            value: 3,
            role: 'Merchant'
        }, 
        Road: {
            text: 'When adding to STONE structure may use any material', 
            material: 'Rubble',
            value: 1,
            role: 'Laborer'
        }, 
        School: {
            text: 'May perform one THINKER action for each INFLUENCE', 
            material: 'Brick',
            value: 2,
            role: 'Legionary'
        }, 
        Scriptorium: {
            text: 'May use one MARBLE material to complete any structure', 
            material: 'Stone',
            value: 3,
            role: 'Merchant'
        }, 
        Senate: {
            text: "May take opponent's JACK into HAND at end of turn in which it is played", 
            material: 'Concrete',
            value: 2,
            role: 'Architect'
        }, 
        Sewer: {
            text: 'May place Orders cards used to lead or follow into STOCKPILE at end of turn', 
            material: 'Stone',
            value: 3,
            role: 'Merchant'
        }, 
        Shrine: {
            text: 'Maximum HAND + 2', 
            material: 'Brick',
            value: 2,
            role: 'Legionary'
        }, 
        Stairway: {
            text: "When performing ARCHITECT action may add material to opponent's completed STRUCTURE to make function available to all players", 
            material: 'Marble',
            value: 3,
            role: 'Patron'
        }, 
        Statue: {
            text: '+ 3 VP. May place Statue on any SITE', 
            material: 'Marble',
            value: 3,
            role: 'Patron'
        }, 
        Storeroom: {
            text: 'All clients count as LABORERS', 
            material: 'Concrete',
            value: 2,
            role: 'Architect'
        }, 
        Temple: {
            text: 'Maximum HAND + 4', 
            material: 'Marble',
            value: 3,
            role: 'Patron'
        }, 
        Tower: {
            text: 'May use RUBBLE in any STRUCTURE.  May lay foundation onto any out of town SITE at no extra cost', 
            material: 'Concrete',
            value: 2,
            role: 'Architect'
        }, 
        Villa: {
            text: 'When performing ARCHITECT action may complete Villa with one material', 
            material: 'Stone',
            value: 3,
            role: 'Merchant'
        }, 
        Vomitorium: {
            text: 'Before performing THINKER action may discard all cards to POOL', 
            material: 'Concrete',
            value: 2,
            role: 'Architect'
        }, 
        Wall: {
            text: 'Immune to LEGIONARY.  + 1 VP for every two materials in STOCKPILE', 
            material: 'Concrete',
            value: 2,
            role: 'Architect'
        }
    };

    util._cardList = [
        'Jack', 'Jack', 'Jack', 'Jack', 'Jack', 'Jack',
        'Academy', 'Academy', 'Academy',
        'Amphitheatre', 'Amphitheatre', 'Amphitheatre',
        'Aqueduct', 'Aqueduct', 'Aqueduct',
        'Archway', 'Archway', 'Archway',
        'Atrium', 'Atrium', 'Atrium',
        'Bar', 'Bar', 'Bar', 'Bar', 'Bar', 'Bar',
        'Basilica', 'Basilica', 'Basilica',
        'Bath', 'Bath', 'Bath',
        'Bridge', 'Bridge', 'Bridge',
        'Catacomb', 'Catacomb', 'Catacomb',
        'Circus', 'Circus', 'Circus', 'Circus', 'Circus', 'Circus',
        'Circus Maximus', 'Circus Maximus', 'Circus Maximus',
        'Coliseum', 'Coliseum', 'Coliseum',
        'Dock', 'Dock', 'Dock', 'Dock', 'Dock', 'Dock',
        'Forum', 'Forum', 'Forum',
        'Foundry', 'Foundry', 'Foundry',
        'Fountain', 'Fountain', 'Fountain',
        'Garden', 'Garden', 'Garden',
        'Gate', 'Gate', 'Gate',
        'Insula', 'Insula', 'Insula', 'Insula', 'Insula', 'Insula',
        'Latrine', 'Latrine', 'Latrine', 'Latrine', 'Latrine', 'Latrine',
        'Ludus Magna', 'Ludus Magna', 'Ludus Magna',
        'Market', 'Market', 'Market', 'Market', 'Market', 'Market',
        'Palace', 'Palace', 'Palace',
        'Palisade', 'Palisade', 'Palisade', 'Palisade', 'Palisade', 'Palisade',
        'Prison', 'Prison', 'Prison',
        'Road', 'Road', 'Road', 'Road', 'Road', 'Road',
        'School', 'School', 'School',
        'Scriptorium', 'Scriptorium', 'Scriptorium',
        'Senate', 'Senate', 'Senate',
        'Sewer', 'Sewer', 'Sewer',
        'Shrine', 'Shrine', 'Shrine',
        'Stairway', 'Stairway', 'Stairway',
        'Statue', 'Statue', 'Statue',
        'Storeroom', 'Storeroom', 'Storeroom',
        'Temple', 'Temple', 'Temple',
        'Tower', 'Tower', 'Tower',
        'Villa', 'Villa', 'Villa',
        'Vomitorium', 'Vomitorium', 'Vomitorium',
        'Wall', 'Wall', 'Wall'
    ];

    return util;
});
