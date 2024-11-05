import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
import pandas_ta as ta
from backtesting.lib import crossover
import logging
import coloredlogs
import numpy as np
import pandas_ta as ta
import logging
from datetime import time


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
        logging.error(f"Error in load_and_prepare_data: {e}")
        raise


class GoldenHarmonyBreakoutStrategy(Strategy):
    def init(self):
        try:
            # Initialize indicators
            self.fast_ema = self.I(ta.ema, pd.Series(self.data.Close), 9)
            self.slow_ema = self.I(ta.ema, pd.Series(self.data.Close), 21)

            # Initialize variables for low, high, and Fibonacci levels
            self.low = np.nan
            self.high = np.nan
            self.first_crossover = False

            # Initialize class variables for storing Fibonacci levels
            self.prev_fib_618 = np.nan
            self.curr_fib_618 = np.nan

        except Exception as e:
            logging.error(f"Error in init method: {e}")
            raise

    def update_fibonacci_levels(self):
        """
        Update the Fibonacci levels based on the current low and high.
        """
        if not np.isnan(self.low) and not np.isnan(self.high):
            self.prev_fib_618 = self.curr_fib_618  # Update previous Fibonacci level
            self.curr_fib_618 = self.high - (self.high - self.low) * 0.618

    def next(self):
        try:
            # Get the current and previous Close prices
            prev_close = self.data.Close[-2]
            curr_close = self.data.Close[-1]

            # Get the current and previous EMA values
            prev_fast_ema = self.fast_ema[-2]
            curr_fast_ema = self.fast_ema[-1]
            prev_slow_ema = self.slow_ema[-2]
            curr_slow_ema = self.slow_ema[-1]

            # Track low and high after EMA crossover for Fibonacci calculation
            if prev_fast_ema < prev_slow_ema and curr_fast_ema > curr_slow_ema:
                if not self.first_crossover:
                    # On the first crossover, set low and high
                    self.low = curr_close
                    self.high = curr_close
                    self.first_crossover = True
                else:
                    # Continue updating low and high dynamically
                    self.low = min(self.low, curr_close)
                    self.high = max(self.high, curr_close)

            elif prev_fast_ema > prev_slow_ema and curr_fast_ema < curr_slow_ema:
                # Reset low, high, and the first crossover flag
                self.low = np.nan
                self.high = np.nan
                self.first_crossover = False

            # Update Fibonacci levels at each step
            self.update_fibonacci_levels()

            # Buy signal: Close price crosses above the Fibonacci 0.618 level
            if not np.isnan(self.curr_fib_618) and not np.isnan(self.prev_fib_618) and prev_close < self.prev_fib_618 and curr_close > self.curr_fib_618:
                if self.position:
                    if self.position.is_short:
                        self.position.close()
                self.buy()
                self.entry_price = curr_close

            # Sell signal: Close price crosses below the Fibonacci 0.618 level
            elif not np.isnan(self.curr_fib_618) and not np.isnan(self.prev_fib_618) and prev_close > self.prev_fib_618 and curr_close < self.curr_fib_618:
                if self.position:
                    if self.position.is_long:
                        self.position.close()
                self.sell()
                self.entry_price = curr_close

        except Exception as e:
            logging.error(f"Error in next method: {e}")
            raise


data = load_data(data_path)
bt = Backtest(data,GoldenHarmonyBreakoutStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
#bt.plot(superimpose=False)

   


