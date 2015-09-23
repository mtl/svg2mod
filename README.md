# svg2mod
This is a small program to convert Inkscape SVG drawings to KiCad footprint module files.  It uses [cjlano's python SVG parser and drawing module](https://github.com/cjlano/svg) to interpret drawings and approximate curves using straight line segments.

## Usage
```
usage: svg2mod.py [-h] [-i input-file-name] [-o output-file-name]
                  [-f scale-factor] [-p precision] [-n module-name]
                  [--value module-value] [--front-only] [--format format]
                  [--units units]

svg2mod.

optional arguments:
  -h, --help            show this help message and exit
  -i input-file-name, --input-file input-file-name
                        name of the SVG file
  -o output-file-name, --output-file output-file-name
                        name of the module file
  -f scale-factor, --factor scale-factor
                        scale paths by this factor
  -p precision, --precision precision
                        smoothness for approximating curves with line segments
                        (int)
  -n module-name, --name module-name, --module-name module-name
                        base name of the module
  --value module-value, --module-value module-value
                        value of the module
  --front-only          omit output of back module
  --format format       output module file format
  --units units         Output units (if format is legacy)
  ```
