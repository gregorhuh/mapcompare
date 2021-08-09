#!/usr/bin/env python3

"""Plot figure using GeoViews' Polygons class and utilizing either the Bokeh or matplotlib backend.

Creates a cProfile of the renderFigure() function encompassing the core plottinh task.
The cProfile is dumped as a .prof in mapcompare/profiles/[viz_type]/[db_name]/) only if basemap=False. 
This is to avoid tile loading affecting performance measurement of the core plotting task.
"""

# TODO Optimise performance, if possible.
# TODO Add legend for static viz_type

import os
import numpy as np
import geoviews as gv
from geoviews import opts
from bokeh.plotting import show
from mapcompare.sql2gdf import sql2gdf
from mapcompare.misc.pw import password
from mapcompare.cProfile_viz import to_cProfile
from cartopy import crs as ccrs

gv.extension('bokeh', 'matplotlib')
outputdir = "mapcompare/outputs/"

# INPUTS
viz_type = 'static/'
db_name = 'dd_subset'
basemap = True    
savefig = False

def prepGDFs(*gdfs):
    """Transforms gdfs to EPSG:4326 and renames the 'geom' column to 'geometry'. The latter is required pending a bug fix by GeoViews.

    Also calculates an appropriate zoom level if a tiled basemap is added while using the Matplotlib backend.

    These steps are separated from actual rendering to not affect performance measurement. 
    """
    def getBBox(*gdfs):
        """Return combined bbox of all GDFs in cartopy set_extent format (x0, x1, y0, y1).
        """

        list_of_bounds = [gdf.total_bounds for gdf in gdfs]
            
        xmin = np.min([item[0] for item in list_of_bounds])
        xmax = np.max([item[2] for item in list_of_bounds])
        ymin = np.min([item[1] for item in list_of_bounds])
        ymax = np.max([item[3] for item in list_of_bounds])
        
        extent = [xmin, xmax, ymin, ymax]
        
        return extent
    
    def get_zoom_mercator(minlon, maxlon, minlat, maxlat, width_to_height):
        """Return optimal zoom level for opts.WMTS(zoom=zoom) for when using the maptlotlib backend.

        This workaround is from https://github.com/richieVil/rv_packages/blob/master/rv_geojson.py#L84
        
        used also in script plotly_py.py to address plotly.js issue #3434.
    
        """
        # longitudinal range by zoom level (20 to 1)
        # in degrees, if centered at equator
        lon_zoom_range = np.array([
            0.0007, 0.0014, 0.003, 0.006, 0.012, 0.024, 0.048, 0.096,
            0.192, 0.3712, 0.768, 1.536, 3.072, 6.144, 11.8784, 23.7568,
            47.5136, 98.304, 190.0544, 360.0
        ])
        margin = 1.2
        height = (maxlat - minlat) * margin * width_to_height
        width = (maxlon - minlon) * margin
        lon_zoom = np.interp(width , lon_zoom_range, range(20, 0, -1))
        lat_zoom = np.interp(height, lon_zoom_range, range(20, 0, -1))

        return round(min(lon_zoom, lat_zoom))

    gdfs = [gdf.to_crs(epsg=4326).rename(columns={'geom': 'geometry'}) for gdf in gdfs]

    extent = getBBox(*gdfs)

    aspect_ratio = (extent[1] - extent [0]) / (extent[3] - extent[2])

    zoom = get_zoom_mercator(extent[0], extent[1], extent[2], extent[3], aspect_ratio) 
        
    return (gdfs, zoom)


