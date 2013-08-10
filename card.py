#!/usr/bin/env python

"""
A class to encapsulate a card.
"""

class Card:
  def __init__(self, name=None, material=None, value=None, role=None):
    self.name = name or ''
    self.short_name = name[:4] if name else ''
    self.material = material
    self.value = value or 0
    self.role = role
    self.is_jack = False

  def __repr__(self):
    rep=('Card(name={name!r}, material={material!r}, '
         'value={value!r}, role={role!r})')
    return rep.format(name=self.name, material=self.material,
      value=self.value, role=self.role)

  def __str__(self):
    return self.name


if __name__ == '__main__':

    test = Card()
    print test
    print repr(test)


