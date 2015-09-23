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

## SVG Files

svg2mod expects images saved in the uncompressed Inkscape SVG (not "plain SVG") format.
 * Drawings should be to scale (1 mm in Inscape will be 1 mm in KiCad).
 * Paths are supported.
   * A path may have an outline and a fill.  (Colors will be ignored.)
   * A path may have a hole, defined by another path.  Sometimes this will render propery in KiCad, but sometimes not.
   * Paths with multiple holes may not work at all.
 * Groups may be used.
 * Layers must be used to indicate the mapping of drawing elements to KiCad layers.
   * Layers must be named according to the rules below.
 * Other types of elements such as rect, arc, and circle are not supported.
   * Use Inkscape's "Path->Object To Path" and "Path->Stroke To Path" menu options to convert these elements into paths that will work.

### Layers
Layers must be named (case-insensitive) according to the following rules:

| Inkscape layer name | KiCad layer(s)   | KiCad legacy | KiCad pretty |
|:-------------------:|:----------------:|:------------:|:------------:|
| Cu                  | F.Cu, B.Cu       | Yes          | Yes          |
| Adhes               | F.Adhes, B.Adhes | Yes          | Yes          |
| Paste               | F.Paste, B.Paste | Yes          | Yes          |
| SilkS               | F.SilkS, B.SilkS | Yes          | Yes          |
| Mask                | F.Mask, B.Mask   | Yes          | Yes          |
| Dwgs.User           | Dwgs.User        | Yes          | No           |
| Cmts.User           | Cmts.User        | Yes          | No           |
| Eco1.User           | Eco1.User        | Yes          | No           |
| Eco2.User           | Eco2.User        | Yes          | No           |
| Edge.Cuts           | Edge.Cuts        | Yes          | No           |
| Fab                 | Fab              | No           | Yes          |
| CrtYd               | CrtYd            | No           | Yes          |
