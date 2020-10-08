#!/usr/bin/env python3

import argparse
import datetime
import os
from pprint import pformat, pprint
import re
import svg2mod.svg as svg
import sys


#----------------------------------------------------------------------------
DEFAULT_DPI = 96 # 96 as of Inkscape 0.92

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
        args.module_value,
        args.ignore_hidden_layers,
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

    # Create an exporter:
    if pretty:
        exported = Svg2ModExportPretty(
            imported,
            args.output_file_name,
            args.center,
            args.scale_factor,
            args.precision,
            args.dpi,
        )

    else:

        # If the module file exists, try to read it:
        exported = None
        if os.path.isfile( args.output_file_name ):

            try:
                exported = Svg2ModExportLegacyUpdater(
                    imported,
                    args.output_file_name,
                    args.center,
                    args.scale_factor,
                    args.precision,
                    args.dpi,
                )

            except Exception as e:
                raise e
                #print( e.message )
                #exported = None

        # Write the module file:
        if exported is None:
            exported = Svg2ModExportLegacy(
                imported,
                args.output_file_name,
                args.center,
                args.scale_factor,
                args.precision,
                use_mm = use_mm,
                dpi = args.dpi,
            )

    # Export the footprint:
    exported.write()


#----------------------------------------------------------------------------

class LineSegment( object ):

    #------------------------------------------------------------------------

    @staticmethod
    def _on_segment( p, q, r ):
        """ Given three colinear points p, q, and r, check if
            point q lies on line segment pr. """

        if (
            q.x <= max( p.x, r.x ) and
            q.x >= min( p.x, r.x ) and
            q.y <= max( p.y, r.y ) and
            q.y >= min( p.y, r.y )
        ):
            return True

        return False


    #------------------------------------------------------------------------

    @staticmethod
    def _orientation( p, q, r ):
        """ Find orientation of ordered triplet (p, q, r).
            Returns following values
            0 --> p, q and r are colinear
            1 --> Clockwise
            2 --> Counterclockwise
        """

        val = (
            ( q.y - p.y ) * ( r.x - q.x ) -
            ( q.x - p.x ) * ( r.y - q.y )
        )

        if val == 0: return 0
        if val > 0: return 1
        return 2


    #------------------------------------------------------------------------

    def __init__( self, p = None, q = None ):

        self.p = p
        self.q = q


    #------------------------------------------------------------------------

    def connects( self, segment ):

        if self.q.x == segment.p.x and self.q.y == segment.p.y: return True
        if self.q.x == segment.q.x and self.q.y == segment.q.y: return True
        if self.p.x == segment.p.x and self.p.y == segment.p.y: return True
        if self.p.x == segment.q.x and self.p.y == segment.q.y: return True
        return False


    #------------------------------------------------------------------------

    def intersects( self, segment ):
        """ Return true if line segments 'p1q1' and 'p2q2' intersect.
            Adapted from:
              http://www.geeksforgeeks.org/check-if-two-given-line-segments-intersect/
        """

        # Find the four orientations needed for general and special cases:
        o1 = self._orientation( self.p, self.q, segment.p )
        o2 = self._orientation( self.p, self.q, segment.q )
        o3 = self._orientation( segment.p, segment.q, self.p )
        o4 = self._orientation( segment.p, segment.q, self.q )

        return (

            # General case:
            ( o1 != o2 and o3 != o4 )

            or

            # p1, q1 and p2 are colinear and p2 lies on segment p1q1:
            ( o1 == 0 and self._on_segment( self.p, segment.p, self.q ) )

            or

            # p1, q1 and p2 are colinear and q2 lies on segment p1q1:
            ( o2 == 0 and self._on_segment( self.p, segment.q, self.q ) )

            or

            # p2, q2 and p1 are colinear and p1 lies on segment p2q2:
            ( o3 == 0 and self._on_segment( segment.p, self.p, segment.q ) )

            or

            # p2, q2 and q1 are colinear and q1 lies on segment p2q2:
            ( o4 == 0 and self._on_segment( segment.p, self.q, segment.q ) )
        )


    #------------------------------------------------------------------------

    def q_next( self, q ):

        self.p = self.q
        self.q = q


    #------------------------------------------------------------------------

