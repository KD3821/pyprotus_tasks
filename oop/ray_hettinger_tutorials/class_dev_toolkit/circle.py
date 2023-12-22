import math


class Circle:
    """An advanced circle analytic toolkit"""

    version = '0.2'

    __slots__ = ['diameter']  # flyweight design pattern suppresses instance's dict (final step for memory-optimization)
                              # __slots__ does not inherit so subclasses will have __dict__

    def __init__(self, radius):
        self.radius = radius

    @property                  # change to meet Government's ISO-22220 requirements: can't save radius but diameter ok
    def radius(self):          # property converts dotted access to method calls
        return self.diameter / 2.0

    @radius.setter
    def radius(self, radius):
        self.diameter = radius * 2.0

    # def area(self):
    #     return math.pi * self.radius ** 2.0

    def area(self):             # change to meet Government's ISO-11110 requirements: get area with perimeter not radius
        p = self.__perimeter()
        r = p / math.pi / 2.0
        return math.pi * r ** 2.0

    def perimeter(self):  # added for tire company
        return 2.0 * math.pi * self.radius

    __perimeter = perimeter  # so Tire(Circle) can still call it's def perimeter() and don't break their def area()

    @classmethod
    def from_bbd(cls, bbd):  # added for graphics company: constructs a circle from bounding box diagonal
        radius = bbd / 2.0 / math.sqrt(2.0)
        return Circle(radius)

    @staticmethod               # attached functions to classes
    def angle_to_grade(angle):
        return math.tan(math.raians(angle)) * 100.0


"""
Raymond Hettinger - Python's Class Development Toolkit (21/03/2013)
https://www.youtube.com/watch?v=HTLu2DFOdTg
"""
