import pandas as pd
import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
import pandas_ta as ta
import pandas as pd
import numpy as np
import pandas_ta as ta
import logging
from backtesting import Backtest, Strategy
from backtesting.lib import crossover


data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi/1.STATISTICAL_BASED/0.DATA/BTCUSDT/future/ohlc_data/2023_2024/btc_day_data_2023_2024/btc_day_data_2023_2024.csv'


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



class DCA_Trading_Strategy(Strategy):
    # Strategy Parameters
    stoploss_input = 0.06604  # 6.604% Stop Loss
    takeprofit_input = 0.02328  # 2.328% Take Profit
    dca_enabled = False  # Toggle DCA
    dca_interval = 1  # Interval in hours for DCA (if enabled)
    RSILowerLevel = 42
    RSIUpperLevel = 70
    rsi_length = 14
    bb_length = 20
    bb_multiplier = 1.0
    dca_amount = 0.1  # Fraction of the initial position to add in DCA

    def init(self):
    
            # Calculate RSI
            self.rsi = self.I(
                lambda close: ta.rsi(pd.Series(close), length=self.rsi_length).fillna(0).values,
                self.data.Close
            )

            # Calculate Bollinger Bands
            self.basis = self.I(
                lambda close: ta.sma(pd.Series(close), length=self.bb_length).fillna(0).values,
                self.data.Close
            )
            self.upper_band = self.I(
                lambda close: (self.basis + self.bb_multiplier * ta.stdev(pd.Series(close), length=self.bb_length)).fillna(0).values,
                self.data.Close
            )
            self.lower_band = self.I(
                lambda close: (self.basis - self.bb_multiplier * ta.stdev(pd.Series(close), length=self.bb_length)).fillna(0).values,
                self.data.Close
            )

            # Initialize position-related variables
            self.entry_price = None
            self.long_profit_target = None
            self.short_profit_target = None
            self.dca_counter = 0  # Counter for DCA intervals

      

    def next(self):
  
            # Current and previous close prices
            current_close = self.data.Close[-1]
            previous_close = self.data.Close[-2]

            # Current and previous indicator values
            current_rsi = self.rsi[-1]
            previous_rsi = self.rsi[-2]
            current_upper_band = self.upper_band[-1]
            previous_upper_band = self.upper_band[-2]
            current_lower_band = self.lower_band[-1]
            previous_lower_band = self.lower_band[-2]

            # Generate Buy/Sell signals based on RSI and Bollinger Bands
            buy_signal = (
                (previous_close <= previous_lower_band) and
                (current_close > current_lower_band) and
                (current_rsi > self.RSILowerLevel)
            )

            sell_signal = (
                (previous_close >= previous_upper_band) and
                (current_close < current_upper_band) and
                (current_rsi > self.RSIUpperLevel)
            )

            # Get the current hour for DCA logic
            current_hour = self.data.index[-1].hour

            # Handle Buy Signal
            if buy_signal:
               
                self.entry_price = current_close
                self.buy()  # Enter long position
                self.long_profit_target = current_close * (1 + self.takeprofit_input)
                self.short_profit_target = current_close * (1 - self.stoploss_input)

            # Handle Sell Signal
            if sell_signal:
             
                if self.position.is_long:
                    # Calculate SL and TP based on entry price
                    stop_loss_level = self.entry_price * (1 - self.stoploss_input)
                    take_profit_level = self.entry_price * (1 + self.takeprofit_input)
                    self.sell()  # Exit long position
                    self.entry_price = None
                    self.long_profit_target = None
                    self.short_profit_target = None

            # Handle DCA Logic (if enabled)
            if self.dca_enabled and self.position.is_long:
                # Increment DCA counter
                self.dca_counter += 1
                if self.dca_counter >= self.dca_interval:
                   
                    self.buy(size=self.position.size * self.dca_amount)  # Add to existing position
                    self.dca_counter = 0  # Reset counter

            # Manage Take Profit and Stop Loss
            if self.position.is_long and self.entry_price:
                if current_close >= self.long_profit_target:
                  
                    self.sell()  # Exit long position
                    self.entry_price = None
                    self.long_profit_target = None
                    self.short_profit_target = None

                elif current_close <= self.short_profit_target:
                   
                    self.sell()  # Exit long position
                    self.entry_price = None
                    self.long_profit_target = None
                    self.short_profit_target = None

            



# Function to load data from CSV
def load_data(csv_file_path):

        data = pd.read_csv(csv_file_path)

        # Ensure that the 'timestamp' column is in datetime format
        if 'timestamp' in data.columns:
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            data.set_index('timestamp', inplace=True)  # Set as DatetimeIndex
        else:
            raise ValueError("CSV data must contain a 'timestamp' column.")

        # Rename columns to match backtesting library expectations
        data.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)

        # Handle missing values by forward filling
        data.fillna(method='ffill', inplace=True)

        return data



data = load_data(data_path)

bt = Backtest(data, DCA_Trading_Strategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)