#----------------------------------------------------------------------------

class PolygonSegment( object ):

    #------------------------------------------------------------------------

    def __init__( self, points ):

        self.points = points

        if len( points ) < 3:
            print(
                "Warning:"
                " Path segment has only {} points (not a polygon?)".format(
                    len( points )
                )
            )


    #------------------------------------------------------------------------

    # KiCad will not "pick up the pen" when moving between a polygon outline
    # and holes within it, so we search for a pair of points connecting the
    # outline (self) to the hole such that the connecting segment will not
    # cross the visible inner space within any hole.
    def _find_insertion_point( self, hole, holes ):

        #print( "      Finding insertion point.  {} holes".format( len( holes ) ) )

        # Try the next point on the container:
        for cp in range( len( self.points ) ):
            container_point = self.points[ cp ]

            #print( "      Trying container point {}".format( cp ) )

            # Try the next point on the hole:
            for hp in range( len( hole.points ) - 1 ):
                hole_point = hole.points[ hp ]

                #print( "      Trying hole point {}".format( cp ) )

                bridge = LineSegment( container_point, hole_point )

                # Check for intersection with each other hole:
                for other_hole in holes:

                    #print( "      Trying other hole.  Check = {}".format( hole == other_hole ) )

                    # If the other hole intersects, don't bother checking
                    # remaining holes:
                    if other_hole.intersects(
                        bridge,
                        check_connects = (
                            other_hole == hole or other_hole == self
                        )
                    ): break

                    #print( "        Hole does not intersect." )

                else:
                    print( "      Found insertion point: {}, {}".format( cp, hp ) )

                    # No other holes intersected, so this insertion point
                    # is acceptable:
                    return ( cp, hole.points_starting_on_index( hp ) )

        print(
            "Could not insert segment without overlapping other segments"
        )


    #------------------------------------------------------------------------

    # Return the list of ordered points starting on the given index, ensuring
    # that the first and last points are the same.
    def points_starting_on_index( self, index ):

        points = self.points

        if index > 0:

            # Strip off end point, which is a duplicate of the start point:
            points = points[ : -1 ]

            points = points[ index : ] + points[ : index ]

            points.append(
                svg.Point( points[ 0 ].x, points[ 0 ].y )
            )

        return points


    #------------------------------------------------------------------------

    # Return a list of points with the given polygon segments (paths) inlined.
    def inline( self, segments ):

        if len( segments ) < 1:
            return self.points

        print( "    Inlining {} segments...".format( len( segments ) ) )

        all_segments = segments[ : ] + [ self ]
        insertions = []

        # Find the insertion point for each hole:
        for hole in segments:

            insertion = self._find_insertion_point(
                hole, all_segments
            )
            if insertion is not None:
                insertions.append( insertion )

        insertions.sort( key = lambda i: i[ 0 ] )

        inlined = [ self.points[ 0 ] ]
        ip = 1
        points = self.points

        for insertion in insertions:

            while ip <= insertion[ 0 ]:
                inlined.append( points[ ip ] )
                ip += 1

            if (
                inlined[ -1 ].x == insertion[ 1 ][ 0 ].x and
                inlined[ -1 ].y == insertion[ 1 ][ 0 ].y
            ):
                inlined += insertion[ 1 ][ 1 : -1 ]
            else:
                inlined += insertion[ 1 ]

            inlined.append( svg.Point(
                points[ ip - 1 ].x,
                points[ ip - 1 ].y,
            ) )

        while ip < len( points ):
            inlined.append( points[ ip ] )
            ip += 1

        return inlined


    #------------------------------------------------------------------------

    def intersects( self, line_segment, check_connects ):

        hole_segment = LineSegment()

        # Check each segment of other hole for intersection:
        for point in self.points:

            hole_segment.q_next( point )

            if hole_segment.p is not None:

                if (
                    check_connects and
                    line_segment.connects( hole_segment )
                ): continue

                if line_segment.intersects( hole_segment ):

                    #print( "Intersection detected." )

                    return True

        return False


    #------------------------------------------------------------------------

    # Apply all transformations and rounding, then remove duplicate
    # consecutive points along the path.
    def process( self, transformer, flip, fill ):

        points = []
        for point in self.points:

            point = transformer.transform_point( point, flip )

            if (
                len( points ) < 1 or
                point.x != points[ -1 ].x or
                point.y != points[ -1 ].y
            ):
                points.append( point )

        if (
            points[ 0 ].x != points[ -1 ].x or
            points[ 0 ].y != points[ -1 ].y
        ):
            #print( "Warning: Closing polygon. start=({}, {}) end=({}, {})".format(
                #points[ 0 ].x, points[ 0 ].y,
                #points[ -1 ].x, points[ -1 ].y,
            #) )

            if fill:
                points.append( svg.Point(
                    points[ 0 ].x,
                    points[ 0 ].y,
                ) )

        #else:
            #print( "Polygon closed: start=({}, {}) end=({}, {})".format(
                #points[ 0 ].x, points[ 0 ].y,
                #points[ -1 ].x, points[ -1 ].y,
            #) )

        self.points = points


    #------------------------------------------------------------------------

