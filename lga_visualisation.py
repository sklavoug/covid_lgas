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
import imageio
import os

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



# Now we have our data, we just need to get our shape files so we can visualise the output.
# Note that the shape files are static and sourced from the Australian Bureau of Statistics (ABS):
# https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files
# Note that this file includes LGAs for the entirety of Australia, but all we really care about is NSW
# as that's where our data is from.

def clean(df):
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
        
    # lgas['geometry'].plot(figsize=(20,8)).set_xlim(140,154)
    
    lgas = lgas[['LGA_CODE21','LGA_NAME21','geometry']]
    
    # NSW is tough to visualise! Most notably because the state is so huge but so much of the population
    # is centred in Sydney and surrounding LGAs, my first run of the map basically showed nothing
    # in the entirety of 2020, which is wrong -- there was COVID there, it was just all in Sydney. The
    # best way to solve this problem is probably to split the map into two subplots, one for Sydney
    # and one for the rest of NSW. I've made a quick CSV mapping file of the LGA_NAME21 column
    # from the lgas dataset to either Sydney/Regional based on the Wikipedia article on NSW
    # LGAs: https://en.wikipedia.org/wiki/Local_government_areas_of_New_South_Wales
    
    syd_non = pd.read_csv('lgas_sydney_regional.csv')
    
    lgas = pd.merge(lgas, syd_non, how='inner', on='LGA_NAME21')
    
    print(lgas)
    
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
    
    # max_color is interesting since we're splitting the plot into two. There's
    # an argument to be made that max_color should be different for Sydney and
    # regional, but I've experienced that argument with online people and it's not
    # fun. Basically it'd look deceptive to have, say the Sydney LGA and the Unincorporated
    # NSW LGA look the same, even though they could have very different numbers of COVID
    # cases.
    
    return df, lgas
    


# We can now generate our plots, but it's tricky! My initial attempt essentially joined
# the gdf and df, but when the plots were done they'd only show the LGAs that had any
# case numbers and not the others. This is essentially because the resultant df, when
# filtered on a particular date, only had records for the LGAs with cases on that date.
# To fix this, we have to merge on each date and then fillna as 0, so the other LGAs
# still appear.

# fig, (ax1, ax2) = plt.subplots(ncols=2, facecolor='black', sharex=False, sharey=False, figsize=(20,8))
# # fig.set_figsize = (40,8)
# # ax1.set_figsize = (40,8)
# # ax2.set_figsize = (20,8)
# fig.tight_layout()
# # plt.figure(facecolor='black')
# ax1.set_title('Regional', y=0, color='white')
# ax2.set_title('Sydney', y=0, color='white')
# ax1.set_axis_off()
# ax2.set_axis_off()
# plt.subplots_adjust(wspace=-0.4)
# ax1.set_xlim(140, 154)
# ax1.set_xlim(140,154)
# ax2.set_xlim(149,152)
# ax2.set_ylim(33,34)

def vis_helper(df, lgas, i):
    print(f'{idx}/{len(dates)}: {i}')
    temp = df.loc[df['notification_date'] == i]
    
    
    merged = pd.merge(lgas, temp, how='left', right_on='lga_code19', left_on='LGA_CODE21')
    merged['count'] = merged['count'].fillna(0)
    # print(merged)
    syd = merged.loc[merged['Region'] == 'Sydney']
    reg = merged.loc[merged['Region'] == 'Regional']
    
    return syd, reg

def visualise(df, lgas, i):
    syd, reg = vis_helper(df, lgas, i)
    
    fig, (ax1, ax2) = plt.subplots(ncols=2, facecolor='black', sharex=False, sharey=False, figsize=(20,8))
    ax1.set_title('Regional', y=0, color='white')
    ax2.set_title('Sydney', y=0, color='white')
    ax1.set_axis_off()
    ax2.set_axis_off()
    plt.subplots_adjust(wspace=-0.4)
    ax1.set_xlim(140, 154)
    
    syd.plot(column='count',
             cmap='plasma',
             vmax=max_color,
             edgecolor='black',
             ax=ax2)
    
    reg.plot(column='count',
             cmap='plasma',
             vmax=max_color,
             edgecolor='black',
             ax=ax1)
    
    fig.suptitle(i, fontsize=16, color='white')
    plt.savefig(f'./output/{i}.jpg')
    plt.close('all')

