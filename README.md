# covid_lgas
Visualisation of COVID cases by NSW LGAs over time using pandas and geopandas.

![](https://github.com/sklavoug/covid_lgas/blob/main/visualisation.gif)

Sources:
- Vaccination data sourced from [Federal COVID data](https://www.health.gov.au/resources/collections/covid-19-vaccination-daily-rollout-update). Note that there are some inconsistencies in vaccination reporting, notably that the PDF reports include a 'Total vaccine doses' figure for NSW and a breakdown of doses by age (16+, 12-15, etc.) and dose number (1 or 2) which don't line up. The PDF reports list the Australian Immunisation Register as the source for both figures. Where data by dose number is available, this has been used; otherwise the higher-level total number of vaccinations is used instead. Federal Health's PDF reports only include dose number and age breakdowns from 2 July onwards; prior to this the higher-level total number of vaccinations is used. Because of the inconsistencies in these figures, the vaccination bar is indicative only.
- NSW case data sourced from [data.nsw.gov.au API](https://data.nsw.gov.au/nsw-covid-19-data/cases).
- LGA shape files sourced from [ABS Downloads](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files).
