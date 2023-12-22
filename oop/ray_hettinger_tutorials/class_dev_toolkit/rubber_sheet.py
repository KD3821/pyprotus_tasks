from circle import Circle


cuts = [0.1, 0.7, 0.8]

circles = [Circle(r) for r in cuts]

for c in circles:
    print('A circle with a radius:', c.radius)
    print('has a perimeter:', c.perimeter())
    print('has a cold area:', c.area())
    c.radius *= 1.1
    print('has a warm area:', c.area())
    print('-----')
