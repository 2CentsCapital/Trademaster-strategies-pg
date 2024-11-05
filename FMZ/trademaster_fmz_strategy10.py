import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
from backtesting.lib import crossover

data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023_2024.csv'

def load_data(csv_file_path):

        data = pd.read_csv(csv_file_path)
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data.set_index('timestamp', inplace=True)
        data.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        return data
  


def compute_vwap(high, low, close, volume):
    typical_price = (high + low + close) / 3
    cumulative_vp = (typical_price * volume).cumsum()
    cumulative_volume = volume.cumsum()
    vwap = cumulative_vp / cumulative_volume
    return vwap

# Strategy Class
class EMA9WMA30Strategy(Strategy):
    def init(self):

        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        volume = pd.Series(self.data.Volume)
        self.ema9 = self.I(ta.ema, close, 9)
        self.wma30 = self.I(ta.wma, close, 30)
        macd = self.I(ta.macd, close, fast=12, slow=26, signal=9)
        self.macd_line = macd[0]
        self.signal_line = macd[1]

        # Additional indicators
        self.sma200 = self.I(ta.sma, close, 200)
        self.ema21 = self.I(ta.ema, close, 21)
        
        self.vwap = self.I(compute_vwap, high, low, close, volume)


    def next(self):
        # Previous and current values for EMA9 and WMA30
        prev_ema9 = self.ema9[-2]
        prev_wma30 = self.wma30[-2]
        current_ema9 = self.ema9[-1]
        current_wma30 = self.wma30[-1]
        macd_line = self.macd_line[-1]
        signal_line = self.signal_line[-1]

        # Buy Signal Condition: EMA9 crosses above WMA30 with MACD confirmation
        buy_signal = (prev_ema9 < prev_wma30) and (current_ema9 > current_wma30) and (macd_line > signal_line)

        # Exit Condition 1: Close is below EMA9 for at least 2 days and below WMA30 for at least 1 day
        below_ema9_count = sum(self.data.Close[-i] < self.ema9[-i] for i in range(1, 3))  # 2 days below EMA9
        below_wma30_count = self.data.Close[-1] < self.wma30[-1]  # 1 day below WMA30

        # Exit Condition 2: MACD bearish crossover
        macd_bearish_cross = (self.macd_line[-2] > self.signal_line[-2]) and (macd_line < signal_line)

        # Exit Conditions
        exit_condition1 = below_ema9_count >= 2 and below_wma30_count
        exit_condition2 = macd_bearish_cross

        # Execute buy/sell based on signals
        if buy_signal:
            self.buy()
        elif exit_condition1 or exit_condition2:
            if self.position:
                self.position.close()



data = load_data(data_path)
bt = Backtest(data,EMA9WMA30Strategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)