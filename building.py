import card_manager
from gtrutils import GTRError
from zone import Zone

class Building:
    """ A container that represents buildings in GtR. The primary
    data members are the building foundation, site, and materials.

    Once the building is complete, the site is NOT removed. The materials
    remain as well. A complete building must retain a memory of its site
    so that we know the material composition in the future.
    """

    def __init__(self, foundation=None, site=None, materials=None,
                 stairway_materials=None, complete=False):
        """ The parameter materials is a list of cards that are used 
        as building materials.
        """
        self.foundation = foundation
        self.site = site
        self.materials = Zone(materials if materials else [])
        self.stairway_materials = Zone(stairway_materials if stairway_materials else [])
        self.complete = complete

    def __str__(self):
        """ The building name is the name of the foundation card.
        """
        return str(self.foundation.name)

    def __repr__(self):
        return ('Building({foundation!r}, {site!r}, {materials!r},'
               '{stairway_materials!r}, {complete!r})'
               .format(**self.__dict__))
    
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def is_stairwayed(self):
        """ True if a material has been added by the Stairway.
        """
        return len(self.stairway_materials) > 0

    def is_composed_of(self, material):
        """ Returns True if the building is composed of the specified material.
        That is, if you would be allowed to add that material to this building
        to complete it. For most buildings this is just the Site or Foundation
        material, but the Statue can be built on any site and counts as that
        site's material and Marble.
        """
        return material in self.get_material_composition()

    def get_material_composition(self):
        """Returns a tuple of materials that make up this building.
        This is determined by the site and foundation. If the site
        is missing (because the building is complete), its material
        doesn't count.
        
        The return value is of the form ('Marble','Stone')
        """
        return (site, foundation.material) if site else (foundation.material,)

    def pop_site(self):
        """Removes and returns this building's site.
        """
        card = site
        site = None
        return card

    def add_material(self, card):
        """ Adds the material to the building materials. Does not
        check legality.
        """
        self.materials.append(card)
