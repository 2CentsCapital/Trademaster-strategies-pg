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
class RetracementStrategy(Strategy):
    def init(self):
 # Get Close, High, Low, and Volume as Pandas Series
            close = pd.Series(self.data.Close)
            high = pd.Series(self.data.High)
            low = pd.Series(self.data.Low)

            # Calculate moving averages (50-period and 200-period SMA)
            self.ma_50 = self.I(ta.sma, close, 50)
            self.ma_200 = self.I(ta.sma, close, 200)

            # Define retracement level lengths
            len_21 = 21
            len_50 = 50
            len_9 = 9

            # Apply condition: Calculate retracement levels only when close > MA_200 and close > MA_50
            condition = (close > self.ma_200) & (close > self.ma_50)

            # Calculate retracement levels only when the condition is met
            self.retrace_21_high = self.I(
                lambda h: np.where(condition, h.rolling(window=len_21).max(), np.nan), high)
            self.retrace_21_low = self.I(
                lambda l: np.where(condition, l.rolling(window=len_21).min(), np.nan), low)
            self.retrace_50_high = self.I(
                lambda h: np.where(condition, h.rolling(window=len_50).max(), np.nan), high)
            self.retrace_50_low = self.I(
                lambda l: np.where(condition, l.rolling(window=len_50).min(), np.nan), low)
            self.retrace_9_high = self.I(
                lambda h: np.where(condition, h.rolling(window=len_9).max(), np.nan), high)
            self.retrace_9_low = self.I(
                lambda l: np.where(condition, l.rolling(window=len_9).min(), np.nan), low)

            # Calculate mid-points for retracement levels
            self.retrace_21_mid = (self.retrace_21_high + self.retrace_21_low) / 2
            self.retrace_50_mid = (self.retrace_50_high + self.retrace_50_low) / 2
            self.retrace_9_mid = (self.retrace_9_high + self.retrace_9_low) / 2

            # Calculate Fibonacci levels based on the retracement mid-points
            self.fib_50_level = (self.retrace_21_mid + self.retrace_50_mid + self.retrace_9_mid) / 3
            self.fib_786_level = (self.retrace_21_high + self.retrace_50_high + self.retrace_9_high) / 3 - (
                ((self.retrace_21_high + self.retrace_50_high + self.retrace_9_high) -
                (self.retrace_21_low + self.retrace_50_low + self.retrace_9_low)) * 0.786)

    def next(self):
        # Fetch latest values
        latest_close = self.data.Close[-1]
        latest_ma_50 = self.ma_50[-1]
        latest_ma_200 = self.ma_200[-1]
        latest_fib_50_level = self.fib_50_level[-1]
        latest_fib_786_level = self.fib_786_level[-1]

        # Buy condition: Close price > ma_200, ma_50 and is <= fib_50 level
        if latest_close > latest_ma_200 and latest_close > latest_ma_50 and latest_close <= latest_fib_50_level:
            risk_reward_ratio = 2.0
            take_profit_level = latest_close + (latest_close - latest_fib_786_level) * risk_reward_ratio
            stop_loss_level = latest_fib_786_level

            # Execute buy trade with stop loss and take profit
            self.buy(sl=stop_loss_level, tp=take_profit_level)




data = load_data(data_path)

bt = Backtest(data, RetracementStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)