import pandas as pd
import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
import pandas_ta as ta

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


def calculate_supertrend(high, low, close, length, multiplier):
    """
    Calculate Supertrend indicator using pandas_ta.

    Parameters:
    - high (array-like): High prices.
    - low (array-like): Low prices.
    - close (array-like): Close prices.
    - length (int): ATR period for Supertrend.
    - multiplier (float): Multiplier for ATR in Supertrend calculation.

    Returns:
    - np.ndarray: Supertrend values.
    """
    # Convert inputs to pandas Series
    high_series = pd.Series(high)
    low_series = pd.Series(low)
    close_series = pd.Series(close)
    
    # Calculate Supertrend
    supertrend_df = ta.supertrend(high_series, low_series, close_series, length=length, multiplier=multiplier)
    
    # Define the expected Supertrend column name
    supertrend_column = f'SUPERT_{length}_{multiplier}.0'
    
    # Check if the Supertrend DataFrame is valid
    if supertrend_df is not None and supertrend_column in supertrend_df.columns:
        return supertrend_df[supertrend_column].values
    else:
        raise ValueError(f"Supertrend calculation failed or missing column: {supertrend_column}")

class SupertrendStrategy(Strategy):
    # Strategy parameters
    length1, factor1 = 7, 3
    length2, factor2 = 14, 2
    length3, factor3 = 21, 1
    stop_loss_perc = 0.02  # 2% Stop Loss
    take_profit_perc = 0.04  # 4% Take Profit

    def init(self):
        """
        Initialize Supertrend indicators.
        """
        try:
            # Calculate Supertrend1
            self.supertrend1 = self.I(
                calculate_supertrend, 
                self.data.High, 
                self.data.Low, 
                self.data.Close, 
                length=self.length1, 
                multiplier=self.factor1
            )
            
            # Calculate Supertrend2
            self.supertrend2 = self.I(
                calculate_supertrend, 
                self.data.High, 
                self.data.Low, 
                self.data.Close, 
                length=self.length2, 
                multiplier=self.factor2
            )
            
            # Calculate Supertrend3
            self.supertrend3 = self.I(
                calculate_supertrend, 
                self.data.High, 
                self.data.Low, 
                self.data.Close, 
                length=self.length3, 
                multiplier=self.factor3
            )
            
            # Initialize entry price and profit targets
            self.entry_price = None
            self.long_profit_target = None
            self.short_profit_target = None
        except Exception as e:
            print(f"Error in init method: {e}")
            raise

    def next(self):
        """
        Execute the strategy on each new bar (price data update).
        """
        try:
            # Ensure enough data is available for Supertrend calculations
            if (
                len(self.supertrend1) < self.length1 or
                len(self.supertrend2) < self.length2 or
                len(self.supertrend3) < self.length3
            ):
                return

            # Current and previous prices
            current_close = self.data.Close[-1]
            previous_close = self.data.Close[-2]
            
            # Current and previous Supertrend values
            current_supertrend1 = self.supertrend1[-1]
            previous_supertrend1 = self.supertrend1[-2]
            current_supertrend2 = self.supertrend2[-1]
            previous_supertrend2 = self.supertrend2[-2]
            current_supertrend3 = self.supertrend3[-1]
            previous_supertrend3 = self.supertrend3[-2]
            
            # Buy Signal: Close crosses above any Supertrend
            buy_signal = (
                (previous_close <= previous_supertrend1 and current_close > current_supertrend1) or
                (previous_close <= previous_supertrend2 and current_close > current_supertrend2) or
                (previous_close <= previous_supertrend3 and current_close > current_supertrend3)
            )
            
            # Sell Signal: Close crosses below any Supertrend
            sell_signal = (
                (previous_close >= previous_supertrend1 and current_close < current_supertrend1) or
                (previous_close >= previous_supertrend2 and current_close < current_supertrend2) or
                (previous_close >= previous_supertrend3 and current_close < current_supertrend3)
            )
            
            # Execute Buy Signal
            if buy_signal:
                # Close existing short position if any
                if self.position and self.position.is_short:
                    self.position.close()
                
                # Enter long position with Stop Loss and Take Profit
                sl = current_close * (1 - self.stop_loss_perc)
                tp = current_close * (1 + self.take_profit_perc)
                self.buy(sl=sl, tp=tp)
                self.entry_price = current_close
                self.long_profit_target = tp
                self.short_profit_target = None  # Reset short profit target
            
            # Execute Sell Signal
            elif sell_signal:
                # Close existing long position if any
                if self.position and self.position.is_long:
                    self.position.close()
                
                # Enter short position with Stop Loss and Take Profit
                sl = current_close * (1 + self.stop_loss_perc)
                tp = current_close * (1 - self.take_profit_perc)
                self.sell(sl=sl, tp=tp)
                self.entry_price = current_close
                self.short_profit_target = tp
                self.long_profit_target = None  # Reset long profit target
            
            # Managing long position (take profit)
            if self.position.is_long and self.long_profit_target:
                if current_close >= self.long_profit_target:
                    self.position.close()
                    self.long_profit_target = None  # Reset after taking profit
            
            # Managing short position (take profit)
            if self.position.is_short and self.short_profit_target:
                if current_close <= self.short_profit_target:
                    self.position.close()
                    self.short_profit_target = None  # Reset after taking profit
        except Exception as e:
            print(f"Error in next method: {e}")
            raise

data = load_data(data_path)

bt = Backtest(data, SupertrendStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)