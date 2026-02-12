# Vancouver Crime Patterns Dashboard

### Section 1: Motivation and Purpose
Target audience: Residents planning to rent or buy a home in Vancouver, or tourists planning to visit Vancouver, like many of our classmates are considering or have done
When choosing a residential area for either long or short term stays, community safety is a crucial consideration for renters and homebuyers. Crime data is often presented in raw tabular form, which is often information-heavy and complex, making it difficult for residents to assess safety trends across different neighborhoods. To help potential residents make more informed housing decisions, we plan to build an interactive data visualization application that will allow users to explore crime data from different neighborhoods and time factors in Vancouver. This application will display the distribution and trends of various crime types across different neighborhoods and allow users to compare data by year, month, hour, location, and crime type, providing a clearer understanding of community safety and supporting more informed renting or buying decisions.


### Section 2: Description of the data

We will visualize a crime dataset provided by the Vancouver Police Department's (VPD) open data platform, GeoDASH. This dataset records crimes committed between 2003 and 2023 and is licensed under an Open Database License, allowing public use and display. The data originates from the PRIME BC Police Records Management System and includes only "Founded Incidents" confirmed by police investigations. We will filter the data to just 2019-2023, 5 years of data, as we do not believe that data older than the proposed timeframe would be relevant to our target audience.

The reduced dataset contains approximately 185,000 observations, each representing an independent crime event (event-level data), rather than aggregated statistics. The data includes 10 variables, primarily: crime type (TYPE), time of occurrence (YEAR, MONTH, DAY, HOUR, MINUTE), and location-related information (HUNDRED_BLOCK, NEIGHBOURHOOD, X, Y). The overall missing data rate is extremely low (0.00346%), mainly concentrated in location-related fields.

During the visualization process, we will derive several summary indicators from the raw data, including the total number of crimes by year, the distribution of crime in different communities, the proportion of different crime types, and crime trend changes over time by both month and hour. These derived indicators will be used to support trend analysis and spatial comparisons.
It is important to note that, to protect privacy, the location information for some crimes (especially those involving physical assault) has been offset, and the data does not represent all alarm records. Furthermore, the statistical methods used for this data differ from Statistics Canada's UCR reporting rules, therefore the two cannot be directly compared.

We will also not be attempting any prediction modeling as it seems inappropriate given the context of the data, just multiple historical trends.


### Section 3: Research questions and usage scenarios

#### Research Questions
This project aims to explore the following research questions:
* How have different types of crime changed over time in Vancouver since 2019?
* Are there noticeable seasonal or hourly patterns in specific crime categories or neighbourhoods?
* Which neighbourhoods experience higher or lower concentrations of particular crime types?
* How do spatial crime patterns shift in the city across years?
* Are there relationships between time of day and specific types of incidents?

These questions will guide the design of interactive visualizations and filtering features in the dashboard.

#### Usage Scenario
Alex just graduated university and has found a job in Vancouver, his dream city. He is planning to rent in Vancouver and wants to understand crime trends in different neighborhoods to make sure he will be safe during the duration of his stay. He wants to see overall crime trends in various neighborhoods over the past five years and compare the distribution and trend change vs time of different crime types in each neighborhood. When he uses our Vancouver Crime Patterns Dashboard, he can filter time series graphs by neighborhood and crime type, view historical time trends, and compare overall crime levels in different neighborhoods using comparative graphs. The Dashboard will allow him to pick safer places to stay, know when it is safe to be outside and when it is not, and what kind of crime to be aware and vigiliant of, so that he can pick an area that best suits his needs.

### Section 4: Sketch

A sketch of the proposed dashboard is included in the README.md file.