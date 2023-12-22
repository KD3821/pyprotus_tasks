import math


class Circle:
    def __init__(self, radius):
        self.radius = radius

    def area(self):
        return self.radius * math.pi ** 2

    def __repr__(self):
        return f"{self.__class__.__name__} has area: {self.area()}"


class Donut(Circle):
    def __init__(self, outer, inner):
        super().__init__(outer)
        self.inner = inner

    def area(self):
        outer, inner = self.radius, self.inner
        return Circle(outer).area() - Circle(inner).area()


d = Donut(5, 2)
d_area = d.area()

c = Circle(5)
c_area = c.area()

print(d, c, sep=' | ')


"""
https://www.youtube.com/watch?v=miGolgp9xq8

Donut has area: 29.608813203268078 | Circle has area: 49.34802200544679

"""