#__all__ = ['geometry', 'svg']

from .svg import *

def parse(filename):
    return Svg(filename)
