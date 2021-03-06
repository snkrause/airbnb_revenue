# -*- coding: utf-8 -*-
"""
Library for udacity blogpost project.

Created on Fri Jan 29 15:39:24 2021

@author: KRS1BBH
"""

import pandas as pd
import os, glob
from datetime import datetime
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt


def coef_weights(coefficients, X_train):
    '''
    INPUT:
    coefficients - the coefficients of the linear model 
    X_train - the training data, so the column names can be used
    OUTPUT:
    coefs_df - a dataframe holding the coefficient, estimate, and abs(estimate)
    
    Provides a dataframe that can be used to understand the most influential coefficients
    in a linear model by providing the coefficient estimates along with the name of the 
    variable attached to the coefficient.
    '''
    coefs_df = pd.DataFrame()
    coefs_df['est_int'] = X_train.columns
    coefs_df['coefs'] = coefficients
    coefs_df['abs_coefs'] = np.abs(coefficients)
    coefs_df = coefs_df.sort_values('abs_coefs', ascending=False)
    return coefs_df


def load_data(path_abnb):
    """
    

    Parameters
    ----------
    path_abnb : string
        path to folder with airbnb data organized by city folders each containing the three files "reviews.csv, calendar.csv, and listings.csv".

    Returns
    -------
    listings : dataframe
        Dataframe with appended file content of all city subfolders in path_abnb. Only mutual columns are kept.
    calendar : dataframe
        Dataframe with appended file content of all city subfolders in path_abnb..
    review : dataframe
        Dataframe with appended file content of all city subfolders in path_abnb..

    """
    
    cities = os.listdir(path_abnb)
    for n in range(len(cities)):
        if n==0:
            #read in listings and calendar files
            listings=pd.read_csv(path_abnb+cities[n]+"/listings.csv")
            listings['folder']=cities[n]
            calendar=pd.read_csv(path_abnb+cities[n]+"/calendar.csv")
            calendar['folder']=cities[n]
            review=pd.read_csv(path_abnb+cities[n]+"/reviews.csv")
            review['folder']=cities[n]
        else:
            df=pd.read_csv(path_abnb+cities[n]+"/listings.csv")
            df['folder']=cities[n]
            common_cols=set(listings.columns) & set(df.columns)
            listings=listings[common_cols].append(df[common_cols], ignore_index=True)
            calendar=calendar.append(pd.read_csv(path_abnb+cities[n]+"/calendar.csv"), ignore_index=True)
            calendar['folder'].fillna(cities[n], inplace=True)
            review=review.append(pd.read_csv(path_abnb+cities[n]+"/reviews.csv"), ignore_index=True)
            review['folder'].fillna(cities[n], inplace=True)
            
    return listings, calendar, review

def analyze_calendar(calendar):
    """
    

    Parameters
    ----------
    calendar : dataframe
        dataframe generated by load_data.

    Returns
    -------
    calendar_revenue : TYPE
        pivoted calendar_stats with 
    calendar_stats : TYPE
        DESCRIPTION.

    """
    #analyzing calendar 
    
    #extract month from date for later evaluation and transform price to numerical
    calendar['date']=pd.to_datetime(calendar['date'])
    calendar['month'] = pd.DatetimeIndex(calendar['date']).month
    calendar['price_num']=calendar['price'].replace('[\$,]', '', regex=True).astype(float) 
    
    #calculate earnings by month and pivot dataframe with months as new columns. Add sum for the year and calculate average monthly revenue by divison with booked months
    calendar_stats=calendar[calendar['available']=='t'].groupby(by=['listing_id','month','folder'], as_index=False)['price_num'].sum().rename(columns={'price_num':'revenue'})
    calendar_revenue=calendar_stats.pivot(index=['listing_id','folder'], columns='month',values='revenue')
    calendar_revenue['booked_months']=calendar_revenue[range(1,13)].count(axis=1)
    calendar_revenue.fillna(0, inplace=True)
    calendar_revenue['revenue_year']=calendar_revenue[range(1,13)].sum(axis=1)
    calendar_revenue['revenue_month_mean']=calendar_revenue['revenue_year']/calendar_revenue['booked_months']
    
    return calendar_revenue, calendar_stats

