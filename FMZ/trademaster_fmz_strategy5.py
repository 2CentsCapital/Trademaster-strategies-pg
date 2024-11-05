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

# Strategy Class
class BBStrategy(Strategy):
    def init(self, length=20, mult=2.0, ma_type='SMA'):
        # Moving average calculation based on selected type
        close = pd.Series(self.data.Close)
        if ma_type == 'SMA':
            self.basis = self.I(ta.sma, close, length)
        elif ma_type == 'EMA':
            self.basis = self.I(ta.ema, close, length)
        elif ma_type == 'SMMA (RMA)':
            self.basis = self.I(ta.rma, close, length)
        elif ma_type == 'WMA':
            self.basis = self.I(ta.wma, close, length)
        elif ma_type == 'VWMA':
            self.basis = self.I(ta.vwma, close, length)

        # Calculate the Bollinger Bands
        self.std_dev = self.I(lambda x: x.rolling(window=length).std(), close)
        self.upper = self.I(lambda b, s: b + (s * mult), self.basis, self.std_dev)
        self.lower = self.I(lambda b, s: b - (s * mult), self.basis, self.std_dev)

    def next(self):
        latest_close = self.data.Close[-1]
        latest_signal = 0

        # Long condition: Close crosses above upper band
        if self.data.Close[-2] < self.upper[-2] and latest_close > self.upper[-1]:
            latest_signal = 1  # Buy signal

        # Short condition: Close crosses below lower band
        elif self.data.Close[-2] > self.lower[-2] and latest_close < self.lower[-1]:
            latest_signal = -1  # Sell signal

        # Handle position management
        if self.position.is_long:
            if latest_signal == -1:  # If sell signal, close long position
                self.position.close()

        elif self.position.is_short:
            if latest_signal == 1:  # If buy signal, close short position
                self.position.close()

        # Execute buy (long) or sell (short) based on the latest signal
        if latest_signal == 1 and not self.position.is_long:
            self.buy()

        elif latest_signal == -1 and not self.position.is_short:
            self.sell()


data = load_data(data_path)

bt = Backtest(data, BBStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)