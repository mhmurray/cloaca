from cloaca.zone import Zone
from cloaca.error import GTRError

class Building(object):
    """A container that represents buildings.
    
    The primary data members are the building foundation, site, and materials.

    Once the building is complete, the site is NOT removed. The materials
    remain as well. A complete building must retain a memory of its site
    so that we know the material composition in the future.

    Even when the building is complete, the site is left attached, so that
    the material composition can be tracked. A copy must be made to add
    to player's influence.

    Attributes:
        foundation -- (Card) foundation of the building.
        site -- (str) site the building is built on, eg. 'Wood'.
        materials -- (Zone) material cards added to the building.
        stairway_materials -- (Zone) material cardss added to the buildling
            with Stairway.
        complete -- (bool) True if the building is complete.
    """

    def __init__(self, foundation=None, site=None, materials=None,
                 stairway_materials=None, complete=False):
        """Initialize an instance with specified properties.

        The args are the same type as the attributes except that
        any iterable can be provided for the materials and stairway_materials.

        Creating a building with no site or no foundation raises a GTRError.
        """
        self.foundation = foundation
        self.site = site
        self.materials = Zone(materials if materials else [])
        self.stairway_materials = Zone(stairway_materials if stairway_materials else [])
        self.complete = complete

        self.materials.name = 'materials'
        self.stairway_materials.name = 'stairway_materials'

        if self.foundation is None:
            raise GTRError('Invalid building (no foundation): '+repr(self))

        if self.site is None:
            raise GTRError('Invalid building (no site): '+repr(self))

    def __str__(self):
        """Return the name of the foundation card."""
        return str(self.foundation.name)

    def __repr__(self):
        return ('Building({foundation!r}, {site!r}, {materials!r},'
               '{stairway_materials!r}, {complete!r})'
               .format(**self.__dict__))
    
    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    @property
    def is_stairwayed(self):
        """Return True if a material has been added by the Stairway."""
        return len(self.stairway_materials) > 0

    def composed_of(self, material):
        """Return True if the building is composed of the specified material.

        That is, this material is allowed to be added to complete it.
        For most buildings this is just the Site or Foundation
        material, but the Statue can be built on any site and counts as that
        site's material and Marble.
        """
        return material == self.site or material == self.foundation.material
