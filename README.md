# svg2mod
This is a small program to convert Inkscape SVG drawings to KiCad footprint module files.  It uses [cjlano's python SVG parser and drawing module](https://github.com/cjlano/svg) to interpret drawings and approximate curves using straight line segments.

## Usage
```
usage: svg2mod.py [-h] -i FILENAME [-o FILENAME] [--name NAME] [--value VALUE]
                  [-f FACTOR] [-p PRECISION] [--front-only] [--format FORMAT]
                  [--units UNITS]

svg2mod.

optional arguments:
  -h, --help            show this help message and exit
  -i FILENAME, --input-file FILENAME
                        name of the SVG file
  -o FILENAME, --output-file FILENAME
                        name of the module file
  --name NAME, --module-name NAME
                        base name of the module
  --value VALUE, --module-value VALUE
                        value of the module
  -f FACTOR, --factor FACTOR
                        scale paths by this factor
  -p PRECISION, --precision PRECISION
                        smoothness for approximating curves with line segments
                        (int)
  --front-only          omit output of back module
  --format FORMAT       output module file format (legacy|pretty)
  --units UNITS         Output units, if format is legacy (decimil|mm)
```
