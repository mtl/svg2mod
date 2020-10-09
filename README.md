# svg2mod
[![Build Status](https://travis-ci.org/svg2mod/svg2mod.svg?branch=master)](https://travis-ci.org/svg2mod/svg2mod)

__[@mtl](https://github.com/mtl) is no longer active. [https://github.com/svg2mod/svg2mod](https://github.com/svg2mod/svg2mod) is now the maintained branch.__

This is a small program to convert Inkscape SVG drawings to KiCad footprint module files.  It uses [cjlano's python SVG parser and drawing module](https://github.com/cjlano/svg) to interpret drawings and approximate curves using straight line segments.  Module files can be output in KiCad's legacy or s-expression (i.e., pretty) formats.

## Requirements

Python 3

## Installation

```pip3 install git+https://github.com/svg2mod/svg2mod```

If building fails make sure setuptools is up to date. `pip3 install setuptools --upgrade`

## Example

```svg2mod -i input.svg -p 1.0```

## Usage
```
usage: svg2mod [-h] -i FILENAME [-o FILENAME] [--name NAME] [--value VALUE]
               [-f FACTOR] [-p PRECISION] [--format FORMAT] [--units UNITS]
               [-d DPI] [--center] [-x]

Convert Inkscape SVG drawings to KiCad footprint modules.

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
                        (float)
  --format FORMAT       output module file format (legacy|pretty)
  --units UNITS         output units, if output format is legacy (decimil|mm)
  -d DPI, --dpi DPI     DPI of the SVG file (int)
  --center              Center the module to the center of the bounding box
  -x                    Do not export hidden layers
```

## SVG Files

svg2mod expects images saved in the uncompressed Inkscape SVG (i.e., not "plain SVG") format.
 * Drawings should be to scale (1 mm in Inscape will be 1 mm in KiCad).  Use the --factor option to resize the resulting module(s) up or down from there.
 * Paths are supported.
   * A path may have an outline and a fill.  (Colors will be ignored.)
   * A path may have holes, defined by interior segments within the path (see included examples).  Sometimes this will render propery in KiCad, but sometimes not.
   * Paths with filled areas within holes may not work at all.
 * Groups may be used.  However, styles applied to groups (e.g., stroke-width) are not applied to contained drawing elements.  In these cases, it may be necessary to ungroup (and perhaps regroup) the elements.
 * Layers must be named according to the rules below.
 * Other types of elements such as rect, arc, and circle are not supported.
   * Use Inkscape's "Path->Object To Path" and "Path->Stroke To Path" menu options to convert these elements into paths that will work.

### Layers
Layers must be named (case-insensitive) according to the following rules:

| Inkscape layer name | KiCad layer(s)   | KiCad legacy | KiCad pretty |
|:-------------------:|:----------------:|:------------:|:------------:|
| F.Cu                | F.Cu             | Yes          | Yes          |
| B.Cu                | B.Cu             | Yes          | Yes          |
| F.Adhes             | F.Adhes          | Yes          | Yes          |
| B.Adhes             | B.Adhes          | Yes          | Yes          |
| F.Paste             | F.Paste          | Yes          | Yes          |
| B.Paste             | B.Paste          | Yes          | Yes          |
| F.SilkS             | F.SilkS          | Yes          | Yes          |
| B.SilkS             | B.SilkS          | Yes          | Yes          |
| F.Mask              | F.Mask           | Yes          | Yes          |
| B.Mask              | B.Mask           | Yes          | Yes          |
| Dwgs.User           | Dwgs.User        | Yes          | Yes          |
| Cmts.User           | Cmts.User        | Yes          | Yes          |
| Eco1.User           | Eco1.User        | Yes          | Yes          |
| Eco2.User           | Eco2.User        | Yes          | Yes          |
| Edge.Cuts           | Edge.Cuts        | Yes          | Yes          |
| F.Fab               | F.Fab            | --           | Yes          |
| B.Fab               | B.Fab            | --           | Yes          |
| F.CrtYd             | F.CrtYd          | --           | Yes          |
| B.CrtYd             | B.CrtYd          | --           | Yes          |

Note: If you have a layer "F.Cu", all of its sub-layers will be treated as "F.Cu" regardless of their names.
