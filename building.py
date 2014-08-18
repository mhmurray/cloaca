class Building:
    """ A container that represents buildings in GtR. The primary
    data members are the building foundation, site, and materials.

    Once the building is complete, the site is removed. The materials
    remain, however. A completed building has no memory of its site.
    """

    def __init__(self, foundation, site, materials):
        """ The parameter materials is a list of cards that are used 
        as building materials.
        """
        self.foundation = foundation
        self.site = site
        self.materials = materials
