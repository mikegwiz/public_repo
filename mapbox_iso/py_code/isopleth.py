# isopleth.py 
# Contains custom class called Isopleth that uses the Mapbox Isochrone API to generate,
# store, and viualize isochrones and isodistance shapes.

# Michael Giangrande
# 2/24
# mikegwiz@gmail.com



import geopandas as gpd
from geopandas.explore import _categorical_legend
import pandas as pd
import folium
import folium.plugins as plugins
import requests
from urllib.parse import urlencode

class Isopleth:
    def __init__(self, mapbox_api_key:str):
        '''
        Initializes a Mapbox client.

        :param mapbox_api_key: Mapbox API key.
        :type mapbox_api_key: str'''

        self.api_key = mapbox_api_key
        self.isochrones = []
        self.isodists = []

    @staticmethod
    def mb_iso_api_url(self, x:float, y:float, colors_list:[list[str]], meters_list:[list[int]]=[], minutes_list:[list[int]]=[], mode:str="driving"):

        '''This static method generates the API used to call to the MapBox Isochrone API.
        
        :param x: The longitude coordinate
        :type x: float

        :param y: The latitude coordinate
        :type y: float

        :param colors_list: List of hex color codes, equal in length to the number of meters or minutes
        :type colors_list: list of str

        :param meters_list: List of meters to construct isodistances. Up to four accepted by API.
            Default is empty list. Either meters_list OR minutes_list is a requirement. Only one or the other.
        :type meters_list: list of int

        :param minutes_list: List of minutes to construct isochrones. Up to four accepted by API.
            Default is empty list. Either meters_list OR minutes_list is a requirement. Only one or the other.
        :type minutes_list: list of int

        :param mode: Specifies the mode of transport to use when calculating isopleth. 
            Options are "driving-traffic", "driving", "walking", "cycling".
            Default is "driving".
        :type mode: str

        :returns: MapBox Isochrone API URL
        rtype: str'''

        base_url = f"https://api.mapbox.com/isochrone/v1/mapbox/{mode}/{x},{y}"
        params = {
            'contours_colors': colors_list,
            'polygons': "true",
            'access_token': self.api_key
        }
        
        if meters_list:
            m_param = {'contours_meters': meters_list}
            params = {**m_param, **params}
        if minutes_list:
            min_param = {'contours_minutes': minutes_list}
            params = {**min_param, **params}

        e_params = urlencode(params)
        api_url = f'{base_url}?{e_params}'

        return(api_url)

    def add_isochrone(self, gdf, id_col:str, minute_list=[5, 10, 15], colors:list=[], mode="driving"):

        '''This method makes the call to the MapBox Isochrone API and generates the geopandas shapes for all x,y
        in the geopandas xy input. Up to four time intervals (in minutes) can be sent (must have same number of corresponding colors),
        and the result is appended to the isochrone instance.
        
        :param gdf: The Geopandas point dataframe of origins to be processed.
        :type gdf: gdf

        :param id_col: The gdf column name containing the unique identifier.
        :type y: str

        :param minutes_list: List of minutes to construct isochrones. Up to four accepted by API.
            Default is [5, 10, 15]. 
        :type minutes_list: list of int

        :param colors: List of hex color codes, equal in length to the number of minutes
        :type colors_list: list of str

        :param mode: Specifies the mode of transport to use when calculating isopleth. 
            Options are "driving-traffic", "driving", "walking", "cycling".
            Default is "driving".
        :type mode: str
        '''
        lon = gdf.to_crs(4326).geometry.x
        lat = gdf.to_crs(4326).geometry.y

        colors = [x.replace(r"#","") for x in colors]

        minutes = ','.join(str(m) for m in minute_list)
        con_color = ','.join(colors)

        for i, row in gdf.iterrows():
            url = self.mb_iso_api_url(self,lon[i],lat[i],mode=mode,colors_list=con_color,minutes_list=minutes)
                
            response = requests.get(url)
            data=response.json()
            temp_gdf = gpd.GeoDataFrame.from_features(data["features"])
            temp_gdf['mode'] = mode
            temp_gdf[id_col] = gdf[id_col][i]
            temp_gdf.drop(columns=['fill-opacity', 'fillColor', 'opacity', 'fill', 'fillOpacity'], inplace=True)
            temp_gdf.set_crs(4326, allow_override=True)

            self.isochrones.append(temp_gdf)       

    def get_isochrones(self):

        '''Returns the isochrones instance as a gdf.'''
        isochrones = pd.concat(self.isochrones, ignore_index=True)

        return gpd.GeoDataFrame(isochrones, geometry="geometry", crs="EPSG:4326")

    def get_dissolve_isochrones(self):

        '''Dissolves the isochrones instance by time (contour) and travel mode. Returns a gdf.'''

        isochrones = pd.concat(self.isochrones, ignore_index=True)
        diss_gdf = gpd.GeoDataFrame(isochrones, geometry="geometry", crs="EPSG:4326")
        diss_gdf.drop('Address', axis=1, inplace=True)
        diss_gdf = diss_gdf.dissolve(by=['contour', 'metric'])
        return diss_gdf.sort_values('contour', ascending = False).reset_index()
    
    
    
    def add_isodist(self, gdf, id_col:str, distance_miles:list, colors:list, mode="driving"):

        '''This method makes the call to the MapBox Isochrone API and generates the geopandas shapes for all x,y
        in the geopandas xy input. Up to four distances (in miles) can be sent (must have same number of corresponding colors),
        and the result is appended to the isodists instance.
        
        :param gdf: The Geopandas point dataframe of origins to be processed.
        :type gdf: gdf

        :param id_col: The gdf column name containing the unique identifier.
        :type y: str

        :param meters_list: List of minutes to construct isodists. Up to four accepted by API. 
        :type meters_list: list of int

        :param colors: List of hex color codes, equal in length to the number of meters
        :type colors_list: list of str

        :param mode: Specifies the mode of transport to use when calculating isodist. 
            Options are "driving-traffic", "driving", "walking", "cycling".
            Default is "driving".
        :type mode: str
        '''

        LON = gdf.to_crs(4326).geometry.x
        LAT = gdf.to_crs(4326).geometry.y

        distance_meter = [int(round(x * 1609.34,0)) for x in distance_miles]
        colors = [x.replace(r"#","") for x in colors]

        meters = ','.join(str(m) for m in distance_meter)
        con_color = ','.join(colors)

        for i, row in gdf.iterrows():
            url = self.mb_iso_api_url(self, LON[i],LAT[i],colors_list=con_color,meters_list=meters)
                
            response = requests.get(url)
            data=response.json()
            temp_gdf = gpd.GeoDataFrame.from_features(data["features"])
            temp_gdf['meters'] = temp_gdf['contour'].astype(str)
            temp_gdf['contour'] = [str(x) for x in list(reversed(distance_miles))]
            temp_gdf[id_col] = gdf[id_col][i]
            temp_gdf.drop(columns=['fill-opacity', 'fillColor', 'opacity', 'fill', 'fillOpacity'], inplace=True)
            temp_gdf.set_crs(4326, allow_override=True)

            self.isodists.append(temp_gdf)

    def get_isodists(self):

        '''Returns the isodists instance as a gdf.'''
        isodists = pd.concat(self.isodists, ignore_index=True)

        return gpd.GeoDataFrame(isodists, geometry="geometry", crs="EPSG:4326")
    
    def get_dissolve_isodists(self):

        '''Dissolves the isodists instance by distance and returns as a gdf.'''

        isodists = pd.concat(self.isodists, ignore_index=True)
        diss_gdf = gpd.GeoDataFrame(isodists, geometry="geometry", crs="EPSG:4326")
        diss_gdf.drop('Address', axis=1, inplace=True)
        diss_gdf = diss_gdf.dissolve(by=['contour', 'metric'])
        diss_gdf['meters'] = diss_gdf['meters'].astype(int)
        return diss_gdf.sort_values('meters', ascending = False).reset_index()
    

    
    def map_iso(self, iso_gdf):

        '''Maps the isochrones or isodists in an interactive Folium map. The inputs to this method are the iso gdb.
        
        :param iso_gdf: The Geopandas isodistance or isochrome geopandas to be mapped.
        :type gdf: gdf

        :returns: Folium map instance
        '''
        
        bin = iso_gdf['contour'].unique().tolist()
        iso_colors = iso_gdf['color'].tolist()
        rev_bin = list(reversed(bin))
        m1 = folium.Map(tiles=None)
        folium.TileLayer('CartoDB positron',name="Light Map",control=False).add_to(m1)

        map_strings = [" miles", "Number of miles: ", "Isodistance miles: "]
        if iso_gdf['metric'][0]=='time':
            map_strings = [" minutes", "Number of minutes: ", "Isochrome minutes: "]

        # geopandas explore iso buffers
        for i, val in enumerate(rev_bin):
            iso_gdf[iso_gdf['contour']==bin[i]].explore(column = "contour",
                    name=f"{bin[i]}{map_strings[0]}",
                    tooltip=["contour"],
                    tooltip_kwds=dict(aliases=[map_strings[1]]),
                    m=m1, 
                    style_kwds=dict(color="black", fillColor=iso_colors[i], fillOpacity=0.4, weight=1),
                    legend=False)

        #Add categorial legend
        _categorical_legend(m1, title=map_strings[2], categories=rev_bin, colors=list(reversed(iso_colors)))

        folium.LayerControl().add_to(m1)
        m1.fit_bounds(m1.get_bounds(), padding=(10, 10))
        return m1
    

    def map_dual_iso(self, iso_gdf_left, iso_gdf_right):

        '''Maps the isochrones or isodists in an interactive Folium map. The inputs to this method are the iso gdb and the colors.
        
        param iso_gdf_left: The Geopandas isodistance or isochrome geopandas to be mapped on the left side.
        :type gdf: gdf

        param iso_gdf_right: The Geopandas isodistance or isochrome geopandas to be mapped on the right side.
        :type gdf: gdf

        :returns: Folium map instance'''
        
        l_bin = iso_gdf_left['contour'].unique().tolist()
        r_bin = iso_gdf_right['contour'].unique().tolist()
        iso_colors_left = iso_gdf_left['color'].unique().tolist()
        iso_colors_right = iso_gdf_right['color'].unique().tolist()
        rev_l_bin = list(reversed(l_bin))
        rev_r_bin = list(reversed(r_bin))
        dual_map = plugins.DualMap(tiles=None)
        folium.TileLayer('CartoDB positron',name="Light Map",control=False).add_to(dual_map.m1)
        folium.TileLayer('CartoDB positron',name="Light Map",control=False).add_to(dual_map.m2)


        l_map_strings = [" miles", "Number of miles: "]
        l_legend_cats = [f"{x} miles" for x in rev_l_bin]
        if iso_gdf_left['metric'][0]=='time':
            l_map_strings = [" minutes", "Number of minutes: "]
            l_legend_cats = [f"{x} minutes ({iso_gdf_left['mode'][0]})" for x in rev_l_bin]
        
        r_map_strings = [" miles", "Number of miles: "]
        r_legend_cats = [f"{x} miles" for x in rev_r_bin]
        if iso_gdf_right['metric'][0]=='time':
            r_map_strings = [" minutes", "Number of minutes: "]
            r_legend_cats = [f"{x} minutes ({iso_gdf_right['mode'][0]})" for x in rev_r_bin]

        # geopandas explore iso buffers to left
        for li, lval in enumerate(rev_l_bin):
            iso_gdf_left[iso_gdf_left['contour']==l_bin[li]].explore(column = "contour",
                    name=f"{l_bin[li]}{l_map_strings[0]}",
                    tooltip=["contour"],
                    tooltip_kwds=dict(aliases=[l_map_strings[1]]),
                    m=dual_map.m1, 
                    style_kwds=dict(color="black", fillColor=iso_colors_left[li], fillOpacity=0.4, weight=1),
                    legend=False)
            
        # geopandas explore iso buffers to right
        for ri, rval in enumerate(rev_r_bin):
            iso_gdf_right[iso_gdf_right['contour']==r_bin[ri]].explore(column = "contour",
                    name=f"{r_bin[ri]}{r_map_strings[0]}",
                    tooltip=["contour"],
                    tooltip_kwds=dict(aliases=[r_map_strings[1]]),
                    m=dual_map.m2, 
                    style_kwds=dict(color="black", fillColor=iso_colors_right[ri], fillOpacity=0.4, weight=1),
                    legend=False)

        #Add categorial legends
        legend_cats, iso_colors = l_legend_cats + r_legend_cats, list(reversed(iso_colors_left)) + list(reversed(iso_colors_right))
        if (l_legend_cats == r_legend_cats) and (iso_colors_left == iso_colors_right):
            legend_cats = l_legend_cats
            iso_colors = iso_colors_left
        _categorical_legend(dual_map,
                            title="Isopleth Comparison",
                            categories=legend_cats,
                            colors=list(reversed(iso_colors)))

        folium.LayerControl().add_to(dual_map.m1)
        folium.LayerControl().add_to(dual_map.m2)
        l_size = iso_gdf_left['geometry'].to_crs(3395).map(lambda p: p.area / 10**6)[0]
        r_size = iso_gdf_right['geometry'].to_crs(3395).map(lambda t: t.area / 10**6)[0]

        if l_size > r_size:
            dual_map.m1.fit_bounds(dual_map.m1.get_bounds(), padding=(10, 10))
        else:
            dual_map.m1.fit_bounds(dual_map.m2.get_bounds(), padding=(10, 10))
        return dual_map
    






    

    
