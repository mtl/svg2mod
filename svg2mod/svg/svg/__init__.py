#__all__ = ['geometry', 'svg']

from .svg import *

def parse(filename, verbose=True):
    f = svg.Svg(filename, verbose)
    return f

