# This is trademaster_fmz_strategy43.py
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy

data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_15m/btc_15min_data_2023.csv'

# Load data function
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
        data['datetime'] = pd.to_datetime(data['datetime'])
        data.set_index('datetime', inplace=True)
        return data
    except Exception as e:
        print(f"Error in load_data: {e}")
        raise

# Strategy class
class RenkoReversalStrategy(Strategy):
    def init(self):
        pass

    def next(self):
        close = self.data.Close
        open_ = self.data.Open

        # Define conditions for Renko-style reversal signals
        long_condition = close[-1] > open_[-2] and close[-2] < open_[-3]
        short_condition = close[-1] < open_[-2] and close[-2] > open_[-3]

        # Entry conditions
        if long_condition and not self.position.is_long:
            self.buy()
            print(f"Entering Long at {close[-1]} on {self.data.index[-1]}")

        elif short_condition and not self.position.is_short:
            self.sell()
            print(f"Entering Short at {close[-1]} on {self.data.index[-1]}")

# Main code
data = load_data(data_path)
bt = Backtest(data, RenkoReversalStrategy, cash=1000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
