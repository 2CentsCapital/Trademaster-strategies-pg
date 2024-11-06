import pandas as pd
import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
import pandas_ta as ta
from TradeMaster.lib import crossover

data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023.csv'

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

def calculate_coral_trends(data, smoothing_period1=3, constant_d1=0.2, smoothing_period2=6, constant_d2=0.2):
    try:
        # Calculate Coral Trend 1
        ema_value1 = ta.ema(data['Close'], length=smoothing_period1)
        smooth_ema1 = ta.ema(ema_value1, length=smoothing_period1)
        data['CoralTrend1'] = smooth_ema1 + constant_d1 * (ema_value1 - smooth_ema1)

        # Calculate Coral Trend 2
        ema_value2 = ta.ema(data['Close'], length=smoothing_period2)
        smooth_ema2 = ta.ema(ema_value2, length=smoothing_period2)
        data['CoralTrend2'] = smooth_ema2 + constant_d2 * (ema_value2 - smooth_ema2)

        return data
    except Exception as e:
        print(f"Error in calculate_coral_trends: {e}")
        raise

class DStrykerLTStrategy(Strategy):
    def init(self):
        self.coral_trend1 = self.data.CoralTrend1
        self.coral_trend2 = self.data.CoralTrend2

    def next(self):
        # Check for crossover between Coral Trend 1 and Coral Trend 2
        if crossover(self.coral_trend1, self.coral_trend2):
            if self.position.is_short:
                self.position.close()
            self.buy()  # Enter long position on crossover

data = load_data(data_path)
data = calculate_coral_trends(data)
bt = Backtest(data, DStrykerLTStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