@to_cProfile
def renderFigure(buildings_in, buildings_out, rivers, basemap=basemap, savefig=savefig, db_name=db_name, viz_type=viz_type):
    
    tiles = gv.tile_sources.OSM()
    
    if basemap and viz_type == 'interactive/':

        # color_index=None makes GeoViews ignore the automatically identified 'use' values dimension according to which
        # a color scheme would otherwise be applied
        buildings_in = gv.Polygons(buildings_in).opts(tools=['hover'], color_index=None, color='red', xaxis=None, yaxis=None)
        buildings_out = gv.Polygons(buildings_out).opts(tools=['hover'], color_index=None, color='lightgrey')
        rivers = gv.Polygons(rivers).opts(color='lightblue')

        features = buildings_in * buildings_out * rivers * tiles

        # Similar to matplotlib legend artists have to be declared separately
        
        popts = dict(show_legend=True, apply_ranges=False)
        bldg_in_leg = gv.Polygons(buildings_in, label="Buildings within 500m of rivers/stream").opts(color_index=None, color='red', **popts)
        bldg_out_leg = gv.Polygons(buildings_out, label="Buildings outside 500m of rivers/stream").opts(color_index=None, color='lightgrey', **popts)
        rivers_leg = gv.Polygons(rivers, label="Rivers/streams").opts(color_index=None, color='lightblue', **popts)

        legend = bldg_in_leg * bldg_out_leg * rivers_leg

        title = "Bokeh's hide/mute legend click policy yet to be exposed in GeoViews"

        layout = (features * legend).opts(width=700, height=500, title=title)

        # gv.Element() does not show in VS Code interpreter, hence this workaround with
        # gv.render and bokeh.plotting.show,
        # otherwise use (gv.Overlay(features * legend).opts())
        p = gv.render(layout)
        
        show(p)
    
    elif basemap == False and viz_type == 'interactive/':

        buildings_in = gv.Polygons(buildings_in).opts(tools=['hover'], color_index=None, color='red', xaxis=None, yaxis=None)
        buildings_out = gv.Polygons(buildings_out).opts(tools=['hover'], color_index=None, color='lightgrey')
        rivers = gv.Polygons(rivers).opts(color='lightblue')
        
        features = buildings_in * buildings_out * rivers

        # Similar to matplotlib legend artists have to be declared separately
        
        popts = dict(show_legend=True, apply_ranges=False)
        bldg_in_leg = gv.Polygons(buildings_in, label="Buildings within 500m of rivers/stream").opts(color_index=None, color='red', **popts)
        bldg_out_leg = gv.Polygons(buildings_out, label="Buildings outside 500m of rivers/stream").opts(color_index=None, color='lightgrey', **popts)
        rivers_leg = gv.Polygons(rivers, label="Rivers/streams").opts(color_index=None, color='lightblue', **popts)

        legend = bldg_in_leg * bldg_out_leg * rivers_leg

        title = "Bokeh's hide/mute legend click policy yet to be exposed in GeoViews"

        layout = (features * legend).opts(width=700, height=500, title=title)

        gv.operation.resample_geometry(layout).opts(width=400, height=400)

        p = gv.render(layout)

        show(p)
        
    elif basemap == False and viz_type == 'static/':           
    
        layout = (gv.Polygons(buildings_in, group="buildings_in") * gv.Polygons(buildings_out, group="buildings_out") * gv.Polygons(rivers, group="rivers")).opts(projection=ccrs.Mercator())

        layout.opts(
            opts.Polygons('buildings_in', cmap=['red'], edgecolor='black', linewidth=0.5, backend="matplotlib"),
            opts.Polygons('buildings_out', cmap=['lightgrey'], edgecolor='black', linewidth=0.5, backend="matplotlib"),
            opts.Polygons('rivers', backend="matplotlib"),
            opts.Overlay(backend='matplotlib')
        )
        
        gv.output(layout, size=500, fig='svg', backend='matplotlib')

        
    elif basemap and viz_type == 'static/':
        
        layout = tiles * gv.Polygons(buildings_in, group="buildings_in") * gv.Polygons(buildings_out, group="buildings_out") * gv.Polygons(rivers, group="rivers").opts(projection=ccrs.Mercator())

        layout.opts(
            opts.Polygons('buildings_in', cmap=['red'], edgecolor='black', linewidth=0.5, backend="matplotlib"),
            opts.Polygons('buildings_out', cmap=['lightgrey'], edgecolor='black', linewidth=0.5, backend="matplotlib"),
            opts.Polygons('rivers', backend="matplotlib"),
            opts.Overlay(backend='matplotlib'),
            opts.WMTS(zoom=zoom, backend='matplotlib')
        )
        
        gv.output(layout, size=500, fig='svg', backend='matplotlib')
    
    
    if savefig and viz_type == 'interactive/':
        if not os.path.exists(outputdir + viz_type):
            os.makedirs(outputdir + viz_type)

        gv.save(layout, outputdir + viz_type + "geoviews (" + db_name + ").html")
    
    elif savefig and viz_type == 'static/':
        if not os.path.exists(outputdir + viz_type):
            os.makedirs(outputdir + viz_type)
        
        gv.save(layout, outputdir + viz_type + "geoviews (" + db_name + ").svg", dpi=600, backend='matplotlib')
    

if __name__ == "__main__":

    buildings_in, buildings_out, rivers = sql2gdf(db_name, password)

    ((buildings_in, buildings_out, rivers), zoom) = prepGDFs(buildings_in, buildings_out, rivers)

    renderFigure(buildings_in, buildings_out, rivers)

    