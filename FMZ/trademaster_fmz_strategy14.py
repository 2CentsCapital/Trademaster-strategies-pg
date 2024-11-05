import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
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
class PullbackStrategy(Strategy):
    ma_length1 = 200
    ma_length2 = 13
    too_deep = 0.27
    too_thin = 0.03
    stop_loss_pct = 0.07  # 7% Stop Loss

    def init(self):
        # Calculate moving averages
        close = pd.Series(self.data.Close)
        self.ma1 = self.I(ta.sma, close, self.ma_length1)
        self.ma2 = self.I(ta.sma, close, self.ma_length2)

        # Calculate 'too_deep' and 'too_thin' conditions
        ratio = self.ma2 / self.ma1 - 1
        self.too_deep = ratio < self.too_deep
        self.too_thin = ratio > self.too_thin

    

        # Initialize entry price and stop loss
        self.entry_price = None
        self.stop_loss = None

    def next(self):
        current_price = self.data.Close[-1]

        # Access current indicators
        ma1 = self.ma1[-1]
        ma2 = self.ma2[-1]
        too_deep = self.too_deep[-1]
        too_thin = self.too_thin[-1]

        # Buy condition
        buy_condition = (
            current_price > ma1 and
            current_price < ma2 and
            too_deep and
            too_thin
        )

        # Close condition 1: price crosses above ma2 and below previous Low
        if len(self.data.Low) >= 2:
            prev_low = self.data.Low[-2]
            close_condition1 = (
                current_price > ma2 and
                current_price < prev_low
            )
        else:
            close_condition1 = False

        # Close condition 2: stop loss triggered
        if self.position.is_long and self.entry_price:
            stop_distance = (self.entry_price - current_price) / current_price
            close_condition2 = stop_distance > self.stop_loss_pct
        else:
            close_condition2 = False

        # Entry logic
        if buy_condition and not self.position.is_long:
            self.entry_price = current_price
            self.stop_loss = self.entry_price * (1 - self.stop_loss_pct)
            self.buy()

        # Exit logic
        if self.position.is_long:
            if close_condition1 or close_condition2:
                self.position.close()
                self.entry_price = None
                self.stop_loss = None

    # Optional: Define custom stop loss handling if needed
    def set_sl(self, price):
        self.stop_loss = price



data = load_data(data_path)

bt = Backtest(data, PullbackStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)