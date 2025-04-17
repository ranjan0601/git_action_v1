import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yfinance as yf
from matplotlib.patches import Circle


df = yf.download('AAPL', period='6mo', progress=False)
# print(df)

def calculate_trendwave_bands(df, length=50, factor=1.0):
    """
    Calculate TrendWave Bands based on the PineScript logic

    Parameters:
    df: DataFrame with OHLC data
    length: lookback period (default 50)
    factor: volatility multiplier (default 1.0)

    Returns:
    DataFrame with original data and indicator values
    """
# Create a copy of the dataframe to avoid modifying the original
    result = df.copy()

    # Calculate HLC3 (typical price)
    result['hlc3'] = (result['High'] + result['Low'] + result['Close']) / 3

     
    # Calculate volatility
    result['volatility'] = result['High'].rolling(70).mean() - result['Low'].rolling(70).mean()
    result['volatility'] = result['volatility'] * 1.0  #factor
    print(result.tail())  
    # Calculate SMA values
    result['sma_25'] = result['Close'].rolling(25).mean()
    result['sma_length'] = result['Close'].rolling(length).mean()

    # Calculate upper and lower bands
    result['upper_raw'] = result['sma_25'] + result['volatility']
    result['lower_raw'] = result['sma_length'] - result['volatility']

    # Calculate highest of upper_raw and lowest of lower_raw
    half_length = int(50 / 2)
    result['upper'] = result['upper_raw'].rolling(half_length).max()
    result['lower'] = result['lower_raw'].rolling(half_length).min()
    print(result.tail()) 

    # Calculate ATR for additional bands
    result['tr'] = np.maximum(
        result['High'] - result['Low'],
        np.maximum(
            np.abs(result['High'] - result['Close'].shift(1)),
            np.abs(result['Low'] - result['Close'].shift(1))
        )
    )
    result['atr_100'] = result['tr'].rolling(100).mean()

    # Initialize trend direction and count
    result['direction'] = 0
    result['count_up'] = 0.0
    result['count_dn'] = 0.0



    # Create result dataframe in decending order at date index
    result = result.sort_index(ascending=True)

    print(result.head())

    # result.to_csv('result.csv')

    prev_direction = result.loc[result.index[0], 'direction']

    print(prev_direction)



    # Calculate signals and trend direction
    for i in range(1, len(result)):
        # Previous direction
        prev_direction = result.loc[result.index[i-1], 'direction']
        
        # Check for crossovers (signals)
        sig_up = ((result.loc[result.index[i-1], 'hlc3'] <= result.loc[result.index[i-1], 'upper']) & (result.loc[result.index[i], 'hlc3'] > result.loc[result.index[i], 'upper']))

        sig_dn = ((result.loc[result.index[i-1], 'hlc3'] >= result.loc[result.index[i-1], 'lower']) & (result.loc[result.index[i], 'hlc3'] < result.loc[result.index[i], 'lower']))
                    
        # print(f'printing the direction {sig_up}')
        # print(f'printing the direction {sig_dn}')
        # Update direction
        if sig_up:
            result.loc[result.index[i], 'direction'] = 1
        elif sig_dn:
            result.loc[result.index[i], 'direction'] = -1
        else:
            result.loc[result.index[i], 'direction'] = prev_direction
            
        # Update counts
        if result.loc[result.index[i], 'direction'] == 1:
            result.loc[result.index[i], 'count_up'] = result.loc[result.index[i-1], 'count_up'] + 0.5
            result.loc[result.index[i], 'count_dn'] = 0
        elif result.loc[result.index[i], 'direction'] == -1:
            result.loc[result.index[i], 'count_dn'] = result.loc[result.index[i-1], 'count_dn'] + 0.5
            result.loc[result.index[i], 'count_up'] = 0
        else:
            result.loc[result.index[i], 'count_up'] = result.loc[result.index[i-1], 'count_up']
            result.loc[result.index[i], 'count_dn'] = result.loc[result.index[i-1], 'count_dn']
        
        # Cap counts at 70
        result.loc[result.index[i], 'count_up'] = min(70, result.loc[result.index[i], 'count_up'])
        result.loc[result.index[i], 'count_dn'] = min(70, result.loc[result.index[i], 'count_dn'])

    # Hide upper band when in uptrend and lower band when in downtrend
    for i in range(len(result)):
        if result.loc[result.index[i], 'direction'] == 1:
            result.loc[result.index[i], 'upper_plot'] = np.nan
            result.loc[result.index[i], 'lower_plot'] = result.loc[result.index[i], 'lower']
        elif result.loc[result.index[i], 'direction'] == -1:
            result.loc[result.index[i], 'upper_plot'] = result.loc[result.index[i], 'upper']
            result.loc[result.index[i], 'lower_plot'] = np.nan
        else:
            result.loc[result.index[i], 'upper_plot'] = result.loc[result.index[i], 'upper']
            result.loc[result.index[i], 'lower_plot'] = result.loc[result.index[i], 'lower']

    # Calculate additional wave bands
    result['upper_band'] = result['lower'] + result['atr_100'] * 5
    result['lower_band'] = result['upper'] - result['atr_100'] * 5

    # Generate buy/sell signals
    result['signal'] = 0
    for i in range(1, len(result)):
        # Buy signal: When direction changes from not-up to up
        if result.loc[result.index[i], 'direction'] == 1 and result.loc[result.index[i-1], 'direction'] != 1:
            result.loc[result.index[i], 'signal'] = 1  # Buy
            
        # Sell signal: When direction changes from not-down to down
        elif result.loc[result.index[i], 'direction'] == -1 and result.loc[result.index[i-1], 'direction'] != -1:
            result.loc[result.index[i], 'signal'] = -1  # Sell
        
    return result
