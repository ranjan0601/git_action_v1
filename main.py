import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from strategy2 import * # Assuming stragegy2.py contains the TrendWave Bands calculation logic
import logging

import time
time.sleep(10)  # Waits 10 seconds to ensure internet is up

def filter_stocks_by_signals(stock_data_dict, length=50, factor=1.0):
    """
    Filter stocks by TrendWave Bands buy/sell signals
    
    Parameters:
    stock_data_dict: Dictionary with stock symbols as keys and OHLC DataFrames as values
    length: lookback period for TrendWave Bands (default 50)
    factor: volatility multiplier for TrendWave Bands (default 1.0)
    
    Returns:
    Dictionary containing lists of stocks with buy signals, sell signals, and their current trend data
    """
    buy_signals = []
    sell_signals = []
    neutral = []
    
    # Store detailed trend information for each stock
    trend_data = {}
    
    for symbol, ohlc_data in stock_data_dict.items():
        try:
            # Calculate TrendWave Bands for this stock
            result = calculate_trendwave_bands(ohlc_data, length, factor)
            
            # Get the most recent data point
            latest_data = result.iloc[-1]
            print(f"latest data {latest_data}")
            prev_data = result.iloc[-2] if len(result) > 1 else None
            
            # Store trend data
            trend_data[symbol] = {
                'price': latest_data['Close'],
                'direction': latest_data['direction'],
                'count_up': latest_data['count_up'],
                'count_dn': latest_data['count_dn'],
                'upper': latest_data['upper'] if not np.isnan(latest_data['upper_plot']) else None,
                'lower': latest_data['lower'] if not np.isnan(latest_data['lower_plot']) else None,
                'days_in_trend': latest_data['count_up'] if latest_data['direction'] == 1 else latest_data['count_dn'],
                'signal': latest_data['signal']
            }
            
            print(type(latest_data['upper_plot']), latest_data['upper_plot'])
            print(type(latest_data['lower_plot']), latest_data['lower_plot'])
            
            # Check for buy signal (direction just changed to 1)
            if latest_data['signal'] == 1:
                buy_signals.append(symbol)
            
            # Check for sell signal (direction just changed to -1)
            elif latest_data['signal'] == -1:
                sell_signals.append(symbol)
            
            # No recent signal
            else:
                # Categorize based on current direction
                if latest_data['direction'] == 1:
                    trend_data[symbol]['trend'] = 'uptrend'
                elif latest_data['direction'] == -1:
                    trend_data[symbol]['trend'] = 'downtrend'
                else:
                    trend_data[symbol]['trend'] = 'neutral'
                    
                neutral.append(symbol)
                
        except Exception as e:
            print(f"Error processing {symbol}: {str(e)}")
    
    return {
        'buy_signals': buy_signals,
        'sell_signals': sell_signals,
        'neutral': neutral,
        'trend_data': trend_data
    }

def download_stock_data(symbols, period="1y"):
    """
    Download historical data for a list of stock symbols
    
    Parameters:
    symbols: List of stock symbols
    period: Time period to download (default "1y" = 1 year)
    
    Returns:
    Dictionary with stock symbols as keys and OHLC DataFrames as values
    """
    stock_data = {}
    
    for symbol in symbols:
        try:
            data = yf.download(symbol, period=period, progress=False)
            if data.empty:
                logging.error(f"No data available for {symbol}")
            else:
                result = data.reset_index(drop=False)
                result.columns = range(result.shape[1])
                result.rename(columns={0: 'Date', 1: 'Close', 2: 'High', 3: 'Low', 4 : 'Open', 5: 'Volume'}, inplace=True)
                result.set_index('Date', inplace=True)
                logging.info(f"Downloaded data for {symbol}")
            if not data.empty:
                stock_data[symbol] = result
                time.sleep(10) # Waits 10 seconds to avoid hitting API limits
            else:
                print(f"No data available for {symbol}")
        except Exception as e:
            print(f"Error downloading {symbol}: {str(e)}")
            logging.exception(f"Failed download for {symbol}: {e}")
    
    return stock_data

def create_signal_summary(signals_dict, last_n_days=1):
    """
    Create a summary report of stocks with buy/sell signals
    
    Parameters:
    signals_dict: Output from filter_stocks_by_signals function
    last_n_days: Number of days to look back for signals (default 1 = today only)
    
    Returns:
    DataFrame with signal summary
    """
    trend_data = signals_dict['trend_data']
    
    # Create lists for DataFrame
    symbols = []
    prices = []
    trends = []
    days_in_trend = []
    signals = []
    
    # Combine buy and sell signals
    for symbol in signals_dict['buy_signals']:
        symbols.append(symbol)
        prices.append(trend_data[symbol]['price'])
        trends.append('uptrend (new)')
        days_in_trend.append(trend_data[symbol]['days_in_trend'])
        signals.append('BUY')
    
    for symbol in signals_dict['sell_signals']:
        symbols.append(symbol)
        prices.append(trend_data[symbol]['price'])
        trends.append('downtrend (new)')
        days_in_trend.append(trend_data[symbol]['days_in_trend'])
        signals.append('SELL')
    
    # Add neutral stocks with their current trend
    for symbol in signals_dict['neutral']:
        data = trend_data[symbol]
        if 'trend' in data:
            symbols.append(symbol)
            prices.append(data['price'])
            trends.append(data['trend'])
            days_in_trend.append(data['days_in_trend'])
            signals.append('HOLD')
    
    # Create DataFrame
    df_summary = pd.DataFrame({
        'Symbol': symbols,
        'Price': prices,
        'Trend': trends,
        'Days in Trend': days_in_trend,
        'Signal': signals
    })
    
    # Sort by signal importance: Buy, Sell, then Hold
    signal_order = {'BUY': 0, 'SELL': 1, 'HOLD': 2}
    df_summary['Signal_Order'] = df_summary['Signal'].map(signal_order)
    df_summary = df_summary.sort_values(['Signal_Order', 'Symbol']).drop('Signal_Order', axis=1)
    
    return df_summary