#----------------------------------------------------------------------------

class Svg2ModImport( object ):

    #------------------------------------------------------------------------

    def _prune_hidden( self, items = None ):

        if items is None:

            items = self.svg.items
            self.svg.items = []

        for item in items:

            if not isinstance( item, svg.Group ):
                continue

            if( item.hidden ):
                print("Ignoring hidden SVG layer: {}".format( item.name ) )
            else:
                self.svg.items.append( item )

            if(item.items):
                self._prune_hidden( item.items )

    def __init__( self, file_name, module_name, module_value, ignore_hidden_layers ):

        self.file_name = file_name
        self.module_name = module_name
        self.module_value = module_value

        print( "Parsing SVG..." )
        self.svg = svg.parse( file_name )
        if( ignore_hidden_layers ):
            self._prune_hidden()


    #------------------------------------------------------------------------

#----------------------------------------------------------------------------

class Svg2ModExport( object ):

    #------------------------------------------------------------------------

    @staticmethod
    def _convert_decimil_to_mm( decimil ):
        return float( decimil ) * 0.00254


    #------------------------------------------------------------------------

    @staticmethod
    def _convert_mm_to_decimil( mm ):
        return int( round( mm * 393.700787 ) )


    #------------------------------------------------------------------------

    def _get_fill_stroke( self, item ):

        fill = True
        stroke = True
        stroke_width = 0.0

        if item.style is not None and item.style != "":

            for property in filter(None, item.style.split( ";" )):

                nv = property.split( ":" );
                name = nv[ 0 ].strip()
                value = nv[ 1 ].strip()

                if name == "fill" and value == "none":
                    fill = False

                elif name == "stroke" and value == "none":
                    stroke = False

                elif name == "stroke-width":
                    if value.endswith("px"):
                        value = value.replace( "px", "" )
                        stroke_width = float( value ) * 25.4 / float(self.dpi)
                    else:
                        stroke_width = float( value )

        if not stroke:
            stroke_width = 0.0
        elif stroke_width is None:
            # Give a default stroke width?
            stroke_width = self._convert_decimil_to_mm( 1 )

        return fill, stroke, stroke_width


    #------------------------------------------------------------------------

    def __init__(
        self,
        svg2mod_import,
        file_name,
        center,
        scale_factor = 1.0,
        precision = 20.0,
        use_mm = True,
        dpi = DEFAULT_DPI,
    ):
        if use_mm:
            # 25.4 mm/in;
            scale_factor *= 25.4 / float(dpi)
            use_mm = True
        else:
            # PCBNew uses "decimil" (10K DPI);
            scale_factor *= 10000.0 / float(dpi)

        self.imported = svg2mod_import
        self.file_name = file_name
        self.center = center
        self.scale_factor = scale_factor
        self.precision = precision
        self.use_mm = use_mm
        self.dpi = dpi

    #------------------------------------------------------------------------

    def _calculate_translation( self ):

        min_point, max_point = self.imported.svg.bbox()

        if(self.center):
            # Center the drawing:
            adjust_x = min_point.x + ( max_point.x - min_point.x ) / 2.0
            adjust_y = min_point.y + ( max_point.y - min_point.y ) / 2.0

            self.translation = svg.Point(
                0.0 - adjust_x,
                0.0 - adjust_y,
            )

        else:
            self.translation = svg.Point(
                0.0,
                0.0,
            )

    #------------------------------------------------------------------------

    # Find and keep only the layers of interest.
    def _prune( self, items = None ):

        if items is None:

            self.layers = {}
            for name in self.layer_map.keys():
                self.layers[ name ] = None

            items = self.imported.svg.items
            self.imported.svg.items = []

        for item in items:

            if not isinstance( item, svg.Group ):
                continue

            for name in self.layers.keys():
                #if re.search( name, item.name, re.I ):
                if name == item.name:
                    print( "Found SVG layer: {}".format( item.name ) )

                    self.imported.svg.items.append( item )
                    self.layers[ name ] = item
                    break
            else:
                self._prune( item.items )


    #------------------------------------------------------------------------

    def _write_items( self, items, layer, flip = False ):

        for item in items:

            if isinstance( item, svg.Group ):
                self._write_items( item.items, layer, flip )
                continue

            elif isinstance( item, svg.Path ):

                segments = [
                    PolygonSegment( segment )
                    for segment in item.segments(
                        precision = self.precision
                    )
                ]

                fill, stroke, stroke_width = self._get_fill_stroke( item )

                for segment in segments:
                    segment.process( self, flip, fill )

                if len( segments ) > 1:
                    points = segments[ 0 ].inline( segments[ 1 : ] )

                elif len( segments ) > 0:
                    points = segments[ 0 ].points

                if not self.use_mm:
                    stroke_width = self._convert_mm_to_decimil(
                        stroke_width
                    )

                print( "    Writing polygon with {} points".format(
                    len( points ) )
                )

                self._write_polygon(
                    points, layer, fill, stroke, stroke_width
                )

            else:
                print( "Unsupported SVG element: {}".format(
                    item.__class__.__name__
                ) )


    #------------------------------------------------------------------------

    def _write_module( self, front ):

        module_name = self._get_module_name( front )

        min_point, max_point = self.imported.svg.bbox()
        min_point = self.transform_point( min_point, flip = False )
        max_point = self.transform_point( max_point, flip = False )

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

        self._write_module_header(
            label_size, label_pen,
            reference_y, value_y,
            front,
        )

        for name, group in self.layers.items():

            if group is None: continue

            layer = self._get_layer_name( name, front )

            #print( "  Writing layer: {}".format( name ) )
            self._write_items( group.items, layer, not front )

        self._write_module_footer( front )


    #------------------------------------------------------------------------

    def _write_polygon_filled( self, points, layer, stroke_width = 0.0 ):

        self._write_polygon_header( points, layer )

        for point in points:
            self._write_polygon_point( point )

        self._write_polygon_footer( layer, stroke_width )


    #------------------------------------------------------------------------

    def _write_polygon_outline( self, points, layer, stroke_width ):

        prior_point = None
        for point in points:

            if prior_point is not None:

                self._write_polygon_segment(
                    prior_point, point, layer, stroke_width
                )

            prior_point = point


    #------------------------------------------------------------------------

    def transform_point( self, point, flip = False ):

        transformed_point = svg.Point(
            ( point.x + self.translation.x ) * self.scale_factor,
            ( point.y + self.translation.y ) * self.scale_factor,
        )

        if flip:
            transformed_point.x *= -1

        if self.use_mm:
            transformed_point.x = round( transformed_point.x, 12 )
            transformed_point.y = round( transformed_point.y, 12 )
        else:
            transformed_point.x = int( round( transformed_point.x ) )
            transformed_point.y = int( round( transformed_point.y ) )

        return transformed_point


    #------------------------------------------------------------------------

    def write( self ):

        self._prune()

        # Must come after pruning:
        translation = self._calculate_translation()

        print( "Writing module file: {}".format( self.file_name ) )
        self.output_file = open( self.file_name, 'w' )

        self._write_library_intro()

        self._write_modules()

        self.output_file.close()
        self.output_file = None


    #------------------------------------------------------------------------