def preprocess_listings(listing, calendar_revenue):
    """
    

    Parameters
    ----------
    listing : TYPE
        DESCRIPTION.
    calendar_revenue : TYPE
        DESCRIPTION.

    Returns
    -------
    df_vis : TYPE
        DESCRIPTION.
    df : TYPE
        DESCRIPTION.

    """
    #prepare listing for ML and add revenue for visualization
    
    #add revenue to listings
    df_vis=listing.merge(calendar_revenue, left_on='id', right_on='listing_id')
    
    #select non-numeric columns
    non_num=listing.select_dtypes(include=['object']).columns.to_list()
    
    #drop columns with irrelevant or duplicate information (e.g., urls, scrape info, etc.)
    non_num_drop=[ x for x in listing.columns if 'url' in x or 'scrape' in x or 'itude' in x or '_id' in x or 'listing' in x or 'availablity' in x or 'instant' in x or 'host' in x or 'since' in x or 'first' in x or 'last' in x or 'license' in x or 'verification' in x or 'avail' in x]
    non_num_drop.remove('availability_365')   
    listing=listing.drop(columns=non_num_drop)
    
    #manual choice of columns to drop
    col_drop=g=['room_type', 'neighbourhood'] 
    listing=listing.drop(columns=col_drop)
    
    #select columns to remove dollar sign
    non_num_to_num=[ x for x in non_num if 'price'in x or'fee' in x or'deposit' in x or'extra' in x in x]
    listing[non_num_to_num]=listing[non_num_to_num].replace({'\$': '', ',': '', '%':''}, regex=True).astype('float32')
    
    #find columns with >30% nan values
    listing_missing = list(listing.columns[listing.isnull().mean() > 0.30])
    listing=listing.drop(columns=listing_missing)
    
    #select columns with descriptions to convert to count # of characters
    non_num=listing.select_dtypes(include=['object']).columns
    non_num_to_count=[ x for x in non_num if 'name'in x or'description' in x or'about' in x or'overview' in x or'summary' in x or'space' in x or'notes' in x or'notes' in x or'amenities' in x]
    for col in non_num_to_count:
        listing[col+'_count']=listing[col].apply(lambda x: len(str(x)))
        listing.drop(col, axis=1, inplace=True)
               
    #turn categoricals into machine processable
    cat_cols=list(listing.select_dtypes(include=['object']).columns)
    listing_transformed=listing
    for col in  cat_cols:
        # for each cat add dummy var, drop original column
        listing_transformed = pd.concat([listing_transformed.drop(col, axis=1), pd.get_dummies(listing_transformed[col], prefix=col, prefix_sep='_', drop_first=False, dummy_na=False)], axis=1)
    
    #connect to revenue results
    df=listing_transformed.merge(calendar_revenue, left_on='id', right_on='listing_id').drop(columns=['id'])
    
    #drop revenue per year >150000 
    df=df[df['revenue_year']<150000]
    
    #drop listings that accommodate more than 8 people
    df=df[df['accommodates']<8.5] 
    
    #drop neighbourhoods_cleansed with less than 10 listings
    neighbourhoods=df_vis['neighbourhood_cleansed'].value_counts().reset_index()
    drop_neighbourhoods=neighbourhoods[neighbourhoods['neighbourhood_cleansed']<10]['index'].to_list()
    df=df.drop(columns=["neighbourhood_cleansed_"+s for s in drop_neighbourhoods])

    #drop property_types with less than 10 listings
    property_type=df_vis['property_type'].value_counts().reset_index()
    drop_property=property_type[property_type['property_type']<20]['index'].to_list()
    df=df.drop(columns=["property_type_"+s for s in drop_property])
    
    #drop all rows with nans
    df=df.dropna(axis=0, how='any')   
    
    return df_vis, df

def regression_model(df, target, drop):
    """
    

    Parameters
    ----------
    df : dataframe
        Cleaned input dataframe for linear regression model.

    Returns
    -------
    lm_model : linear regression model
        Linear regression model.
    X_train : dataframe
        Train dataset for coefficient ranking.

    """

    #split into response and data set. Drop revenue related columns and redundant information.  
    y=df[target]
    X=df.drop(columns=drop) 
    
    #Split into train and test
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = .30, random_state=42) 
    
    lm_model = LinearRegression(normalize=True) # Instantiate
    lm_model.fit(X_train, y_train) #Fit
            
    #Predict and score the model
    y_test_preds = lm_model.predict(X_test) 
    
    #Rsquared and y_test
    rsquared_score = r2_score(y_test, y_test_preds)
    length_y_test = len(y_test)

    print("The r-squared score for your model was {} on {} values.".format(rsquared_score, length_y_test))

    return lm_model, X_train