def plot_signal_distribution(signals_dict):
    """
    Create a pie chart showing distribution of signals
    
    Parameters:
    signals_dict: Output from filter_stocks_by_signals function
    """
    # Count stocks in each category
    buy_count = len(signals_dict['buy_signals'])
    sell_count = len(signals_dict['sell_signals'])
    
    # Count uptrend and downtrend among neutral stocks
    uptrend_count = 0
    downtrend_count = 0
    neutral_count = 0
    
    for symbol in signals_dict['neutral']:
        if signals_dict['trend_data'][symbol]['direction'] == 1:
            uptrend_count += 1
        elif signals_dict['trend_data'][symbol]['direction'] == -1:
            downtrend_count += 1
        else:
            neutral_count += 1
    
    # Create pie chart
    labels = ['Buy Signal', 'Sell Signal', 'In Uptrend', 'In Downtrend', 'Neutral']
    sizes = [buy_count, sell_count, uptrend_count, downtrend_count, neutral_count]
    colors = ['green', 'red', 'lightgreen', 'lightcoral', 'lightgray']
    
    # Remove categories with zero count
    filtered_labels = []
    filtered_sizes = []
    filtered_colors = []
    
    for i in range(len(sizes)):
        if sizes[i] > 0:
            filtered_labels.append(labels[i])
            filtered_sizes.append(sizes[i])
            filtered_colors.append(colors[i])
    
    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))
    wedges, texts, autotexts = ax.pie(filtered_sizes, labels=filtered_labels, colors=filtered_colors,
                                     autopct='%1.1f%%', startangle=90, shadow=True)
    
    # Equal aspect ratio ensures that pie is drawn as a circle
    ax.axis('equal')
    plt.title('Stock Signal Distribution')
    
    # Make text properties better
    for text in texts:
        text.set_fontsize(12)
    for autotext in autotexts:
        autotext.set_fontsize(12)
        autotext.set_fontweight('bold')
    
    plt.tight_layout()
    plt.show()
    
    return fig, ax

# # Example usage
# if __name__ == "__main__":
    # Example list of stocks (e.g., S&P 500 components)

logging.basicConfig(filename='log.txt', level=logging.DEBUG)
logging.info('Starting the script')
symbols = [
    "RELIANCE.NS",  # Reliance Industries
    "TCS.NS",       # Tata Consultancy Services
    # "INFY.NS",      # Infosys
    # "HDFCBANK.NS",  # HDFC Bank
    # "ICICIBANK.NS", # ICICI Bank
    # "HINDUNILVR.NS",# Hindustan Unilever
    # "SBIN.NS",      # State Bank of India
    # "BHARTIARTL.NS",# Bharti Airtel
    # "ITC.NS",       # ITC Limited
    # "KOTAKBANK.NS", # Kotak Mahindra Bank
    # "LT.NS",        # Larsen & Toubro
    # "AXISBANK.NS",  # Axis Bank
    # "HCLTECH.NS",   # HCL Technologies
    # "ASIANPAINT.NS",# Asian Paints
    # "MARUTI.NS",    # Maruti Suzuki
    # "SUNPHARMA.NS", # Sun Pharmaceutical
    # "TITAN.NS",     # Titan Company
    # "ULTRACEMCO.NS",# UltraTech Cement
    # "WIPRO.NS",     # Wipro
    # "ADANIENT.NS"   # Adani Enterprises
]

print(f"Downloading data for {len(symbols)} stocks...")
stock_data = download_stock_data(symbols, period="6mo")

# print(stock_data['JNJ'].head())

# Calculate TrendWave Bands and filter signals
signals = filter_stocks_by_signals(stock_data, length=50, factor=1.0)

# Print results
print("\n=== SIGNAL SUMMARY ===")
print(f"BUY Signals: {len(signals['buy_signals'])}")
for symbol in signals['buy_signals']:
    print(f"  - {symbol}: ${signals['trend_data'][symbol]['price']:.2f}")

print(f"\nSELL Signals: {len(signals['sell_signals'])}")
for symbol in signals['sell_signals']:
    print(f"  - {symbol}: ${signals['trend_data'][symbol]['price']:.2f}")

print(f"\nNeutral (No Recent Signal): {len(signals['neutral'])}")

# Create and display summary table
summary_df = create_signal_summary(signals)
print("\n=== DETAILED SUMMARY ===")
print(summary_df)

# Plot signal distribution
plot_signal_distribution(signals)


import requests

def send_to_telegram(summary_df, bot_token, chat_id):
    """
    Send the summary DataFrame to Telegram as a message.

    Parameters:
    summary_df: DataFrame to send
    bot_token: Telegram bot token
    chat_id: Telegram chat ID
    """
    # Convert DataFrame to string
    message = summary_df.to_string(index=False)

    # Telegram API URL
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Payload for the API request
    payload = {
        "chat_id": chat_id,
        "text": message
    }

    # Send the message
    response = requests.post(url, data=payload)

    # Check response
    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print(f"Failed to send message. Error: {response.text}")

# Example usage
bot_token = "7998210391:AAFL3DVEKRmx71PkjdEhxGAFSzb3pEiVJS8"  # Replace with your bot's API token
chat_id = "5769301731"      # Replace with your chat ID

# Send the summary DataFrame
send_to_telegram(summary_df, bot_token, chat_id)