def visualise_w_vacc(df, lgas, i):
    
    temp = df.loc[df['notification_date'] == i]
    
    first_vacc = int(temp['First'].unique()[0]) / 6565651 * 100
    second_vacc = int(temp['Second'].unique()[0]) / 6565651 * 100
    
    # num_vacc = 91
    # prop_vacc = int(num_vacc) / 6565651
    
    vacc = {'Second': [second_vacc],
            'First': [first_vacc-second_vacc],
            'Total': [100-first_vacc]}
    
    vacc_df = pd.DataFrame.from_dict(vacc)
    
    # print(vacc_df)
    
    syd, reg = vis_helper(df, lgas, i)
    

    fig, (ax1, ax2, ax3) = plt.subplots(ncols=3, 
                                        facecolor='black', 
                                        sharex=False, 
                                        sharey=False, 
                                        figsize=(20,8),
                                        gridspec_kw={'width_ratios': [10,10,1]})
    # ax3.set_figsize((2,8))
    ax3.set_facecolor('black')
    ax3.text(-1, first_vacc, round(first_vacc,2), ha='left',
          weight='bold', color='goldenrod')
    ax3.text(-1, vacc['Second'][0], round(vacc['Second'][0],2), ha='left',
             weight='bold', color='lightseagreen')
    ax3.text(0.5, first_vacc, 'First', ha='left', color='white')
    ax3.text(0.5, second_vacc, 'Second', ha='left', color='white')
    # ax3.bar_label(labels=round(vacc['Vacc'][0],2))
    # ax3.set_axis_bgcolor('black')
    vacc_plot = vacc_df.plot(ax=ax3,
                             kind='bar',
                             stacked=True,
                             color={'First': 'goldenrod',
                                    'Second': 'lightseagreen',
                                    'Total': 'black'},
                             edgecolor='white',
                             legend=False)
    # vacc_plot.bar_label(round(vacc['Vacc'][0],2))
    # for c in vacc_plot.containers[::2]:
    #     vacc_plot.bar_label(c, label_type='edge', fmt='%0.1f', padding=10)
    
    # vacc_plot.set_axis_bgcolor('black')
    
    ax1.set_title('Regional', y=0, color='white')
    ax2.set_title('Sydney', y=0, color='white')
    ax3.set_title('Vaccinations', y=1, color='white')
    ax1.set_axis_off()
    ax2.set_axis_off()
    plt.subplots_adjust(wspace=0)
    ax1.set_xlim(140, 154)
    
    syd.plot(column='count',
             cmap='plasma',
             vmax=max_color,
             edgecolor='black',
             ax=ax2)
    
    reg.plot(column='count',
             cmap='plasma',
             vmax=max_color,
             edgecolor='black',
             ax=ax1)
    
    fig.suptitle(f'Cases and Vaccinations\n{i}', fontsize=16, color='white')
    plt.savefig(f'./output_vacc/vacc_{i}.jpg')
    plt.close('all')
    # print(syd, reg)
    
    
# Great! After merging we only lost about 400 rows, but checking the initial extract
# it looks like a few rows didn't have LGAs, which is fine. An expansion might be to clean
# this data a bit more rigorously, but what we have should suffice for now (and in the overall
# dataset before being grouped, it's <1% of the total data available).

# Extract a subset of the data. It's clear for our purposes (a map of COVID cases
# in NSW) we don't really care about most of the data; our shape files are for
# LGAs so we'll keep the LGA name field (and possibly the code in case name doesn't
# line up), and we'll keep the date because this is going to be based on date. Otherwise
# we don't need postcode/suburb, NSW Health have been kind enough to conform them to
# LGAs already.
# url = 'https://data.nsw.gov.au/data/api/3/action/datastore_search?resource_id=21304414-1ff1-4243-a5d2-f52778048b29&limit=10'  

# extract_from_api(url)

def create_gif(vis_type):
    if vis_type == 'vacc':
        directory = './output_vacc'
        filename = 'visualisation_vacc.gif'
    else:
        directory = './output'
        filename = 'visualisation.gif'
        
    images = []
    for file_idx, filename in enumerate(os.listdir(directory)):
        if filename[-4:] == '.jpg':
            print(file_idx)
            images.append(imageio.imread(f'{directory}/{filename}'))
    imageio.mimsave('visualisation_vacc.gif', images, fps=30, subrectangles=True)


# With our second query we've got only what we wanted and we've extracted all the data,
# all 77,000 rows of it.
url = 'https://data.nsw.gov.au/data/api/3/action/datastore_search_sql?sql=SELECT%20notification_date,lga_code19,lga_name19%20from%20%2221304414-1ff1-4243-a5d2-f52778048b29%22%20'

df = extract_from_api(url)

df, lgas = clean(df)

# dates = list(df['notification_date'].unique())

# for idx, date in enumerate(dates):
#     if idx == 0:
#         visualise(df, lgas, date)

# create_gif()
# imageio.help('gif')

# Vaccination data sourced from https://www.health.gov.au/resources/collections/covid-19-vaccination-daily-rollout-update
vacc = pd.read_csv('vaccinations.csv')
vacc = vacc.fillna(0)

# print(df, vacc)

df = pd.merge(df, vacc, how='left', left_on='notification_date', right_on='Date')

print(df)

max_color = df['count'].max()

df = df.dropna(subset=['Date'])

# print(df)

dates = list(df['notification_date'].unique())

print(dates)

for idx, date in enumerate(dates):
    visualise_w_vacc(df, lgas, date)
    
create_gif('vacc')


