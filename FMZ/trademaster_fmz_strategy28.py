import pandas as pd
import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
import pandas_ta as ta
import logging

data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi/1.STATISTICAL_BASED/0.DATA/BTCUSDT/future/ohlc_data/2023_2024/btc_day_data_2023_2024/btc_day_data_2023_2024.csv'
# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


import pandas as pd
import pandas_ta as ta
import logging
from backtesting import Backtest, Strategy

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StochRSIMoveStrategy(Strategy):
    # Strategy Parameters
    lookback_period = 24               # Lookback period in bars for 30min timeframe (12 hours)
    rsi_length = 14                    # RSI Length
    stoch_length = 14                  # Stochastic RSI Length
    k_length = 3                       # Stochastic %K Length
    d_length = 3                       # Stochastic %D Length
    big_move_threshold = 2.5 / 100     # Big Move Threshold as percentage (2.5%)

    def init(self):
        """
        Initialize indicators.
        """
        try:
           

            # Calculate RSI without filling NaN values with zeros
            self.rsi = self.I(
                lambda close: ta.rsi(pd.Series(close), length=self.rsi_length).fillna(method='ffill').values,
                self.data.Close
            )

            # Calculate Stochastic RSI with correct parameter assignments
            stoch_rsi = ta.stochrsi(
                pd.Series(self.rsi),
                length=self.stoch_length,
                rsi_length=self.rsi_length,
                smooth1=self.k_length,
                smooth2=self.d_length,
                append=False
            )

            # Log the columns of Stochastic RSI to verify correctness
            logging.info(f"Stochastic RSI columns: {stoch_rsi.columns.tolist()}")

            # Dynamically generate expected column names based on parameters
            stochrsi_k_col = f'STOCHRSIk_{self.stoch_length}_{self.rsi_length}_{self.k_length}_{self.d_length}'
            stochrsi_d_col = f'STOCHRSId_{self.stoch_length}_{self.rsi_length}_{self.k_length}_{self.d_length}'

            expected_stochrsi_columns = [stochrsi_k_col, stochrsi_d_col]

            # Validate Stochastic RSI calculation
            for col in expected_stochrsi_columns:
                if col not in stoch_rsi.columns:
                    raise ValueError(f"Stochastic RSI calculation missing expected column: {col}")

            # Calculate Stochastic RSI %K using SMA smoothing
            self.stochrsi_k = self.I(
                lambda stoch_k: ta.sma(pd.Series(stoch_k), length=self.k_length).fillna(method='ffill').values,
                stoch_rsi[stochrsi_k_col]
            )

            # Calculate Stochastic RSI %D using SMA smoothing
            self.stochrsi_d = self.I(
                lambda stoch_d: ta.sma(pd.Series(stoch_d), length=self.d_length).fillna(method='ffill').values,
                self.stochrsi_k
            )

            # Calculate Percent Price Change from 12 hours ago
            self.price_12hrs_ago = self.I(
                lambda close: pd.Series(close).shift(self.lookback_period - 1).fillna(method='bfill').values,
                self.data.Close
            )
            self.percent_change = self.I(
                lambda close, price_12hrs: (abs(pd.Series(close) - pd.Series(price_12hrs)) / pd.Series(price_12hrs)).fillna(0).values,
                self.data.Close,
                self.price_12hrs_ago
            )

            logging.info("Indicator calculations completed successfully.")

        except Exception as e:
            logging.error(f"Error during initialization: {e}")
            raise

    def next(self):
        """
        Generate signals and manage positions.
        """
        try:
            # Retrieve current indicator values
            current_percent_change = self.percent_change[-1]
            current_stochrsi_k = self.stochrsi_k[-1]
            current_stochrsi_d = self.stochrsi_d[-1]

            # Initialize signal
            signal = 0

            # Check for Big Move
            if current_percent_change >= self.big_move_threshold:
                # Check for Oversold Conditions for Long Entry
                if current_stochrsi_k < 3 or current_stochrsi_d < 3:
                    signal = 1  # Long Signal
                    logging.info(f"Long Signal detected at price {self.data.Close[-1]:.2f}.")

                # Check for Overbought Conditions for Short Entry
                elif current_stochrsi_k > 97 or current_stochrsi_d > 97:
                    signal = -1  # Short Signal
                    logging.info(f"Short Signal detected at price {self.data.Close[-1]:.2f}.")

            # Execute Long Signal
            if signal == 1:
                # Close existing short position if any
                if self.position and self.position.is_short:
                    logging.info("Closing existing short position before entering long position.")
                    self.position.close()

                # Enter long position
                logging.info(f"Executing Long Order at price {self.data.Close[-1]:.2f}.")
                self.buy()

            # Execute Short Signal
            elif signal == -1:
                # Close existing long position if any
                if self.position and self.position.is_long:
                    logging.info("Closing existing long position before entering short position.")
                    self.position.close()

                # Enter short position
                logging.info(f"Executing Short Order at price {self.data.Close[-1]:.2f}.")
                self.sell()

        except Exception as e:
            logging.error(f"Error in next method: {e}")
            raise

def load_data(csv_file_path):
    """
    Load and preprocess data from a CSV file.

    Parameters:
    - csv_file_path (str): Path to the CSV file.

    Returns:
    - pd.DataFrame: Preprocessed DataFrame with necessary columns.
    """
    try:
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

        logging.info("Data loaded and preprocessed successfully.")
        return data

    except Exception as e:
        logging.error(f"Failed to load data: {e}")
        raise


data = load_data(data_path)

bt = Backtest(data, StochRSIMoveStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)