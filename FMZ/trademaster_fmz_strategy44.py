# This is trademaster_fmz_strategy44.py
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

# Function to calculate Demark Reversal Points
def calculate_demark_reversal(data, length=9, lb_length=4):
    up_count = np.zeros(len(data))
    down_count = np.zeros(len(data))

    for i in range(length, len(data)):
        up_count[i] = sum(data['Close'].iloc[i - j] > data['Close'].iloc[i - j - lb_length] for j in range(length))
        down_count[i] = sum(data['Close'].iloc[i - j] < data['Close'].iloc[i - j - lb_length] for j in range(length))

    drp = np.where(down_count == length, 1, np.where(up_count == length, -1, 0))
    return drp

# Strategy class
class DemarkReversalStrategy(Strategy):
    def init(self):
        self.drp = self.I(calculate_demark_reversal, self.data, 9, 4)

    def next(self):
        # Buy signal on bullish crossover
        if self.drp[-2] <= 0 and self.drp[-1] > 0 and not self.position.is_long:
            self.buy()
            print(f"Entering Long at {self.data.Close[-1]} on {self.data.index[-1]}")

        # Sell signal on bearish crossover
        elif self.drp[-2] >= 0 and self.drp[-1] < 0 and not self.position.is_short:
            self.sell()
            print(f"Entering Short at {self.data.Close[-1]} on {self.data.index[-1]}")

# Main code
data = load_data(data_path)
bt = Backtest(data, DemarkReversalStrategy, cash=1000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
