import card_manager

class Building:
    """ A container that represents buildings in GtR. The primary
    data members are the building foundation, site, and materials.

    Once the building is complete, the site is removed. The materials
    remain, however. A completed building has no memory of its site.
    """

    def __init__(self, foundation=None, site=None, materials=None):
        """ The parameter materials is a list of cards that are used 
        as building materials.
        """
        self.foundation = foundation
        self.site = site
        self.materials = materials if materials else []
        self.stairway_materials = []

    def is_completed(self):
        """ True if the building is completed.
        """
        return self.site is None
    
    def is_stairwayed(self):
        """ True if a material has been added by the Stairway.
        """
        return len(self.stairway_material) > 0

    def get_material_composition(self):
        """ Returns a list of materials that make up this building.
        This is determined by the site and foundation. If the site
        is missing (because the building is complete), its material
        doesn't count.
        
        The return value is of the form ['Marble','Stone']
        """
        materials = []
        materials.append(card_manager.get_material_of_card(self.foundation))
        if site: materials.append(site)

        return materials

    def pop_site(self):
        """ Removes and returns this building's site.
        """
        card = site
        site = None
        return card

    def add_material(self, card):
        """ Adds the material to the building materials. Does not
        check legality.
        """
        materials.append(card)
