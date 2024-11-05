import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import pandas_ta as ta
from backtesting.lib import crossover

data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023_2024.csv'

# Function to calculate indicators on the daily timeframe

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
class EMASMACrossoverStrategy(Strategy):
    def init(self):
        # Calculate EMA and SMAs
        close = pd.Series(self.data.Close)
        self.ema = self.I(ta.ema, close, 9)
        self.sma30 = self.I(ta.sma, close, 30)
        self.sma50 = self.I(ta.sma, close, 50)
        self.sma200 = self.I(ta.sma, close, 200)
        self.sma325 = self.I(ta.sma, close, 325)

    def next(self):
        # Previous and current values for EMA and SMAs
        prev_ema = self.ema[-2]
        prev_sma30 = self.sma30[-2]
        current_ema = self.ema[-1]
        current_sma30 = self.sma30[-1]
        prev_sma50 = self.sma50[-2]
        current_sma50 = self.sma50[-1]

        # Buy Signal Condition: EMA crosses above SMA30
        buy_signal = (prev_ema < prev_sma30) and (current_ema > current_sma30)

        # Sell Signal Condition: EMA crosses below SMA30 or SMA50
        sell_signal = (prev_sma30 < prev_ema and current_sma30 > current_ema) or \
                      (prev_sma50 < prev_ema and current_sma50 > current_ema)

        # Execute buy or sell based on signals
        if buy_signal:
            self.buy()

        elif sell_signal:
            self.position.close()



data = load_data(data_path)

bt = Backtest(data, EMASMACrossoverStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)