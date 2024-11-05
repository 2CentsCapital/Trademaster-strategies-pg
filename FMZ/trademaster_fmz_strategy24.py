import pandas as pd
import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
import pandas_ta as ta
import pandas as pd
import numpy as np
import pandas_ta as ta
from backtesting import Backtest, Strategy

data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi/1.STATISTICAL_BASED/0.DATA/BTCUSDT/future/ohlc_data/2023_2024/btc_day_data_2023_2024/btc_day_data_2023_2024.csv'


def calculate_bollinger_bands(close, window=20, window_dev=2):
    """
    Calculate Bollinger Bands.
    
    Parameters:
    - close (array-like): Close prices.
    - window (int): Rolling window size.
    - window_dev (float): Number of standard deviations.
    
    Returns:
    - tuple of np.ndarray: (basis, upper_band, lower_band)
    """
    close_series = pd.Series(close)
    basis = close_series.rolling(window=window).mean().fillna(0).values
    deviation = close_series.rolling(window=window).std().fillna(0).values
    upper_band = basis + (window_dev * deviation)
    lower_band = basis - (window_dev * deviation)
    return basis, upper_band, lower_band

def calculate_macd(close, fast=12, slow=26, signal=9):
    """
    Calculate MACD using pandas_ta.
    
    Parameters:
    - close (array-like): Close prices.
    - fast (int): Fast EMA period.
    - slow (int): Slow EMA period.
    - signal (int): Signal line EMA period.
    
    Returns:
    - tuple of np.ndarray: (macd_line, signal_line, histogram)
    """
    close_series = pd.Series(close)
    macd = ta.macd(close_series, fast=fast, slow=slow, signal=signal)
    
    # Assign column names directly based on known output
    macd_line_col = f'MACD_{fast}_{slow}_{signal}'
    signal_line_col = f'MACDs_{fast}_{slow}_{signal}'
    histogram_col = f'MACDh_{fast}_{slow}_{signal}'
    
    # Check if columns exist
    if macd_line_col in macd.columns and signal_line_col in macd.columns and histogram_col in macd.columns:
        macd_line = macd[macd_line_col].fillna(0).values
        signal_line = macd[signal_line_col].fillna(0).values
        histogram = macd[histogram_col].fillna(0).values
        return macd_line, signal_line, histogram
    else:
        raise ValueError(f"MACD calculation failed or missing expected columns. Available columns: {macd.columns.tolist()}")

# Function to load data from CSV

def load_data(csv_file_path):
    """
    Load and preprocess data from a CSV file.

    Parameters:
    - csv_file_path (str): Path to the CSV file.

    Returns:
    - pd.DataFrame: Preprocessed DataFrame with necessary columns.
    """
    data = pd.read_csv(csv_file_path)
    
    # Ensure that the 'timestamp' column is properly set as the index and is in datetime format
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

# Strategy Class

class VolatilityBreakoutStrategy(Strategy):
    # Strategy parameters
    atr_length = 14
    bollinger_window = 20
    bollinger_dev = 2
    rsi_length = 14
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    stop_loss_perc = 0.02  # 2% Stop Loss
    take_profit_perc = 0.04  # 4% Take Profit

    def init(self):
        """
        Initialize indicators.
        """
        try:
            # Calculate ATR
            self.atr = self.I(
                lambda high, low, close: ta.atr(
                    pd.Series(high), pd.Series(low), pd.Series(close), length=self.atr_length
                ).fillna(0).values,
                self.data.High, self.data.Low, self.data.Close
            )
            
            # Calculate Bollinger Bands - Separate calls for each component
            self.basis = self.I(
                lambda close: calculate_bollinger_bands(close, window=self.bollinger_window, window_dev=self.bollinger_dev)[0],
                self.data.Close
            )
            self.upper_band = self.I(
                lambda close: calculate_bollinger_bands(close, window=self.bollinger_window, window_dev=self.bollinger_dev)[1],
                self.data.Close
            )
            self.lower_band = self.I(
                lambda close: calculate_bollinger_bands(close, window=self.bollinger_window, window_dev=self.bollinger_dev)[2],
                self.data.Close
            )
             
            # Calculate RSI
            self.rsi = self.I(
                lambda close: ta.rsi(pd.Series(close), length=self.rsi_length).fillna(0).values,
                self.data.Close
            )
            
            # Calculate MACD - Separate calls for each component
            # Note: Calling calculate_macd separately for each component
            self.macd_line = self.I(
                lambda close: calculate_macd(close, fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)[0],
                self.data.Close
            )
            self.signal_line = self.I(
                lambda close: calculate_macd(close, fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)[1],
                self.data.Close
            )
            self.histogram = self.I(
                lambda close: calculate_macd(close, fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)[2],
                self.data.Close
            )
            
            # Initialize entry price and profit targets
            self.entry_price = None
            self.long_profit_target = None
            self.short_profit_target = None
            
            # Debugging: Print sample indicator values
            print(f"ATR Sample: {self.atr[:5]}")
            print(f"Bollinger Basis Sample: {self.basis[:5]}")
            print(f"Bollinger Upper Band Sample: {self.upper_band[:5]}")
            print(f"Bollinger Lower Band Sample: {self.lower_band[:5]}")
            print(f"RSI Sample: {self.rsi[:5]}")
            print(f"MACD Line Sample: {self.macd_line[:5]}")
            print(f"Signal Line Sample: {self.signal_line[:5]}")
            print(f"Histogram Sample: {self.histogram[:5]}")
        except Exception as e:
            print(f"Error in init method: {e}")
            raise

    def next(self):
        """
        Execute the strategy on each new bar (price data update).
        """
        try:
            # Ensure enough data is available for indicator calculations
            if (
                len(self.atr) < self.atr_length or
                len(self.basis) < self.bollinger_window or
                len(self.rsi) < self.rsi_length or
                len(self.macd_line) < self.macd_slow
            ):
                return

            # Current and previous prices
            current_close = self.data.Close[-1]
            previous_close = self.data.Close[-2]
            
            # Current and previous indicator values
            current_upper_band = self.upper_band[-1]
            previous_upper_band = self.upper_band[-2]
            current_lower_band = self.lower_band[-1]
            previous_lower_band = self.lower_band[-2]
            current_rsi = self.rsi[-1]
            current_macd = self.macd_line[-1]
            current_signal = self.signal_line[-1]
            previous_macd = self.macd_line[-2]
            previous_signal = self.signal_line[-2]
            
            # Generate long and short signals based on Bollinger Bands, RSI, and MACD
            long_condition = (
                (previous_close <= previous_upper_band) and
                (current_close > current_upper_band) and
                (current_rsi > 50) and
                (current_macd > current_signal)
            )
            
            short_condition = (
                (previous_close >= previous_lower_band) and
                (current_close < current_lower_band) and
                (current_rsi < 50) and
                (current_macd < current_signal)
            )
            
            # Signal = 1 for Buy (Long), Signal = -1 for Sell (Short)
            signal = 0
            if long_condition:
                signal = 1  # Buy signal
            elif short_condition:
                signal = -1  # Sell signal
            
            # Execute Buy Signal
            if signal == 1:
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
            elif signal == -1:
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

bt = Backtest(data, VolatilityBreakoutStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)