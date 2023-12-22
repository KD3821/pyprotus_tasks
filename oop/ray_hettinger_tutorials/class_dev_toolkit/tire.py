from circle import Circle


class Tire(Circle):
    """Tires are circles with corrected perimeter"""

    def perimeter(self):
        """Circumference corrected for the rubber"""
        return Circle.perimeter(self) * 1.25


t = Tire(25)

print('A tire with a radius:', t.radius)
print('has an inner area:', t.area())
print('has an odometer corrected perimeter:', t.perimeter())
print('-----')
