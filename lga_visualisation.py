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
from shapely.geometry import polygon
import matplotlib.pyplot as plt

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
url = 'https://data.nsw.gov.au/data/api/3/action/datastore_search_sql?sql=SELECT%20notification_date,lga_code19,lga_name19%20from%20%2221304414-1ff1-4243-a5d2-f52778048b29%22%20'

df = extract_from_api(url)

# Now we have our data, we just need to get our shape files so we can visualise the output.
# Note that the shape files are static and sourced from the Australian Bureau of Statistics (ABS):
# https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files
# Note that this file includes LGAs for the entirety of Australia, but all we really care about is NSW
# as that's where our data is from.

# So we just clean the LGA file so it's only got the NSW LGAs in it.
def clean_lgas():
    lgas = gpd.read_file('LGA_2021_AUST_GDA2020.shp')
    
    lgas = lgas.loc[lgas['STE_NAME21'] == 'New South Wales']
    
    lgas.to_file("LGA_2021_NSW_GDA2020.shp")

# Interestingly, the map works but there's a huge part sticking out on the RHS. I'm fairly certain
# from googling that this is Lord Howe Island, however, looking into the min/max x/y axis values
# for the map suggests it's not its own LGA, and instead falls into 'Unincorporated NSW'.
lgas = gpd.read_file('LGA_2021_NSW_GDA2020.shp')
    
# print(lgas.columns)
# print(lgas['geometry'].bounds)

to_remove = lgas.loc[lgas['geometry'].bounds['maxx'] > 157]
# print(to_remove['LGA_NAME21'])

# That's a problem because Unincorporated NSW is also the far west of the state, which we definitely
# don't want to lose. We can barely see the island on the map too since it's so small, so probably
# best to just set the x limit on the map (same way as for matplotlib).

# print(lgas['LGA_NAME21'])
    
lgas['geometry'].plot(figsize=(20,8)).set_xlim(140,154)

lgas = lgas[['LGA_CODE21','LGA_NAME21','geometry']]

# Now to finish cleaning up our case data! With 77000 rows and only ~365 days of data, it looks
# like they're reporting each case as a new line. That's kind of great as it's super granular,
# but for our purposes we can roll it up to LGAs and just see a count of how many in each LGA
# on each day. Here we go!

# print(df.drop_duplicates(keep='first'))

# Yup that looks much more reasonable, 8130 combinations. So let's group them together, reset
# the index and then merge with our LGA shape file. Note that in this case I'm adding a dummy
# column 'count' with values all 1 (as they're each 1 case) so groupby has something to work
# from.

df['count'] = 1
df = df.groupby(['notification_date','lga_code19','lga_name19'])[['count']].count()
# print(df)
df = df.reset_index(drop=False)
# print(df)

df = df.sort_values(by='notification_date', ascending=True)

max_color = df['count'].max()

dates = list(df['notification_date'].unique())

dates = dates[:1]


# We can now generate our plots, but it's tricky! My initial attempt essentially joined
# the gdf and df, but when the plots were done they'd only show the LGAs that had any
# case numbers and not the others. This is essentially because the resultant df, when
# filtered on a particular date, only had records for the LGAs with cases on that date.
# To fix this, we have to merge on each date and then fillna as 0, so the other LGAs
# still appear.

fig, (ax1, ax2) = plt.subplots(ncols=2, sharex=False, sharey=False)
fig.set_figsize = (20,8)
ax1.set_xlim(140,154)
ax2.set_xlim(149,152)
ax2.set_ylim(33,34)

for i in dates:
    print(i)
    temp = df.loc[df['notification_date'] == i]
    merged = pd.merge(lgas, temp, how='left', right_on='lga_code19', left_on='LGA_CODE21')
    merged['count'] = merged['count'].fillna(0)
    merged.plot(column='count', 
                cmap='Reds', 
                vmax=max_color,
                edgecolor='black',
                ax=ax1)
    merged.plot(column='count', 
                cmap='Reds', 
                vmax=max_color,
                edgecolor='black',
                ax=ax2)
    # ax.set_axis_off()
    # ax.set_xlim(140,154)
    # fig.set_title(i)
    plt.savefig(f'{i}.jpg')

# Great! After merging we only lost about 400 rows, but checking the initial extract
# it looks like a few rows didn't have LGAs, which is fine. An expansion might be to clean
# this data a bit more rigorously, but what we have should suffice for now (and in the overall
# dataset before being grouped, it's <1% of the total data available).

