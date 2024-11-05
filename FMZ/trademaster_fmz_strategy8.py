import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import logging
import coloredlogs
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


# MultiEMA Strategy Class
class MultiEMAStrategy(Strategy):
    def init(self):
        # Calculate EMAs
        close = pd.Series(self.data.Close)
        self.ema8 = self.I(ta.ema, close, 8)
        self.ema21 = self.I(ta.ema, close, 21)
        self.ema50 = self.I(ta.ema, close, 50)
        self.ema200 = self.I(ta.ema, close, 200)

        # Condition: All short-term EMAs must be above the 200-period EMA
        self.all_above_200 = (self.ema8 > self.ema200) & \
                             (self.ema21 > self.ema200) & \
                             (self.ema50 > self.ema200)

    def next(self):
        # Check previous and current EMA values for buy/sell signals
        prev_ema8 = self.ema8[-2]
        prev_ema21 = self.ema21[-2]
        current_ema8 = self.ema8[-1]
        current_ema21 = self.ema21[-1]
        all_above_200 = self.all_above_200[-1]

        # Buy condition: EMA8 crosses above EMA21 and all are above EMA200
        if prev_ema8 < prev_ema21 and current_ema8 > current_ema21 and all_above_200:
            self.buy()

        # Sell condition: EMA8 crosses below EMA21
        elif prev_ema8 > prev_ema21 and current_ema8 < current_ema21:
            self.position.close()



data = load_data(data_path)

bt = Backtest(data,  MultiEMAStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
# bt.plot(superimpose=False)