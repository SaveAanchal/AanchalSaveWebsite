# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 28 16:01:33 2024

@author: slorphelin
"""

"""
File to clean csv files
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pvlib

starttime = pd.Timestamp.now()
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = PROJECT_ROOT / "Data"
CLEANED_ROOT = PROJECT_ROOT / "code" / "DL_models" / "cleaned_files" / "cleaned_files_NaN_deg_irr"

#Will be used in reshape_df(df)
#It is unifying Fixed and Deger files to have the same name references
def rename_temperature_columns(df):
    column_mapping = {
        'TempF_Mono': 'Temp_Mono',
        'TempF_Poly': 'Temp_Poly',
        'TempF_Amor': 'Temp_Amor',
        'TempF_Cigs': 'Temp_Cigs'
    }
    df = df.rename(columns=column_mapping)
    return df
 
def reshape_df(df):
    # Convert DayID to datetime format with DD/MM/YYYY
    df['DayID'] = pd.to_datetime(df['DayID'], errors='coerce')
    df['DayID'] = df['DayID'].dt.strftime('%d/%m/%Y')

    # Combine "DayID" and "TimeID" columns into a single datetime column "date"
    df['TimeID'] = pd.to_datetime(df['TimeID'], format='%H:%M:%S').dt.time
    df['date'] = df['DayID'].astype(str) + ' ' + df['TimeID'].astype(str)

    # Convert "date" column to datetime format
    df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y %H:%M:%S')

    # Drop the original "DayID" and "TimeID" columns if needed
    df.drop(columns=['DayID', 'TimeID'], inplace=True)

    # Rename 'Temprature' column to 'Temperature' if it exists due to a typo in the data
    if 'Temprature' in df.columns:
        df.rename(columns={'Temprature': 'Temperature'}, inplace=True)

    df = rename_temperature_columns(df)
    
    return df

def remove_nighttime_values(df):
    lat = 49.109 #CanBeChanged
    lon = 6.183 #CanBeChanged
    alt = 209 #CanBeChanged
    # Calculate solar position
    solpos = pvlib.solarposition.get_solarposition(time=df['date'], latitude=lat, longitude=lon, altitude=alt, method='pyephem')
    # Extract zenith angle in degrees
    zenith_angle = solpos['apparent_zenith']
    zenith_angle = zenith_angle.reset_index(drop=True) # getting rid of "date" column attached as an index to zenith_angle
    # Replace nighttime values with NaN
    df.loc[zenith_angle > 83, 'date'] = np.nan
    # Drop rows with NaN values in the 'date' column
    df.dropna(subset=['date'], inplace=True)
    return df

def remove_bad_temps(df):
    #If temperatures are greater than 60, we replace the values by NaN to mark them as outliers/missing values
    if 'Temperature' in df.columns:
        df['Temperature'] = np.where((df['Temperature'] > 60), np.nan, df['Temperature'])
    if 'TempF_Mono' in df.columns:
        df['TempF_Mono'] = np.where((df['TempF_Mono'] > 60), np.nan, df['TempF_Mono'])
    if 'TempF_Poly' in df.columns:
        df['TempF_Poly'] = np.where((df['TempF_Poly'] > 60), np.nan, df['TempF_Poly'])
    if 'TempF_Amor' in df.columns:
        df['TempF_Amor'] = np.where((df['TempF_Amor'] > 60), np.nan, df['TempF_Amor'])
    if 'TempF_Cigs' in df.columns:
        df['TempF_Cigs'] = np.where((df['TempF_Cigs'] > 60), np.nan, df['TempF_Cigs'])
    return df

#Function that will help us find the number of rows that we need to insert between 2 dates
def build_gap_intervals(total_seconds):
    if total_seconds < 20:
        print("Error. Number has to be superior to 19 to be considered as a missing row.")
        return []

    # Build the minimum number of 10-15 second chunks whose sum equals the gap.
    interval_count = int(np.ceil(total_seconds / 15))
    intervals = [10] * interval_count
    remainder = total_seconds - (10 * interval_count)

    idx = 0
    while remainder > 0:
        increment = min(5, remainder)
        intervals[idx] += increment
        remainder -= increment
        idx = (idx + 1) % interval_count

    # The last chunk ends at the next observed timestamp, so only earlier chunks create new rows.
    return intervals[:-1]

