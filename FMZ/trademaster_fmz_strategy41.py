import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy

data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_2h/btc_2h_data_2023.csv'

def load_data(csv_file_path):
    try:
        data = pd.read_csv(csv_file_path)
        data.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        return data
    except Exception as e:
        print(f"Error in load_data: {e}")
        raise

# Indicator function to calculate Bollinger Bands
def calculate_bollinger_bands(data, length=20, mult=2):
    basis = data['Close'].rolling(window=length).mean()
    dev = data['Close'].rolling(window=length).std()
    upper1 = basis + dev
    lower1 = basis - dev
    upper2 = basis + mult * dev
    lower2 = basis - mult * dev
    data['basis'] = basis
    data['upper1'] = upper1
    data['lower1'] = lower1
    data['upper2'] = upper2
    data['lower2'] = lower2
    return data

# Strategy class
class FiveMinScalpingStrategy(Strategy):
    def init(self):
        # Initialize references to Bollinger Bands
        self.basis = self.data['basis']
        self.upper1 = self.data['upper1']
        self.lower1 = self.data['lower1']
        self.upper2 = self.data['upper2']
        self.lower2 = self.data['lower2']

    def next(self):
        close = self.data.Close[-1]
               # Ensure there are at least two data points to avoid IndexError
        if len(self.data) < 2:
            return  # Skip this iteration if there's not enough data


        # Check entry conditions
        long_condition = self.data.Close[-2] < self.lower1[-2] and close > self.lower1[-1]
        short_condition = self.data.Close[-2] > self.upper1[-2] and close < self.upper1[-1]

        # Enter or exit long position
        if long_condition and not self.position().is_long:
            self.buy()
            print(f"Entering Long at {close} on {self.data.index[-1]}")

        elif short_condition and self.position().is_long:
            self.position().close()
            print(f"Closing Long at {close} on {self.data.index[-1]}")

        # Enter or exit short position
        if short_condition and not self.position().is_short:
            self.sell()
            print(f"Entering Short at {close} on {self.data.index[-1]}")

        elif long_condition and self.position().is_short:
            self.position().close()
            print(f"Closing Short at {close} on {self.data.index[-1]}")

# Main code
data = load_data(data_path)
data = calculate_bollinger_bands(data)  # Calculate indicators before running the strategy
bt = Backtest(data, FiveMinScalpingStrategy, cash=1000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
