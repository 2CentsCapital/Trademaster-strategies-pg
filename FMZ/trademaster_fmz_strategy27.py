import pandas as pd
import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
import pandas_ta as ta




data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi/1.STATISTICAL_BASED/0.DATA/BTCUSDT/future/ohlc_data/2023_2024/btc_day_data_2023_2024/btc_day_data_2023_2024.csv'


import pandas as pd
import pandas_ta as ta
import logging
from backtesting import Backtest, Strategy

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BollingerMacdRsiStrategy(Strategy):
    # Strategy Parameters
    bb_length = 20
    bb_multiplier = 2.0
    macd_fast = 12
    macd_slow = 26
    macd_signal = 9
    rsi_length = 14
    rsi_oversold = 30
    rsi_overbought = 70
    stoploss_input = 0.02  # 2% Stop Loss
    takeprofit_input = 0.04  # 4% Take Profit

    def init(self):
        """
        Initialize indicators.
        """
        try:
            logging.info("Initializing Bollinger Bands, MACD, and RSI indicators.")

            # Bollinger Bands
            self.bb_basis = self.I(
                lambda close: ta.sma(pd.Series(close), length=self.bb_length).fillna(0).values,
                self.data.Close
            )
            self.bb_dev = self.I(
                lambda close: (self.bb_multiplier * ta.stdev(pd.Series(close), length=self.bb_length)).fillna(0).values,
                self.data.Close
            )
            self.bb_upper = self.I(
                lambda close: (
                    ta.sma(pd.Series(close), length=self.bb_length).fillna(0) + 
                    (self.bb_multiplier * ta.stdev(pd.Series(close), length=self.bb_length)).fillna(0)
                ).values,
                self.data.Close
            )
            self.bb_lower = self.I(
                lambda close: (
                    ta.sma(pd.Series(close), length=self.bb_length).fillna(0) - 
                    (self.bb_multiplier * ta.stdev(pd.Series(close), length=self.bb_length)).fillna(0)
                ).values,
                self.data.Close
            )

            logging.info("Bollinger Bands indicators calculated.")

            # MACD
            macd = ta.macd(
                close=pd.Series(self.data.Close),
                fast=self.macd_fast,
                slow=self.macd_slow,
                signal=self.macd_signal
            )

            # Expected MACD columns based on pandas_ta naming convention
            expected_macd_columns = [
                f'MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}',
                f'MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}',
                f'MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'
            ]

            # Validate MACD calculation
            for col in expected_macd_columns:
                if col not in macd.columns:
                    raise ValueError(f"MACD calculation missing expected column: {col}")

            # Assign MACD components using self.I
            self.macd_line = self.I(
                lambda close: macd[f'MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'].fillna(0).values,
                self.data.Close
            )
            self.signal_line = self.I(
                lambda close: macd[f'MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'].fillna(0).values,
                self.data.Close
            )
            self.macd_hist = self.I(
                lambda close: macd[f'MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'].fillna(0).values,
                self.data.Close
            )

            logging.info("MACD indicators calculated.")

            # RSI
            self.rsi = self.I(
                lambda close: ta.rsi(pd.Series(close), length=self.rsi_length).fillna(0).values,
                self.data.Close
            )

            logging.info("RSI indicator calculated.")

            # Initialize position-related variables
            self.entry_price = None
            self.long_profit_target = None
            self.short_profit_target = None

            logging.info("All indicators initialized successfully.")

        except Exception as e:
            logging.error(f"Error during initialization: {e}")
            raise

    def next(self):
        """
        Generate signals and manage positions.
        """
        try:
            # Current and previous prices
            current_close = self.data.Close[-1]
            previous_close = self.data.Close[-2]

            # Current indicator values
            current_bb_upper = self.bb_upper[-1]
            current_bb_lower = self.bb_lower[-1]
            current_macd = self.macd_line[-1]
            current_signal = self.signal_line[-1]
            current_rsi = self.rsi[-1]

            # Previous indicator values
            previous_macd = self.macd_line[-2]
            previous_signal = self.signal_line[-2]

            # Initialize signal
            signal = 0

            # Generate Buy Signal
            if (current_close < current_bb_lower) and (current_macd > current_signal) and (current_rsi < self.rsi_oversold):
                signal = 1
                logging.info(f"Buy Signal detected at price {current_close}.")

            # Generate Sell Signal
            elif (current_close > current_bb_upper) and (current_macd < current_signal) and (current_rsi > self.rsi_overbought):
                signal = -1
                logging.info(f"Sell Signal detected at price {current_close}.")

            # Execute Buy Signal
            if signal == 1:
                # Close existing short position if any
                if self.position and self.position.is_short:
                    logging.info("Closing existing short position before buying.")
                    self.position.close()

                # Enter long position
                logging.info(f"Executing Buy at price {current_close}.")
                self.buy()
                self.entry_price = current_close
                self.long_profit_target = current_close * (1 + self.takeprofit_input)
                self.short_profit_target = current_close * (1 - self.stoploss_input)

            # Execute Sell Signal
            elif signal == -1:
                # Close existing long position if any
                if self.position and self.position.is_long:
                    logging.info("Closing existing long position before selling.")
                    self.position.close()

                # Enter short position
                logging.info(f"Executing Sell at price {current_close}.")
                self.sell()
                self.entry_price = current_close
                self.long_profit_target = current_close * (1 + self.takeprofit_input)
                self.short_profit_target = current_close * (1 - self.stoploss_input)

            # Manage Take Profit and Stop Loss for Long Positions
            if self.position.is_long and self.entry_price:
                if current_close >= self.long_profit_target:
                    logging.info(f"Take Profit reached at price {current_close}. Exiting long position.")
                    self.position.close()
                    self.entry_price = None
                    self.long_profit_target = None
                    self.short_profit_target = None

                elif current_close <= self.short_profit_target:
                    logging.info(f"Stop Loss triggered at price {current_close}. Exiting long position.")
                    self.position.close()
                    self.entry_price = None
                    self.long_profit_target = None
                    self.short_profit_target = None

            # Manage Take Profit and Stop Loss for Short Positions
            if self.position.is_short and self.entry_price:
                if current_close <= self.short_profit_target:
                    logging.info(f"Take Profit reached at price {current_close}. Exiting short position.")
                    self.position.close()
                    self.entry_price = None
                    self.long_profit_target = None
                    self.short_profit_target = None

                elif current_close >= self.long_profit_target:
                    logging.info(f"Stop Loss triggered at price {current_close}. Exiting short position.")
                    self.position.close()
                    self.entry_price = None
                    self.long_profit_target = None
                    self.short_profit_target = None

            logging.debug("Next method processing complete.")

        except Exception as e:
            logging.error(f"Error in next method: {e}")
            raise

# Function to load data from CSV
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

bt = Backtest(data,BollingerMacdRsiStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)