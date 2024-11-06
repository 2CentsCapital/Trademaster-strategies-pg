import pandas as pd
import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
import pandas_ta as ta
from TradeMaster.lib import crossover, crossunder

# Define your data path
data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023.csv'

# Load the data from the CSV file
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

# Calculate MACD and VWMA indicators
def calculate_indicators(data, macd_fast=12, macd_slow=26, macd_signal=9, vwma1=20, vwma2=50):
    try:
        # Calculate MACD indicators
        macd = ta.macd(data['Close'], fast=macd_fast, slow=macd_slow, signal=macd_signal)
        data['MACD'] = macd['MACD_12_26_9']
        data['Signal'] = macd['MACDs_12_26_9']
        data['Histogram'] = macd['MACDh_12_26_9']

        # Calculate VWMA indicators
        data['VWMA20'] = ta.vwma(data['Close'], length=vwma1)
        data['VWMA50'] = ta.vwma(data['Close'], length=vwma2)

        return data
    except Exception as e:
        print(f"Error in calculate_indicators: {e}")
        raise

class MACDVWMAStrategy(Strategy):
    leverage = 1
    commission_value_input = 3
    precision = 2

    def init(self):
        # Access calculated indicators
        self.macd = self.data.MACD
        self.signal = self.data.Signal
        self.histogram = self.data.Histogram
        self.vwma20 = self.data.VWMA20
        self.vwma50 = self.data.VWMA50

        # Calculate commission value based on leverage
        self.commission_value = (self.commission_value_input / 100) / self.leverage

    def next(self):
        # Calculate leveraged contracts
        leveraged_contracts = max(round(self.equity * self.leverage / self.data.Close[-1], self.precision), 0)

        # Generate MACD signals
        macd_long_entry_signal = self.histogram[-1] > 0
        macd_long_exit_signal = self.histogram[-1] < 0
        macd_short_entry_signal = self.histogram[-1] < 0
        macd_short_exit_signal = self.histogram[-1] > 0

        # VWMA conditions for long and short positions
        vwma_long_entry_signal = self.vwma20[-1] > self.vwma50[-1]
        vwma_short_entry_signal = self.vwma20[-1] < self.vwma50[-1]

        # Combined long entry and exit signals
        long_entry = macd_long_entry_signal and vwma_long_entry_signal
        long_exit = crossunder(self.macd, self.signal)

        # Combined short entry and exit signals
        short_entry = macd_short_entry_signal and vwma_short_entry_signal
        short_exit = crossover(self.macd, self.signal)

        # Execute long and short orders based on the conditions
        if long_entry:
            if self.position.is_short:
                self.position.close()
            self.buy(size=leveraged_contracts)

        if long_exit and self.position.is_long:
            self.position.close()

        if short_entry:
            if self.position.is_long:
                self.position.close()
            self.sell(size=leveraged_contracts)

        if short_exit and self.position.is_short:
            self.position.close()

# Load data and run backtest
data = load_data(data_path)
data = calculate_indicators(data)
bt = Backtest(data, MACDVWMAStrategy, cash=100000, commission=0.003, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
