# -*- coding: utf-8 -*-
"""
Created on Thu Nov 11 15:57:34 2021

@author: Arden Morbe
"""

# Extract COVID case data from the data.nsw.gov.au API.
# Note that the data is also available from the API as a csv file, but
# connecting directly makes it easier to get the most up-to-date
# data available.

import pandas as pd
import json
from urllib.request import urlopen
import geopandas as gpd

def extract_from_api(url):
    '''

    Parameters
    ----------
    url : string (url)
        A data.nsw.gov.au API URL.

    Returns
    -------
    df: DataFrame
        Contains the data requested in tabular form.

    '''
    fileobj = urlopen(url)
    
    # Get JSON data from API and convert to a dictionary
    x = fileobj.read()
    x = json.loads(x)
    
    # There's metadata attached that we can ignore, as we only
    # want the results.
    x = x['result']['records']
    
    # Convert dictionary of results to DataFrame.
    df = pd.DataFrame.from_dict(x)
    
    print(df)
    
    return df

# Extract a subset of the data. It's clear for our purposes (a map of COVID cases
# in NSW) we don't really care about most of the data; our shape files are for
# LGAs so we'll keep the LGA name field (and possibly the code in case name doesn't
# line up), and we'll keep the date because this is going to be based on date. Otherwise
# we don't need postcode/suburb, NSW Health have been kind enough to conform them to
# LGAs already.
url = 'https://data.nsw.gov.au/data/api/3/action/datastore_search?resource_id=21304414-1ff1-4243-a5d2-f52778048b29&limit=10'  

# extract_from_api(url)

# With our second query we've got only what we wanted and we've extracted all the data,
# all 77,000 rows of it.
url = 'https://data.nsw.gov.au/data/api/3/action/datastore_search_sql?sql=SELECT%20notification_date,lga_name19%20from%20%2221304414-1ff1-4243-a5d2-f52778048b29%22%20'

# extract_from_api(url)

# Now we have our data, we just need to get our shape files so we can visualise the output.
# Note that the shape files are static and sourced from the Australian Bureau of Statistics (ABS):
# https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files
# Note that this file includes LGAs for the entirety of Australia, but all we really care about is NSW
# as that's where our data is from.

# So we just clean the LGA file so it's only got the NSW LGAs in it.
def clean_lgas():
    lgas = gpd.read_file('LGA_2021_AUST_GDA2020.shp')
    
    lgas = lgas.loc[lgas['STE_NAME21'] == 'New South Wales']
    
    print(lgas.columns)
    
    for i in lgas.columns:
        print(lgas[i])
    
    lgas.to_file("LGA_2021_NSW_GDA2020.shp")
    
lgas = gpd.read_file('LGA_2021_NSW_GDA2020.shp')

print(lgas)
    



