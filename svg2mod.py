#!/usr/bin/python

from __future__ import absolute_import

import argparse
import datetime
import os
from pprint import pformat, pprint
import re
import svg
import sys


#----------------------------------------------------------------------------

def main():

    args, parser = get_arguments()

    pretty = args.format == 'pretty'
    use_mm = args.units == 'mm'

    if pretty:
        
        if not use_mm:
            print( "Error: decimil units only allowed with legacy output type" )
            sys.exit( -1 )

        #if args.include_reverse:
            #print(
                #"Warning: reverse footprint not supported or required for" +
                #" pretty output format"
            #)

    # Import the SVG:
    imported = Svg2ModImport(
        args.input_file_name,
        args.module_name,
        args.module_value
    )

    # Pick an output file name if none was provided:
    if args.output_file_name is None:

        args.output_file_name = os.path.splitext(
            os.path.basename( args.input_file_name )
        )[ 0 ]

    # Append the correct file name extension if needed:
    if pretty:
        extension = ".kicad_mod"
    else:
        extension = ".mod"
    if args.output_file_name[ - len( extension ) : ] != extension:
        args.output_file_name += extension

    # Export the footprint:
    exported = Svg2ModExport(
        imported,
        args.output_file_name,
        args.scale_factor,
        args.precision,
        pretty = pretty,
        use_mm = use_mm,
        include_reverse = not args.front_only,
    )
    exported.write()


#----------------------------------------------------------------------------

class Svg2ModImport( object ):

    #------------------------------------------------------------------------

    def __init__( self, file_name, module_name, module_value ):

        self.file_name = file_name
        self.module_name = module_name
        self.module_value = module_value

        print( "Parsing SVG..." )
        self.svg = svg.parse( file_name )


    #------------------------------------------------------------------------

#----------------------------------------------------------------------------