#----------------------------------------------------------------------------

class Svg2ModExportLegacy( Svg2ModExport ):

    layer_map = {
        #'inkscape-name' : [ kicad-front, kicad-back ],
        'F.Cu' : [ 15, 15 ],
        'B.Cu' : [ 0, 0 ],
        'F.Adhes' : [ 17, 17 ],
        'B.Adhes' : [ 16, 16 ],
        'F.Paste' : [ 19, 19 ],
        'B.Paste' : [ 18, 18 ],
        'F.SilkS' : [ 21, 21 ],
        'B.SilkS' : [ 20, 20 ],
        'F.Mask' : [ 23, 23 ],
        'B.Mask' : [ 22, 22 ],
        'Dwgs.User' : [ 24, 24 ],
        'Cmts.User' : [ 25, 25 ],
        'Eco1.User' : [ 26, 26 ],
        'Eco2.User' : [ 27, 27 ],
        'Edge.Cuts' : [ 28, 28 ],
    }


    #------------------------------------------------------------------------

    def __init__(
        self,
        svg2mod_import,
        file_name,
        center,
        scale_factor = 1.0,
        precision = 20.0,
        use_mm = True,
        dpi = DEFAULT_DPI,
    ):
        super( Svg2ModExportLegacy, self ).__init__(
            svg2mod_import,
            file_name,
            center,
            scale_factor,
            precision,
            use_mm,
            dpi,
        )

        self.include_reverse = True


    #------------------------------------------------------------------------

    def _get_layer_name( self, name, front ):

        layer_info = self.layer_map[ name ]
        layer = layer_info[ 0 ]
        if not front and layer_info[ 1 ] is not None:
            layer = layer_info[ 1 ]

        return layer


    #------------------------------------------------------------------------

    def _get_module_name( self, front = None ):

        if self.include_reverse and not front:
            return self.imported.module_name + "-rev"

        return self.imported.module_name


    #------------------------------------------------------------------------

    def _write_library_intro( self ):

        modules_list = self._get_module_name( front = True )
        if self.include_reverse:
            modules_list += (
                "\n" +
                self._get_module_name( front = False )
            )

        units = ""
        if self.use_mm:
            units = "\nUnits mm"

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

    def _write_module_header(
        self,
        label_size,
        label_pen,
        reference_y,
        value_y,
        front,
    ):

        self.output_file.write( """$MODULE {0}
Po 0 0 0 {6} 00000000 00000000 ~~
Li {0}
T0 0 {1} {2} {2} 0 {3} N I 21 "{0}"
T1 0 {5} {2} {2} 0 {3} N I 21 "{4}"
""".format(
    self._get_module_name( front ),
    reference_y,
    label_size,
    label_pen,
    self.imported.module_value,
    value_y,
    15, # Seems necessary
)
        )


    #------------------------------------------------------------------------

    def _write_module_footer( self, front ):

        self.output_file.write(
            "$EndMODULE {0}\n".format( self._get_module_name( front ) )
        )


    #------------------------------------------------------------------------

    def _write_modules( self ):

        self._write_module( front = True )

        if self.include_reverse:
            self._write_module( front = False )

        self.output_file.write( "$EndLIBRARY" )


    #------------------------------------------------------------------------

    def _write_polygon( self, points, layer, fill, stroke, stroke_width ):

        if fill:
            self._write_polygon_filled(
                points, layer
            )

        if stroke:

            self._write_polygon_outline(
                points, layer, stroke_width
            )


    #------------------------------------------------------------------------

    def _write_polygon_footer( self, layer, stroke_width ):

        pass


    #------------------------------------------------------------------------

    def _write_polygon_header( self, points, layer ):

        pen = 1
        if self.use_mm:
            pen = self._convert_decimil_to_mm( pen )

        self.output_file.write( "DP 0 0 0 0 {} {} {}\n".format(
            len( points ),
            pen,
            layer
        ) )


    #------------------------------------------------------------------------

    def _write_polygon_point( self, point ):

            self.output_file.write(
                "Dl {} {}\n".format( point.x, point.y )
            )


    #------------------------------------------------------------------------

    def _write_polygon_segment( self, p, q, layer, stroke_width ):

        self.output_file.write( "DS {} {} {} {} {} {}\n".format(
            p.x, p.y,
            q.x, q.y,
            stroke_width,
            layer
        ) )


    #------------------------------------------------------------------------