#We go through the dataframe and insert new blank rows with reference date
#The goal is to add the missing rows with NaN values to mark them as missing values
#A new file is made from the following function
def insert_rows(df): 
    #df = pd.read_csv(file_in)
    lat = 49.109
    lon = 6.183
    alt = 209
    rows_to_insert = []
    prev_date = pd.to_datetime(df['date'].iloc[0])  # Variable to store the previous date
    #print('File treated : ', df['date'].head(1))
    for index, row in df.iloc[0:].iterrows(): 
        timedate = pd.to_datetime(row['date'])
        # Calculate solar position
        solpos = pvlib.solarposition.get_solarposition(time=timedate, latitude=lat, longitude=lon, altitude=alt, method='pyephem')
        # Extract zenith angle in degrees
        zenith_angle = solpos['apparent_zenith']
        # NB : zenith_angle <= 90 means that it is day time
        # We do not want night values to be recomposed again, with zeros, because they are not considered as missing values
        zenith_angle = int(zenith_angle.iloc[0])
        #If it is day time
        if (zenith_angle <= 83):
            is_new_day = False if pd.to_datetime(row['date']).day == pd.to_datetime(prev_date).day else True
            # IF it is a new day, we set the previous date to the first date of the new day
            if (is_new_day == False):
                time_diff = (pd.to_datetime(row['date']) - pd.to_datetime(prev_date)).total_seconds() 
                time_diff = int(time_diff)
                
                if time_diff > 19:  # If the time gap between two rows is greater than 19 seconds
                    seconds_to_add = build_gap_intervals(time_diff)
                    new_date = prev_date  # Initialize with previous date
                    
                    for i in range(len(seconds_to_add)):  # We add the coefficients (13 and/or 14 and/or 15)
                        new_date += pd.Timedelta(seconds=seconds_to_add[i])
                        #Create a dictionary to hold the values for the new row
                        #new row contains only NaN values
                        new_row_data = {column: np.nan for column in df.columns if column != 'date'} #No more : new_row_data = {column: 0 for column in df.columns if column != 'date'}
                        new_row_data['date'] = new_date                 
                        # Explicitly set NaN values for each column
                        # Create a new pandas Series using the dictionary
                        new_row = pd.Series(index=df.columns, dtype=object)
                        
                        # Explicitly set NaN values for each column
                        for col, value in new_row_data.items():
                            if pd.api.types.is_numeric_dtype(df[col]):
                                new_row[col] = float(value)
                            else:
                                new_row[col] = value
                        # Append the index and the new row to the rows_to_insert list
                        rows_to_insert.append((index + i, new_row)) # NB : inserting a new row pushes the existing elements at that index and higher indices down by one position (i to i+1 for example)
            
        prev_date = pd.to_datetime(row['date'])  # Update previous date for the next iteration

    # Insert new rows into the DataFrame
    for idx, new_row in rows_to_insert :
    # Explicitly set NaN values for each column
        for col, value in new_row_data.items():
            new_row[col] = float(value) if pd.api.types.is_numeric_dtype(df[col]) else value
        # Insert new rows into the DataFrame
        df.loc[idx] = new_row
        
    #df.to_csv(file_out, index=False)
    return df

#We mark the inf, -inf and null values as outliers by replacing them by NaN values
def toNaN(df):
    # Replace infinite values with NaN
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    # Replace null values with NaN
    df.replace([None], np.nan, inplace=True)
    df.replace([pd.NaT], np.nan, inplace=True)
    return df

def reshape_all(file_path):
    # Read the file
    print(f'Cleaning file : {file_path}')
    df = pd.read_csv(file_path) 
    #Reshape data
    print("Shaping")
    df = reshape_df(df)
    # Remove nighttime values
    print("Night Values")
    df = remove_nighttime_values(df)
    # Remove misread temperatures
    print("Bad Temp")
    df = remove_bad_temps(df)
    # Replace 'inf' or 'Inf' or null with NaN
    print("Inserting Rows")
    df = insert_rows(df)
    print("To NaN")
    df = toNaN(df)
    df.reset_index(drop=True, inplace=True)     
    return df

# Dictionary mapping month names to abbreviations 
#CanBeChanged (month_abbr)
#We can add or remove months as long as the abbreviations are correctly formatted

month_abbr = {
    'January': 'jan', 
    'February': 'feb', 
    'March': 'mar',
    'April': 'apr',
    'May': 'may', 
    'June': 'jun',
    'July': 'jul',
    'August': 'aug', 
    'September': 'sep',
    'October': 'oct',
    'November': 'nov',
    'December': 'dec'
}

def get_month_abbr(month):
    # Get the abbreviation for the month
    abbr = month_abbr.get(month)
    if not abbr:
        # If the abbreviation doesn't exist, use the first three letters
        abbr = month[:3].lower()
    return abbr


def iter_existing_months(year, data_type):
    base_path = DATA_ROOT / str(year) / data_type
    if not base_path.exists():
        return []
    return [
        abbr
        for abbr in month_abbr.values()
        if (base_path / f"{abbr}.csv").exists()
    ]


def iter_missing_output_months(year, data_type):
    output_path = CLEANED_ROOT / str(year) / data_type
    return [
        abbr
        for abbr in month_abbr.values()
        if not (output_path / f"{abbr}.csv").exists()
    ]

#Launch the entire code
def main():
    for year in range(2025, 2025 + 1): ##CanBeChanged -replace the former dates by the dates you want to include - DO NOT Change the "+1"
        file_path_irr = DATA_ROOT / str(year) / "irradiance"
        file_path_deg = DATA_ROOT / str(year) / "deger"

        output_path_irr = CLEANED_ROOT / str(year) / "irradiance"
        output_path_deg = CLEANED_ROOT / str(year) / "deger"
        output_path_irr.mkdir(parents=True, exist_ok=True)
        output_path_deg.mkdir(parents=True, exist_ok=True)

        months_to_process = sorted(
            (
                set(iter_existing_months(year, "irradiance"))
                & set(iter_existing_months(year, "deger"))
                & (
                    set(iter_missing_output_months(year, "irradiance"))
                    | set(iter_missing_output_months(year, "deger"))
                )
            ),
            key=list(month_abbr.values()).index,
        )

        for abbr in months_to_process:
            prov_irr = file_path_irr / f"{abbr}.csv"
            code_irr = reshape_all(prov_irr)
            print('Prov file : ', prov_irr)
            to_irr = output_path_irr / f"{abbr}.csv"
            print('To file : ', to_irr)
            code_irr.to_csv(to_irr, index=True)

            prov_deg = file_path_deg / f"{abbr}.csv"
            code_deg = reshape_all(prov_deg)
            print('Prov file dg: ', prov_deg)
            to_deg = output_path_deg / f"{abbr}.csv"
            print('To dg file : ', to_deg)
            code_deg.to_csv(to_deg, index=True)

    return

main()
# df = pd.read_csv("/home/bertrand/Documents/Simulation/Python/PV_GTE/my_code/DL_models/cleaned_files/cleaned_files_NaN_deg_irr/2024/irradiance/sep.csv")
endtime = pd.Timestamp.now()
runtime = endtime - starttime
print("Run Time:", runtime.total_seconds())