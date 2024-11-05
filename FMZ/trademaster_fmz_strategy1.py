import pandas as pd
import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
import pandas_ta as ta
from TradeMaster.lib import crossover
import numpy as np
import pandas_ta as ta
from datetime import time


data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023.csv'


def load_data(csv_file_path):
    try:
        
        data = pd.read_csv(csv_file_path)
        # data['timestamp'] = pd.to_datetime(data['timestamp'])
        # data.set_index('timestamp', inplace=True)
        data.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
       
        return data
    except Exception as e:
        print(f"Error in load_and_prepare_data: {e}")
        raise




def calculate_daily_indicators(daily_data):
    try:
        # Calculate EMAs, HMA, and SMA using pandas_ta
        daily_data['fast_ema'] = ta.ema(daily_data['Close'], length=9)
        daily_data['slow_ema'] = ta.ema(daily_data['Close'], length=21)
        daily_data['ema_200'] = ta.ema(daily_data['Close'], length=200)
        daily_data['hma_300'] = ta.hma(daily_data['Close'], length=300)
        daily_data['ma_18'] = ta.sma(daily_data['Close'], length=18)

        # Initialize columns for Fibonacci levels
        daily_data['fib_618'] = np.nan
        daily_data['fib_65'] = np.nan

        # Initialize variables for low, high, and a flag for the first crossover
        low = np.nan
        high = np.nan
        first_crossover = False

        # Loop through data to calculate indicators and Fibonacci levels
        for i in range(1, len(daily_data)):
            # Get current and previous values of EMAs
            prev_fast_ema = daily_data['fast_ema'].iloc[i - 1]
            curr_fast_ema = daily_data['fast_ema'].iloc[i]
            prev_slow_ema = daily_data['slow_ema'].iloc[i - 1]
            curr_slow_ema = daily_data['slow_ema'].iloc[i]

            # Check if fast EMA crosses above slow EMA (crossover)
            if prev_fast_ema < prev_slow_ema and curr_fast_ema > curr_slow_ema:
                if not first_crossover:  # If this is the first crossover
                    # Initialize low and high at the first crossover
                    low = daily_data['Close'].iloc[i] if np.isnan(low) else low
                    high = daily_data['Close'].iloc[i] if np.isnan(high) else high
                    first_crossover = True
                else:  # Update low and high after the first crossover
                    low = min(low, daily_data['Close'].iloc[i]) if not np.isnan(low) else daily_data['Close'].iloc[i]
                    high = max(high, daily_data['Close'].iloc[i]) if not np.isnan(high) else daily_data['Close'].iloc[i]

            # Check if fast EMA crosses below slow EMA (crossunder)
            elif prev_fast_ema > prev_slow_ema and curr_fast_ema < curr_slow_ema:
                # Reset low, high, and the first crossover flag
                low = np.nan
                high = np.nan
                first_crossover = False

            # Calculate Fibonacci levels if low and high are set
            if not np.isnan(low) and not np.isnan(high):
                daily_data.at[daily_data.index[i], 'fib_618'] = high - (high - low) * 0.618
                daily_data.at[daily_data.index[i], 'fib_65'] = high - (high - low) * 0.65

        return daily_data

    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise

def generate_signals(daily_data):
    try:
        daily_data['signal'] = 0  # Initialize signal column

        # Loop through data to check conditions for buy and sell signals
        for i in range(1, len(daily_data)):
            # Previous and current Close prices
            prev_close = daily_data['Close'].iloc[i - 1]
            curr_close = daily_data['Close'].iloc[i]

            # Previous and current Fibonacci 0.618 level
            prev_fib_618 = daily_data['fib_618'].iloc[i - 1]
            curr_fib_618 = daily_data['fib_618'].iloc[i]

            # Check for Buy Signal: Close price crosses above the Fibonacci 0.618 level
            if not np.isnan(curr_fib_618) and not np.isnan(prev_fib_618) and prev_close < prev_fib_618 and curr_close > curr_fib_618:
                daily_data.at[daily_data.index[i], 'signal'] = 1

            # Check for Sell Signal: Close price crosses below the Fibonacci 0.618 level
            elif not np.isnan(curr_fib_618) and not np.isnan(prev_fib_618) and prev_close > prev_fib_618 and curr_close < curr_fib_618:
                daily_data.at[daily_data.index[i], 'signal'] = -1

        return daily_data

    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise


class GoldenHarmonyBreakoutStrategy(Strategy):
    def init(self):
        # Since data is already pre-processed, we don't need to calculate indicators here
        pass

    def next(self):
       
        # Use the generated signal to buy/sell
        current_signal = self.data.signal[-1]

        if current_signal == 1:
            if self.position().is_short:
                self.position().close()
            self.buy()

        elif current_signal == -1:
            if self.position().is_long:
                self.position().close()
            self.sell()




data = load_data(data_path)
data= calculate_daily_indicators(data)
data = generate_signals(data)
bt = Backtest(data,GoldenHarmonyBreakoutStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
#bt.tear_sheet()


   