#----------------------------------------------------------------------------

class Svg2ModExportLegacyUpdater( Svg2ModExportLegacy ):

    #------------------------------------------------------------------------

    def __init__(
        self,
        svg2mod_import,
        file_name,
        center,
        scale_factor = 1.0,
        precision = 20.0,
        dpi = DEFAULT_DPI,
        include_reverse = True,
    ):
        self.file_name = file_name
        use_mm = self._parse_output_file()

        super( Svg2ModExportLegacyUpdater, self ).__init__(
            svg2mod_import,
            file_name,
            center,
            scale_factor,
            precision,
            use_mm,
            dpi,
        )


    #------------------------------------------------------------------------

    def _parse_output_file( self ):

        print( "Parsing module file: {}".format( self.file_name ) )
        module_file = open( self.file_name, 'r' )
        lines = module_file.readlines()
        module_file.close()

        self.loaded_modules = {}
        self.post_index = []
        self.pre_index = []
        use_mm = False

        index = 0

        # Find the start of the index:
        while index < len( lines ):

            line = lines[ index ]
            index += 1
            self.pre_index.append( line )
            if line[ : 6 ] == "$INDEX":
                break

            m = re.match( "Units[\s]+mm[\s]*", line )
            if m is not None:
                print( "  Use mm detected" )
                use_mm = True

        # Read the index:
        while index < len( lines ):

            line = lines[ index ]
            if line[ : 9 ] == "$EndINDEX":
                break
            index += 1
            self.loaded_modules[ line.strip() ] = []

        # Read up until the first module:
        while index < len( lines ):

            line = lines[ index ]
            if line[ : 7 ] == "$MODULE":
                break
            index += 1
            self.post_index.append( line )

        # Read modules:
        while index < len( lines ):

            line = lines[ index ]
            if line[ : 7 ] == "$MODULE":
                module_name, module_lines, index = self._read_module( lines, index )
                if module_name is not None:
                    self.loaded_modules[ module_name ] = module_lines

            elif line[ : 11 ] == "$EndLIBRARY":
                break

            else:
                raise Exception(
                    "Expected $EndLIBRARY: [{}]".format( line )
                )

        #print( "Pre-index:" )
        #pprint( self.pre_index )

        #print( "Post-index:" )
        #pprint( self.post_index )

        #print( "Loaded modules:" )
        #pprint( self.loaded_modules )

        return use_mm


    #------------------------------------------------------------------------

    def _read_module( self, lines, index ):

        # Read module name:
        m = re.match( r'\$MODULE[\s]+([^\s]+)[\s]*', lines[ index ] )
        module_name = m.group( 1 )

        print( "  Reading module {}".format( module_name ) )

        index += 1
        module_lines = []
        while index < len( lines ):

            line = lines[ index ]
            index += 1

            m = re.match(
                r'\$EndMODULE[\s]+' + module_name + r'[\s]*', line
            )
            if m is not None:
                return module_name, module_lines, index

            module_lines.append( line )

        raise Exception(
            "Could not find end of module '{}'".format( module_name )
        )


    #------------------------------------------------------------------------

    def _write_library_intro( self ):

        # Write pre-index:
        self.output_file.writelines( self.pre_index )

        self.loaded_modules[ self._get_module_name( front = True ) ] = None
        if self.include_reverse:
            self.loaded_modules[
                self._get_module_name( front = False )
            ] = None

        # Write index:
        for module_name in sorted(
            self.loaded_modules.keys(),
            key = str.lower
        ):
            self.output_file.write( module_name + "\n" )

        # Write post-index:
        self.output_file.writelines( self.post_index )


    #------------------------------------------------------------------------

    def _write_preserved_modules( self, up_to = None ):

        if up_to is not None:
            up_to = up_to.lower()

        for module_name in sorted(
            self.loaded_modules.keys(),
            key = str.lower
        ):
            if up_to is not None and module_name.lower() >= up_to:
                continue

            module_lines = self.loaded_modules[ module_name ]

            if module_lines is not None:

                self.output_file.write(
                    "$MODULE {}\n".format( module_name )
                )
                self.output_file.writelines( module_lines )
                self.output_file.write(
                    "$EndMODULE {}\n".format( module_name )
                )

                self.loaded_modules[ module_name ] = None


    #------------------------------------------------------------------------

    def _write_module_footer( self, front ):

        super( Svg2ModExportLegacyUpdater, self )._write_module_footer(
            front,
        )

        # Write remaining modules:
        if not front:
            self._write_preserved_modules()


    #------------------------------------------------------------------------

    def _write_module_header(
        self,
        label_size,
        label_pen,
        reference_y,
        value_y,
        front,
    ):
        self._write_preserved_modules(
            up_to = self._get_module_name( front )
        )

        super( Svg2ModExportLegacyUpdater, self )._write_module_header(
            label_size,
            label_pen,
            reference_y,
            value_y,
            front,
        )


    #------------------------------------------------------------------------

