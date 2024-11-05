import pandas as pd
import pandas_ta as ta
from backtesting import Backtest, Strategy
import numpy as np


data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi/1.STATISTICAL_BASED/0.DATA/BTCUSDT/future/ohlc_data/2023_2024/btc_day_data_2023_2024/btc_day_data_2023_2024.csv'
# 2. Indicator Calculation

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
class TAMMY_V2(Strategy):
    fast_len = 14
    slow_len = 100
    atr_length = 10
    risk_per_trade = 2.0  # Percentage risk per trade

    def init(self):
        # Access data

        close = pd.Series(self.data.Close)
        high = pd.Series(self.data.High)
        low = pd.Series(self.data.Low)
      
        # Calculate SMAs
        self.fast_sma = self.I(ta.sma, close, self.fast_len)
        self.slow_sma = self.I(ta.sma, close, self.slow_len)

        # Calculate True Range (TR)
        tr = pd.Series(np.maximum.reduce([
            self.data.High - self.data.Low,
            abs(self.data.High - close.shift(1)),
            abs(self.data.Low - close.shift(1))
        ]))

        # Calculate ATR
        self.atr = self.I(ta.sma, tr, self.atr_length)

        # Initialize stop loss
        self.stop_loss = None

    def next(self):
        # Current index
        i = len(self.data) - 1

        # Access current values
        current_close = self.data.Close[-1]
        previous_close = self.data.Close[-2] if i >= 1 else None

        current_fast_sma = self.fast_sma[-1]
        previous_fast_sma = self.fast_sma[-2] if i >= 1 else None

        current_slow_sma = self.slow_sma[-1]
        previous_slow_sma = self.slow_sma[-2] if i >= 1 else None

        current_atr = self.atr[-1]

        # Generate signals
        buy_signal = False
        sell_signal = False

        # Check for buy signal
        if previous_close is not None and previous_slow_sma is not None:
            if (current_close > current_slow_sma) and (previous_close <= previous_slow_sma):
                buy_signal = True

        # Check for sell signal
        if previous_close is not None and previous_fast_sma is not None:
            if (current_close < current_fast_sma) and (previous_close >= previous_fast_sma):
                sell_signal = True

        # Entry logic
        if buy_signal and not self.position.is_long:
            # Calculate stop loss price
            self.stop_loss = current_close - current_atr * (self.risk_per_trade / 100)
            # Buy with a stop loss
            self.buy(sl=self.stop_loss)

        # Exit logic
        if self.position.is_long:
            # Check for stop loss hit
            if current_close <= self.stop_loss:
                self.position.close()
            # Check for sell signal
            elif sell_signal:
                self.position.close()

    # Optional: Implement a method to update the stop loss dynamically
    def update_stop_loss(self):
        if self.position.is_long:
            # For example, trailing stop loss logic can be implemented here
            pass





data = load_data(data_path)

bt = Backtest(data,TAMMY_V2, cash=100000, commission=.002, exclusive_orders=True)


stats = bt.run()
print(stats)

# bt.plot(superimpose=False)