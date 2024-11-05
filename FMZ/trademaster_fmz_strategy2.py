import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
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


import pandas as pd
import pandas_ta as ta
from backtesting import Backtest, Strategy

# Function to load data from CSV
def load_data(csv_file_path):
    data = pd.read_csv(csv_file_path)
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data.set_index('timestamp', inplace=True)
    data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
    return data

# ComboStrategy class with indicator calculation in `init` and signal generation/position handling in `next`
class ComboStrategy(Strategy):
    def init(self):
        # Calculate indicators once during the initialization phase
        close = pd.Series(self.data.Close)
        open_ = pd.Series(self.data.Open)
        volume = pd.Series(self.data.Volume)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)

        # Calculate SMAs, EMAs, and OHLC average
        self.sma01 = self.I(ta.sma, close, 3)
        self.sma02 = self.I(ta.sma, close, 8)
        self.sma03 = self.I(ta.sma, close, 10)
        self.ema01 = self.I(ta.ema, close, 5)
        self.ema02 = self.I(ta.ema, close, 3)
        self.ohlc = self.I(lambda o, h, l, c: (o + h + l + c) / 4, open_, high, low, close)

        # Initialize variables for position tracking
        self.BarsSinceEntry = 0
        self.MaxProfitCount = 0
        self.MaxBars = 10
        self.position_avg_price = None

    def next(self):
        # Fetch the latest values of indicators
        current_close = self.data.Close[-1]
        current_open = self.data.Open[-1]
        prev_close = self.data.Close[-2]
        current_volume = self.data.Volume[-1]
        prev_volume = self.data.Volume[-2]

        # Define conditions for signal generation based on indicators
        cond01 = current_close < self.sma03[-1]
        cond02 = current_close <= self.sma01[-1]
        cond03 = prev_close > self.sma01[-2]
        cond04 = current_open > self.ema01[-1]
        cond05 = self.sma02[-1] < self.sma02[-2]

        entry01 = cond01 and cond02 and cond03 and cond04 and cond05

        cond06 = current_close < self.ema02[-1]
        cond07 = current_open > self.ohlc[-1]
        cond08 = current_volume <= prev_volume
        shifted_open = self.data.Open[-2]
        shifted_close = self.data.Close[-2]
        cond09 = (current_close < min(shifted_open, shifted_close)) or (current_close > max(shifted_open, shifted_close))

        entry02 = cond06 and cond07 and cond08 and cond09

        # Set buy condition if either entry01 or entry02 is true
        buy_condition = entry01 or entry02

        # Cond00: Check if no position is open
        cond00 = self.position.size == 0

        # Update BarsSinceEntry and MaxProfitCount
        if cond00:
            self.BarsSinceEntry = 0  # Reset BarsSinceEntry if no position
            self.MaxProfitCount = 0  # Reset MaxProfitCount if no position
        else:
            self.BarsSinceEntry += 1
            if current_close > self.position_avg_price and self.BarsSinceEntry > 1:
                self.MaxProfitCount += 1  # Increment MaxProfitCount if profit condition is met

        # Check if we should enter a position based on signals
        if buy_condition and cond00:
            self.buy(size=1)
            self.position_avg_price = current_close  # Store the entry price

        # Exit the position if BarsSinceEntry exceeds MaxBars or MaxProfitCount exceeds threshold
        if (self.BarsSinceEntry >= self.MaxBars) or (self.MaxProfitCount >= 5):
            self.position.close()





data = load_data(data_path)
bt = Backtest(data,ComboStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
# bt.plot(superimpose=False)

   