#----------------------------------------------------------------------------

class Svg2ModExportPretty( Svg2ModExport ):

    layer_map = {
        #'inkscape-name' : kicad-name,
        'F.Cu' :    "F.Cu",
        'B.Cu' :    "B.Cu",
        'F.Adhes' : "F.Adhes",
        'B.Adhes' : "B.Adhes",
        'F.Paste' : "F.Paste",
        'B.Paste' : "B.Paste",
        'F.SilkS' : "F.SilkS",
        'B.SilkS' : "B.SilkS",
        'F.Mask' :  "F.Mask",
        'B.Mask' :  "B.Mask",
        'Dwgs.User' : "Dwgs.User",
        'Cmts.User' : "Cmts.User",
        'Eco1.User' : "Eco1.User",
        'Eco2.User' : "Eco2.User",
        'Edge.Cuts' : "Edge.Cuts",
        'F.CrtYd' : "F.CrtYd",
        'B.CrtYd' : "B.CrtYd",
        'F.Fab' :   "F.Fab",
        'B.Fab' :   "B.Fab"
    }


    #------------------------------------------------------------------------

    def _get_layer_name( self, name, front ):

        return self.layer_map[ name ]


    #------------------------------------------------------------------------

    def _get_module_name( self, front = None ):

        return self.imported.module_name


    #------------------------------------------------------------------------

    def _write_library_intro( self ):

        self.output_file.write( """(module {0} (layer F.Cu) (tedit {1:8X})
  (attr virtual)
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


    #------------------------------------------------------------------------

    def _write_module_footer( self, front ):

        self.output_file.write( "\n)" )


    #------------------------------------------------------------------------

    def _write_module_header(
        self,
        label_size,
        label_pen,
        reference_y,
        value_y,
        front,
    ):
        if front:
            side = "F"
        else:
            side = "B"

        self.output_file.write(
"""  (fp_text reference {0} (at 0 {1}) (layer {2}.SilkS) hide
    (effects (font (size {3} {3}) (thickness {4})))
  )
  (fp_text value {5} (at 0 {6}) (layer {2}.SilkS) hide
    (effects (font (size {3} {3}) (thickness {4})))
  )""".format(

    self._get_module_name(), #0
    reference_y, #1
    side, #2
    label_size, #3
    label_pen, #4
    self.imported.module_value, #5
    value_y, #6
)
        )


    #------------------------------------------------------------------------

    def _write_modules( self ):

        self._write_module( front = True )


    #------------------------------------------------------------------------

    def _write_polygon( self, points, layer, fill, stroke, stroke_width ):

        if fill:
            self._write_polygon_filled(
                points, layer, stroke_width
            )

        # Polygons with a fill and stroke are drawn with the filled polygon
        # above:
        if stroke and not fill:

            self._write_polygon_outline(
                points, layer, stroke_width
            )


    #------------------------------------------------------------------------

    def _write_polygon_footer( self, layer, stroke_width ):

        self.output_file.write(
            "    )\n    (layer {})\n    (width {})\n  )".format(
                layer, stroke_width
            )
        )


    #------------------------------------------------------------------------

    def _write_polygon_header( self, points, layer ):

            self.output_file.write( "\n  (fp_poly\n    (pts \n" )


    #------------------------------------------------------------------------

    def _write_polygon_point( self, point ):

            self.output_file.write(
                "      (xy {} {})\n".format( point.x, point.y )
            )


    #------------------------------------------------------------------------

    def _write_polygon_segment( self, p, q, layer, stroke_width ):

        self.output_file.write(
            """\n  (fp_line
    (start {} {})
    (end {} {})
    (layer {})
    (width {})
  )""".format(
    p.x, p.y,
    q.x, q.y,
    layer,
    stroke_width,
)
        )


    #------------------------------------------------------------------------

#----------------------------------------------------------------------------

def get_arguments():

    parser = argparse.ArgumentParser(
        description = (
            'Convert Inkscape SVG drawings to KiCad footprint modules.'
        )
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
        type = float,
        dest = 'precision',
        metavar = 'PRECISION',
        help = "smoothness for approximating curves with line segments (float)",
        default = 10.0,
    )

    parser.add_argument(
        '--format',
        type = str,
        dest = 'format',
        metavar = 'FORMAT',
        choices = [ 'legacy', 'pretty' ],
        help = "output module file format (legacy|pretty)",
        default = 'pretty',
    )

    parser.add_argument(
        '--units',
        type = str,
        dest = 'units',
        metavar = 'UNITS',
        choices = [ 'decimil', 'mm' ],
        help = "output units, if output format is legacy (decimil|mm)",
        default = 'mm',
    )

    parser.add_argument(
        '-d', '--dpi',
        type = int,
        dest = 'dpi',
        metavar = 'DPI',
        help = "DPI of the SVG file (int)",
        default = DEFAULT_DPI,
    )

    parser.add_argument(
        '--center',
        dest = 'center',
        action = 'store_const',
        const = True,
        help = "Center the module to the center of the bounding box",
        default = False,
    )

    parser.add_argument(
        '-x',
        dest = 'ignore_hidden_layers',
        action = 'store_const',
        const = True,
        help = "Do not export hidden layers",
        default = False,
    )

    return parser.parse_args(), parser


    #------------------------------------------------------------------------

#----------------------------------------------------------------------------
if __name__ == "__main__":
    main()


#----------------------------------------------------------------------------
