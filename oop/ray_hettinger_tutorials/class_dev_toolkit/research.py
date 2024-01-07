from random import random
import time

from circle import Circle


t1 = time.time()

n = 10_000_000

circles = [Circle(random()) for i in range(n)]

t2 = time.time()

avg = sum([c.area() for c in circles]) / n

t_avg = time.time() - t2

t_init = t2 - t1

print('The average area of', n, 'random cycles is', avg, '- avg took:', t_avg, '| init took:', t_init, sep=' ')


"""
for 10_000_000 circles tried to use __slots__:
regular class:
... avg took: 7.704173803329468 | init took: 13.984457015991211
with __slots__:
... avg took: 7.042635917663574 | init took: 9.010088920593262
"""