class Svg2ModExport( object ):

    layer_map = {
        #'name' : [ front, back, pretty-name ],
        'Cu' : [ 15, 0, "Cu" ],
        'Adhes' : [ 17, 16, "Adhes" ],
        'Paste' : [ 19, 18, "Paste" ],
        'SilkS' : [ 21, 20, "SilkS" ],
        'Mask' : [ 23, 22, "Mask" ],
        'Dwgs\\.User' : [ 24, 24, None ],
        'Cmts\\.User' : [ 25, 25, None ],
        'Eco1\\.User' : [ 26, 26, None ],
        'Eco2\\.User' : [ 27, 27, None ],
        'Edge\\.Cuts' : [ 28, 28, None ],
        'CrtYd' : [ None, None, "CrtYd" ],
        'Fab' : [ None, None, "Fab" ],
    }


    #------------------------------------------------------------------------

    @staticmethod
    def _convert_decimil_to_mm( decimil ):
        return float( decimil ) * 0.00254


    #------------------------------------------------------------------------

    @staticmethod
    def _convert_mm_to_decimil( mm ):
        return int( round( mm * 393.700787 ) )


    #------------------------------------------------------------------------

    @classmethod
    def _get_fill_stroke( cls, item ):

        fill = True
        stroke = True
        stroke_width = 0.0

        for property in item.style.split( ";" ):

            nv = property.split( ":" );
            name = nv[ 0 ].strip()
            value = nv[ 1 ].strip()

            if name == "fill" and value == "none":
                fill = False

            elif name == "stroke" and value == "none":
                stroke = False

            elif name == "stroke-width":
                stroke_width = float( value ) * 25.4 / 90.0

        if not stroke:
            stroke_width = 0.0
        elif stroke_width is None:
            # Give a default stroke width?
            stroke_width = cls._convert_decimil_to_mm( 1 )

        return fill, stroke, stroke_width


    #------------------------------------------------------------------------

    def __init__(
        self,
        svg2mod_import,
        file_name,
        scale_factor = 1.0,
        precision = 20,
        pretty = True,
        use_mm = True,
        include_reverse = True,
    ):
        if pretty or use_mm:
            # 25.4 mm/in; Inkscape uses 90 DPI:
            scale_factor *= 25.4 / 90.0
            use_mm = True
        else:
            # PCBNew uses "decimil" (10K DPI); Inkscape uses 90 DPI:
            scale_factor *= 10000.0 / 90.0

        self.imported = svg2mod_import
        self.file_name = file_name
        self.scale_factor = scale_factor
        self.precision = precision
        self.pretty = pretty
        self.use_mm = use_mm
        self.include_reverse = include_reverse


    #------------------------------------------------------------------------

    def _calculate_translation( self ):

        min_point, max_point = self.imported.svg.bbox()

        # Center the drawing:
        adjust_x = min_point.x + ( max_point.x - min_point.x ) / 2.0
        adjust_y = min_point.y + ( max_point.y - min_point.y ) / 2.0

        self.translation = svg.Point(
            0.0 - adjust_x,
            0.0 - adjust_y,
        )


    #------------------------------------------------------------------------

    # Apply all transformations and rounding, then remove duplicate
    # consecutive points along the path.
    def _collapse_points( self, points, flip ):

        new_points = []
        for point in points:

            point = self._transform_point( point, flip )

            if (
                len( new_points ) < 1 or
                point.x != new_points[ -1 ].x or
                point.y != new_points[ -1 ].y
            ):
                new_points.append( point )

        return new_points


    #------------------------------------------------------------------------

    def _get_module_name( self, front = None ):

        if not self.pretty and self.include_reverse:
            if front:
                return self.imported.module_name + "-Front"
            else:
                return self.imported.module_name + "-Back"

        return self.imported.module_name


    #------------------------------------------------------------------------

    # Find and keep only the layers of interest.
    def _prune( self, items = None ):

        if items is None:

            self.layers = {}
            for name, layer_info in self.layer_map.iteritems():
                if (
                    ( self.pretty and layer_info[ 2 ] is not None ) or
                    ( not self.pretty and layer_info[ 0 ] is not None )
                ):
                    self.layers[ name ] = None

            items = self.imported.svg.items
            self.imported.svg.items = []

        for item in items:

            if not isinstance( item, svg.Group ):
                continue

            for name in self.layers.iterkeys():
                if re.search( name, item.name, re.I ):
                    print( "Found layer: {}".format( item.name ) )
                    self.imported.svg.items.append( item )
                    self.layers[ name ] = item
                    break
            else:
                self._prune( item.items )


    #------------------------------------------------------------------------

    def _transform_point( self, point, flip ):

        transformed_point = svg.Point(
            ( point.x + self.translation.x ) * self.scale_factor,
            ( point.y + self.translation.y ) * self.scale_factor,
        )

        if flip:
            transformed_point.x *= -1

        if not self.use_mm:
            transformed_point.x = int( round( transformed_point.x ) )
            transformed_point.y = int( round( transformed_point.y ) )

        return transformed_point


    #------------------------------------------------------------------------

    def _write_items( self, items, flip, layer ):

        for item in items:

            if isinstance( item, svg.Group ):
                self._write_items( item.items, flip, layer )
                continue

            elif isinstance( item, svg.Path ):

                segments = item.segments( precision = self.precision )

                fill, stroke, stroke_width = self._get_fill_stroke( item )

                if not self.use_mm:
                    stroke_width = self._convert_mm_to_decimil(
                        stroke_width
                    )

                if fill:
                    self._write_polygon_filled(
                        segments, flip, layer,
                        stroke_width # For pretty format
                    )

                # In pretty format, polygons with a fill and stroke are
                # drawn with the filled polygon above:
                if stroke and not ( self.pretty and fill ):

                    self._write_polygon_outline(
                        segments, stroke_width, flip, layer
                    )

            else:
                print( "Unsupported SVG element: {}".format(
                    item.__class__.__name__
                ) )


    #------------------------------------------------------------------------

    def _write_module( self, front ):

        module_name = self._get_module_name( front )

        if front:
            side = "F"
        else:
            side = "B"

        min_point, max_point = self.imported.svg.bbox()
        min_point = self._transform_point( min_point, flip = False )
        max_point = self._transform_point( max_point, flip = False )

        label_offset = 1200
        label_size = 600
        label_pen = 120

        if self.use_mm:
            label_size = self._convert_decimil_to_mm( label_size )
            label_pen = self._convert_decimil_to_mm( label_pen )
            reference_y = min_point.y - self._convert_decimil_to_mm( label_offset )
            value_y = max_point.y + self._convert_decimil_to_mm( label_offset )
        else:
            reference_y = min_point.y - label_offset
            value_y = max_point.y + label_offset

        if self.pretty:

            self.output_file.write(
"""  (fp_text reference {0} (at 0 {1}) (layer {2}.SilkS) hide
    (effects (font (size {3} {3}) (thickness {4})))
  )
  (fp_text value {5} (at 0 {6}) (layer {2}.SilkS) hide
    (effects (font (size {3} {3}) (thickness {4})))
  )""".format(

    module_name, #0
    reference_y, #1
    side, #2
    label_size, #3
    label_pen, #4
    self.imported.module_value, #5
    value_y, #6
)
            )

        else:

            self.output_file.write( """$MODULE {0}
Po 0 0 0 {6} 00000000 00000000 ~~
Li {0}
T0 0 {1} {2} {2} 0 {3} N I 21 "{0}"
T1 0 {5} {2} {2} 0 {3} N I 21 "{4}"
""".format(
    module_name,
    reference_y,
    label_size,
    label_pen,
    self.imported.module_value,
    value_y,
    15, # Seems necessary
)
            )

        for name, group in self.layers.iteritems():

            if group is None: continue

            layer_info = self.layer_map[ name ]
            if self.pretty:
                layer = side + "." + layer_info[ 2 ]

            else:
                layer = layer_info[ 0 ]
                if not front and layer_info[ 1 ] is not None:
                    layer = layer_info[ 1 ]

            #print( "  Writing layer: {}".format( name ) )
            self._write_items( group.items, not front, layer )

        if self.pretty:
            self.output_file.write( "\n)" )
        else:
            self.output_file.write( "$EndMODULE {0}\n".format( module_name ) )


    #------------------------------------------------------------------------

    def _write_polygon_filled(
        self,
        segments,
        flip,
        layer,
        stroke_width = 0.0
    ):

        print( "    Writing filled polygon with {} segments".format( len( segments ) ) )

        if len( segments ) > 2:
            print(
                "Warning: " +
                "Not sure if Pcbnew supports more than 2 segments per path."
            )

        collapsed_segments = []

        total_points = 0
        for points in segments:

            points = self._collapse_points( points, flip )
            collapsed_segments.append( points )

            num_points = len( points )
            if num_points < 3:
                print(
                    "Warning: " +
                    "Segment has only {} points (not a polygon?)".format( num_points )
                )
            total_points += num_points

        if len( collapsed_segments ) > 1:
            total_points += 1

        if self.pretty:
            self.output_file.write( "\n  (fp_poly\n    (pts \n" )
            point_str = "      (xy {} {})\n"

        else:
            pen = 1
            if self.use_mm:
                pen = self._convert_decimil_to_mm( pen )

            self.output_file.write( "DP 0 0 0 0 {} {} {}\n".format(
                total_points,
                pen,
                layer
            ) )
            point_str = "Dl {} {}\n"

        for points in collapsed_segments:

            #print( "      Writing segment with {} points".format( len( points ) ) )

            if (
                points[ 0 ].x != points[ -1 ].x or
                points[ 0 ].y != points[ -1 ].y
            ):
                print( "Warning: Polygon is not closed. start={} end={}".format(
                    points[ 0 ], points[ -1 ]
                ) )

            for point in points:

                self.output_file.write( point_str.format( point.x, point.y ) )

        if len( collapsed_segments ) > 1:

            self.output_file.write( point_str.format(
                collapsed_segments[ 0 ][ 0 ].x,
                collapsed_segments[ 0 ][ 0 ].y,
            ) )

        if self.pretty:
            self.output_file.write(
                "    )\n    (layer {})\n    (width {})\n  )".format(
                    layer, stroke_width
                )
            )


    #------------------------------------------------------------------------

    def _write_polygon_outline( self, segments, stroke_width, flip, layer ):

        print( "    Writing polygon outline with {} segments".format( len( segments ) ) )

        for points in segments:

            points = self._collapse_points( points, flip )

            prior_point = None
            for point in points:

                if prior_point is not None:

                    if self.pretty:
                        self.output_file.write(
                            """\n  (fp_line
    (start {} {})
    (end {} {})
    (layer {})
    (width {})
  )""".format(
                                prior_point.x, prior_point.y,
                                point.x, point.y,
                                layer,
                                stroke_width,
                            )
                        )

                    else:
                        self.output_file.write( "DS {} {} {} {} {} {}\n".format(
                            prior_point.x,
                            prior_point.y,
                            point.x,
                            point.y,
                            stroke_width,
                            layer
                        ) )

                prior_point = point


    #------------------------------------------------------------------------

    def _write_library_intro( self ):

        if self.pretty:

            print( "Writing module file: {}".format( self.file_name ) )
            self.output_file = open( self.file_name, 'w' )

            self.output_file.write( """(module {0} (layer F.Cu) (tedit {1:8X})
  (attr smd)
  (descr "{2}")
  (tags {3})
""".format(
    self.imported.module_name, #0
    int( round( os.path.getctime( #1
        self.imported.file_name
    ) ) ),
    "Imported from {}".format( self.imported.file_name ), #2
    "svg2mod", #3
)
            )

        else: # legacy format:

            print( "Writing module file: {}".format( self.file_name ) )
            self.output_file = open( self.file_name, 'w' )

            modules_list = self._get_module_name( front = True )
            if self.include_reverse:
                modules_list += (
                    "\n" + 
                    self._get_module_name( front = False )
                )

            units = ""
            if self.use_mm: units = "\nUnits mm"

            self.output_file.write( """PCBNEW-LibModule-V1  {0}{1}
$INDEX
{2}
$EndINDEX
#
# {3}
#
""".format(
    datetime.datetime.now().strftime( "%a %d %b %Y %I:%M:%S %p %Z" ),
    units,
    modules_list,
    self.imported.file_name,
)
            )


    #------------------------------------------------------------------------

    def write( self ):

        self._prune()

        # Must come after pruning:
        translation = self._calculate_translation()

        self._write_library_intro()

        self._write_module( front = True )
        if not self.pretty and self.include_reverse:
            self._write_module( front = False )

        if not self.pretty:
            self.output_file.write( "$EndLIBRARY" )

        self.output_file.close()
        self.output_file = None


    #------------------------------------------------------------------------

