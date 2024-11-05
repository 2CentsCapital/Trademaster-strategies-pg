import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import logging
import coloredlogs
import pandas_ta as ta
data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023_2024.csv'
def load_data(csv_file_path):
    try:
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
    except Exception as e:
        logging.error(f"Error in load_data: {e}")
        raise

# Keltner Channel Pullback Strategy Class
class KCPullbackStrategy(Strategy):
    def init(self, atr_length=35, atr_multiplier=5.5, kc_length=20, kc_multiplier=6.0, ema_length=280):
        # Calculate ATR
        close = pd.Series(self.data.Close)
        open = pd.Series(self.data.Open)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
        self.atr = self.I(ta.atr, high, low, close, length=atr_length)

        # Calculate Keltner Channel
        self.kc_basis = self.I(ta.sma, close, length=kc_length)
        self.kc_range = self.atr * kc_multiplier
        self.upper_kc = self.I(lambda b, r: b + r, self.kc_basis, self.kc_range)
        self.lower_kc = self.I(lambda b, r: b - r, self.kc_basis, self.kc_range)

        # Calculate EMA
        self.ema = self.I(ta.ema, close, length=ema_length)

        # Initialize ATR multiplier for stop loss
        self.atr_multiplier = atr_multiplier

    def next(self):
        # Check for Keltner Channel touches and EMA crossover
        middle_line_touched = (self.data.High[-1] >= self.kc_basis[-1]) and (self.data.Low[-1] <= self.kc_basis[-1])

        long_condition = (self.data.Close[-1] > self.ema[-1]) and middle_line_touched and any(self.data.High[-i] >= self.upper_kc[-i] for i in range(1, min(len(self.data), 120)))
        short_condition = (self.data.Close[-1] < self.ema[-1]) and middle_line_touched and any(self.data.Low[-i] <= self.lower_kc[-i] for i in range(1, min(len(self.data), 120)))

        # Entry Conditions
        if long_condition and not self.position.is_long:
            self.entry_price = self.data.Close[-1]
            self.prev_atr = self.atr[-2]
            long_stop_loss = self.entry_price - self.atr_multiplier * self.prev_atr
            self.buy(sl=long_stop_loss)

        elif short_condition and not self.position.is_short:
            self.entry_price = self.data.Close[-1]
            self.prev_atr = self.atr[-2]
            short_stop_loss = self.entry_price + self.atr_multiplier * self.prev_atr
            self.sell(sl=short_stop_loss)

        # Exit Conditions
        if self.position.is_long and self.data.High[-1] >= self.upper_kc[-1]:
            self.position.close()

        elif self.position.is_short and self.data.Low[-1] <= self.lower_kc[-1]:
            self.position.close()


data = load_data(data_path)
bt = Backtest(data,KCPullbackStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)