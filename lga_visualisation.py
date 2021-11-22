# -*- coding: utf-8 -*-
"""
Created on Thu Nov 11 15:57:34 2021
@author: SKLAVOUG
"""

# Extract COVID case data from the data.nsw.gov.au API and cross-reference with
# federal vaccination data to create a map of cases with a growing bar of
# vaccinations.

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
    
    # There's metadata attached that we can ignore, as we only want the results.
    x = x['result']['records']
    
    # Convert dictionary of results to DataFrame.
    df = pd.DataFrame.from_dict(x)
    
    return df



# Now we have our data, we just need to get our shape files so we can visualise the output.
# Note that the shape files are static and sourced from the Australian Bureau of Statistics (ABS):
# https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files
# Note that this file includes LGAs for the entirety of Australia, but all we really care about is NSW
# as that's where our data is from.

def clean(df):
    # Clean the LGA file so it's only got the NSW LGAs in it.
    def clean_lgas():
        lgas = gpd.read_file('LGA_2021_AUST_GDA2020.shp')
        
        lgas = lgas.loc[lgas['STE_NAME21'] == 'New South Wales']
        
        lgas.to_file("LGA_2021_NSW_GDA2020.shp")
    
    # There's a big (mostly) empty RHS of the generated map -- I suspect this is Lord Howe Island
    # off to the right, but drilling down it's listed as 'Unincorporated NSW', which also includes
    # the Far West region. To remove it we just set the x limit on the map without removing it from
    # the source.
    lgas = gpd.read_file('LGA_2021_NSW_GDA2020.shp')
    
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
    
    # There's >70K rows in the cases API extract, which given that it's only been around 18 months
    # since the dataset started, means that each case is its own row. For our purposes we want to
    # roll these up by LGA, so set a 'count' column to 1 and then groupby date and LGA.
    df['count'] = 1
    df = df.groupby(['notification_date','lga_code19','lga_name19'])[['count']].count()
    df = df.reset_index(drop=False)

    df = df.sort_values(by='notification_date', ascending=True)
    
    return df, lgas

# Function to help with visualisation, notably by splitting Sydney and regional into two maps.
def vis_helper(df, lgas, i):
    print(f'{idx}/{len(dates)}: {i}')
    temp = df.loc[df['notification_date'] == i]
    
    merged = pd.merge(lgas, temp, how='left', right_on='lga_code19', left_on='LGA_CODE21')
    merged['count'] = merged['count'].fillna(0)
    
    syd = merged.loc[merged['Region'] == 'Sydney']
    reg = merged.loc[merged['Region'] == 'Regional']
    
    return syd, reg

# Workhorse visualisation function, including creating subplots for each figure, setting colours
# and dimensions, and saving the figure to a specific 'output' folder.
def visualise_w_vacc(df, lgas, i):
    
    temp = df.loc[df['notification_date'] == i]
    
    # Split into first and second vaccination as proportions of 100% (for the bar).
    first_vacc = int(temp['First'].unique()[0]) / 6565651 * 100
    second_vacc = int(temp['Second'].unique()[0]) / 6565651 * 100
    
    vacc = {'Second': [second_vacc],
            'First': [first_vacc-second_vacc],
            'Total': [100-first_vacc]}
    
    vacc_df = pd.DataFrame.from_dict(vacc)
    
    syd, reg = vis_helper(df, lgas, i)
    
    # Create subplots
    fig, (ax1, ax2, ax3) = plt.subplots(ncols=3, 
                                        facecolor='black', 
                                        sharex=False, 
                                        sharey=False, 
                                        figsize=(20,8),
                                        gridspec_kw={'width_ratios': [10,10,1]})

    # Set text for vaccination progress bar
    ax3.set_facecolor('black')
    ax3.text(-1, first_vacc, round(first_vacc,2), ha='left',
          weight='bold', color='goldenrod')
    ax3.text(-1, vacc['Second'][0], round(vacc['Second'][0],2), ha='left',
             weight='bold', color='lightseagreen')
    ax3.text(0.5, first_vacc, 'First', ha='left', color='white')
    ax3.text(0.5, second_vacc, 'Second', ha='left', color='white')

    # Create plot
    vacc_plot = vacc_df.plot(ax=ax3,
                             kind='bar',
                             stacked=True,
                             color={'First': 'goldenrod',
                                    'Second': 'lightseagreen',
                                    'Total': 'black'},
                             edgecolor='white',
                             legend=False)
    
    # Set titles and plot maps    
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
    
    # Set title for figure and save the plot in an 'output_vacc' folder
    fig.suptitle(f'Cases and Vaccinations\n{i}', fontsize=16, color='white')
    plt.savefig(f'./output_vacc/vacc_{i}.jpg')
    plt.close('all')
    
# Create a gif from the separate images
def create_gif():
    directory = './output_vacc'
    filename = 'visualisation_vacc.gif'
        
    images = []
    for file_idx, filename in enumerate(os.listdir(directory)):
        if filename[-4:] == '.jpg':
            print(file_idx)
            images.append(imageio.imread(f'{directory}/{filename}'))
    imageio.mimsave('visualisation_vacc.gif', images, fps=30, subrectangles=True)


# Extract case data from API and merge with LGA shape file (after some cleaning)
url = 'https://data.nsw.gov.au/data/api/3/action/datastore_search_sql?sql=SELECT%20notification_date,lga_code19,lga_name19%20from%20%2221304414-1ff1-4243-a5d2-f52778048b29%22%20'
df = extract_from_api(url)
df, lgas = clean(df)

# Vaccination data sourced from https://www.health.gov.au/resources/collections/covid-19-vaccination-daily-rollout-update
vacc = pd.read_csv('vaccinations.csv')
vacc = vacc.fillna(0)

# Merge case and vaccincation data on date.
df = pd.merge(df, vacc, how='left', left_on='notification_date', right_on='Date')

# Set max_color (i.e., the brightest point the map can be). There's an argument to be made
# that regional and Sydney should have two different max_colors since they're two different
# maps, but that would be misleading and make it seem like there was more COVID in the regions
# than there was.
max_color = df['count'].max()

df = df.dropna(subset=['Date'])

dates = list(df['notification_date'].unique())

# Create an image for each date, with regional map on the LHS, Sydney map in the middle and
# the bar of vaccinations on the RHS.
for idx, date in enumerate(dates):
    visualise_w_vacc(df, lgas, date)

# Combine all the images into a GIF.
create_gif()