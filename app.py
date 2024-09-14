import streamlit as st 
import folium
from geopy.geocoders import MapBox
from folium.plugins import HeatMap
# !pip install mapbox
from mapbox import Geocoder


import requests
from streamlit_folium import st_folium
import geopandas as gpd 
import pandas as pd 
import plotly.express as px
import datetime as dt
import os
from dotenv import load_dotenv, find_dotenv

# !pip install geopy -U
# run with bash command from project folder: streamlit run /app.py

# from dotenv import load_dotenv, find_dotenv
# _ = load_dotenv(find_dotenv()) # read local .env file
load_dotenv('.')

# GEOCODING_API_KEY = os.getenv('GEOCODING_API_KEY')

GEOCODING_API_KEY = st.secrets['GEOCODING_API_KEY']


MAPBOX_API_KEY = os.getenv('MAPBOX_API_KEY')
ISOCHRONE_API_URL = os.getenv('ISOCHRONE_API_URL')

ISOCHRONE_API_URL = "https://api.mapbox.com/isochrone/v1/mapbox/driving/"
geocoder = Geocoder(access_token=MAPBOX_API_KEY)


# counties shapefile from: https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html
counties = gpd.read_file('data/cb_2018_us_county_5m')
counties['FIPS'] = counties.STATEFP + counties.COUNTYFP

# data drawn from: https://github.com/CSSEGISandData/COVID-19/tree/master/csse_covid_19_data
cases = pd.read_csv('data/cases15jul20.csv',dtype={'FIPS':str})
cases_timeseries = pd.read_csv('data/cases_timeseries.csv', dtype={'FIPS':str})

counties = counties.merge(cases,on='FIPS')

# Initialize Mapbox geocoder
geolocator = MapBox(api_key=GEOCODING_API_KEY)

tab1, tab2 = st.tabs(["Demo", "About"])


with tab1:
    st.markdown("**Isochrones** are a great way to distill geospatial data down to the lived experience of a user.  With one simple API call, you can present someone with just the portion of your data that is within an hour's drive of where they are.  That can be a powerful for a number of behavioral science applications.")

    st.title("This is how CovidCommitment worked")



    # User input for ZIP code
    zip_code = st.text_input("Enter a City, Town, or ZIP Code:")

    if zip_code:

        # Geocode the ZIP code to get its centroid
        # location = geolocator.geocode(f"{zip_code}, USA")

        location = geocoder.forward(f"{zip_code}, USA")


        coordinates = location.json()['features'][0]['center']
        center = [float(coordinates[1]), float(coordinates[0])]
        # Make a request to Mapbox Isochrone API
        response = requests.get(
            f"{ISOCHRONE_API_URL}{center[1]},{center[0]}.json?contours_minutes=60&polygons=true&access_token={MAPBOX_API_KEY}"
        )
        data = response.json()
        isochrone = gpd.GeoDataFrame.from_features(data)[0:1].geometry.item()
        # Create a Leaflet map
        m = folium.Map(location=center, zoom_start=8)
        folium.TileLayer('cartodbpositron').add_to(m)
        folium.GeoJson(data).add_to(m)

        # Add the isochrone polygons as GeoJSON to the map
        folium.GeoJson(data).add_to(m)
        overlap_fips = []
        for row in counties.itertuples():
            if isochrone.intersects(row.geometry):
                overlap_fips.append(row.FIPS)
                folium.GeoJson(row.geometry, style_function=lambda feature: {
                    "fillColor": "orange",
                    "color": "orange",
                    "opacity":.8
                },
                tooltip=row.NAME + ': ' +  str(row.Active) + ' active cases | ' + str(row.Deaths) + ' deaths as of 15 Jul 20',
                ).add_to(m)

        st_data = st_folium(m, width=725)


        # Make trend line plot
        overlap_counties_timeseries = cases_timeseries[cases_timeseries.FIPS.isin(overlap_fips)]
        chart_cases_timeseries = pd.DataFrame(
            overlap_counties_timeseries[[col for col in overlap_counties_timeseries if '/' in col]].groupby(level=0).sum().sum()
            ).reset_index().rename(columns={'index':'date',0:'cases'})
        chart_cases_timeseries['date'] = pd.to_datetime(chart_cases_timeseries['date'])

        # Create a Plotly line plot
        fig = px.line(chart_cases_timeseries[chart_cases_timeseries.date<=dt.datetime(2020,7,16,0,0)], x='date', y='cases', title='Cumulative covid cases within about an hour drive of '+zip_code +' (since Jan 2020)')
        fig.update_traces(line_color='orange', line_width=5)

        # Customize the plot (optional)
        fig.update_xaxes(title_text='Date')
        fig.update_yaxes(title_text='Total Cases')
        st.plotly_chart(fig)

with tab2:
    st.markdown('# This is the explainer')