#----------------------------------------------------------------------------

def get_arguments():

    parser = argparse.ArgumentParser(
        description = 'svg2mod.'
    )

    #------------------------------------------------------------------------

    parser.add_argument(
        '-i', '--input-file',
        type = str,
        dest = 'input_file_name',
        metavar = 'FILENAME',
        help = "name of the SVG file",
        required = True,
    )

    parser.add_argument(
        '-o', '--output-file',
        type = str,
        dest = 'output_file_name',
        metavar = 'FILENAME',
        help = "name of the module file",
    )

    parser.add_argument(
        '--name', '--module-name',
        type = str,
        dest = 'module_name',
        metavar = 'NAME',
        help = "base name of the module",
        default = "svg2mod",
    )

    parser.add_argument(
        '--value', '--module-value',
        type = str,
        dest = 'module_value',
        metavar = 'VALUE',
        help = "value of the module",
        default = "G***",
    )

    parser.add_argument(
        '-f', '--factor',
        type = float,
        dest = 'scale_factor',
        metavar = 'FACTOR',
        help = "scale paths by this factor",
        default = 1.0,
    )

    parser.add_argument(
        '-p', '--precision',
        type = int,
        dest = 'precision',
        metavar = 'PRECISION',
        help = "smoothness for approximating curves with line segments (int)",
        default = 10,
    )

    parser.add_argument(
        '--front-only',
        dest = 'front_only',
        action = 'store_const',
        const = True,
        help = "omit output of back module",
        default = False,
    )

    parser.add_argument(
        '--format',
        type = str,
        dest = 'format',
        metavar = 'FORMAT',
        choices = [ 'legacy', 'pretty' ],
        help = "output module file format (legacy|pretty)",
        default = 'legacy',
    )

    parser.add_argument(
        '--units',
        type = str,
        dest = 'units',
        metavar = 'UNITS',
        choices = [ 'decimil', 'mm' ],
        help = "Output units, if format is legacy (decimil|mm)",
        default = 'mm',
    )

    return parser.parse_args(), parser


    #------------------------------------------------------------------------

#----------------------------------------------------------------------------

main()


#----------------------------------------------------------------------------
# vi: set et sts=4 sw=4 ts=4:
