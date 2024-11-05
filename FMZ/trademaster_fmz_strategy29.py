import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
import pandas_ta as ta
import logging
import coloredlogs

# Set up logging
log_file_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi_strategy_backtest/1.STATISTICAL_AND_PROBABILITY_BASED/1.fmz_pinescript_strategies_backtest/Trademaster_fmz_30_strategies/tradebook/29_ChandeKrollStopStrategy(.log'

# Configure basic logging to file
logging.basicConfig(level=logging.DEBUG, filename=log_file_path, filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Set up colored logs for console output
coloredlogs.install(level='DEBUG',
                    fmt='%(asctime)s - %(levelname)s - %(message)s',
                    level_styles={
                        'info': {'color': 'green'},
                        'debug': {'color': 'white'},
                        'error': {'color': 'red'},
                    })

def load_and_prepare_data(csv_file_path):
    try:
        logging.info("Loading and preparing data.")
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
        logging.info("Data loading and preparation complete.")
        return data
    except Exception as e:
        logging.error(f"Error in load_and_prepare_data: {e}")
        raise



def calculate_daily_indicators(daily_data, p=10, x=1, q=9, adxlen=14, dilen=14):
    """
    Calculate the Chande Kroll Stop and ADX indicators on a 10-minute timeframe.
    """

  
    daily_data['ATR'] = ta.atr(daily_data['High'], daily_data['Low'], daily_data['Close'], length=p)
    
    # Initial High and Low Stops
    daily_data['first_high_stop'] = daily_data['High'].rolling(window=p).max() - x * daily_data['ATR']
    daily_data['first_low_stop'] = daily_data['Low'].rolling(window=p).min() + x * daily_data['ATR']
    
    # Final Stop Levels
    daily_data['stop_short'] = daily_data['first_high_stop'].rolling(window=q).max()
    daily_data['stop_long'] = daily_data['first_low_stop'].rolling(window=q).min()
    
    # ADX Calculation
    daily_data['ADX'] = ta.adx(daily_data['High'], daily_data['Low'], daily_data['Close'], length=dilen)['ADX_14']
    daily_data['plus_DI'] = ta.adx(daily_data['High'], daily_data['Low'], daily_data['Close'], length=dilen)['DMP_14']
    daily_data['minus_DI'] = ta.adx(daily_data['High'], daily_data['Low'], daily_data['Close'], length=dilen)['DMN_14']
    
    return daily_data

def generate_signals(daily_data, ADX_sig=20):
    """
    Generate trading signals based on the Chande Kroll Stop strategy logic.
    """
    daily_data['signal'] = 0
    
    # Long Entry
    daily_data.loc[(daily_data['Close'] < daily_data['stop_long']) & (daily_data['ADX'] > ADX_sig), 'signal'] = 1
    
    # Short Entry
    daily_data.loc[(daily_data['Close'] > daily_data['stop_short']) & (daily_data['ADX'] > ADX_sig), 'signal'] = -1
    
    return daily_data

class ChandeKrollStopStrategy(Strategy):

    def init(self):
        try:
            logging.info("Initializing Rainbow Oscillator Strategy")
            self.entry_price = None
            logging.info("Initialization complete")
        except Exception as e:
            logging.error(f"Error in init method: {e}")
            raise

    def next(self):
        try:
            current_signal = self.data.signal[-1]
            current_price = self.data.Close[-1]
            logging.debug(f"Processing bar: {self.data.index[-1]} with signal {current_signal} at price {current_price}")

                
                    # Handle buy signal
            if current_signal == 1:
                logging.debug(f"Buy signal detected, executing long at close={current_price}")
                self.entry_price = current_price
                if self.position:
                    if self.position.is_short:
                        logging.debug("Closing short position before opening long")
                        self.position.close()
                    elif self.position.is_long:
                        logging.debug("Already in long position, no action needed")
                        return
                self.buy()  # Execute long position

            # Handle sell signal
            if current_signal == -1:
                logging.debug(f"Sell signal detected, executing short at close={current_price}")
                self.entry_price = current_price
                if self.position:
                    if self.position.is_long:
                        logging.debug("Closing long position before opening short")
                        self.position.close()
                    elif self.position.is_short:
                        logging.debug("Already in short position, no action needed")
                        return
                self.sell()  # Execute short position

                    
            
                    
                    
        except Exception as e:
            logging.error(f"Error in next method: {e}")
            raise





# Main script execution
try:
    # Load and prepare data
    data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi_strategy_backtest/0.DATA/BTCUSDT/spot/ohlc_data/2023_2024/btc_day_data_2023_2024/btc_day_data_2023_2024.csv'
    minute_data = load_and_prepare_data(data_path)
   
    daily_data = calculate_daily_indicators(minute_data)
    daily_signals = generate_signals(daily_data)
    
    # Run backtest
    bt = Backtest(daily_signals, ChandeKrollStopStrategy, cash=1000000, commission=.002)
    stats = bt.run()
    logging.info(stats)
    logging.info("Backtest complete")

    # Convert the trades to a DataFrame
    trades = stats['_trades']  # Accessing the trades DataFrame from the stats object

    # Save the trades to a CSV file
    trades_csv_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi_strategy_backtest/1.STATISTICAL_AND_PROBABILITY_BASED/1.fmz_pinescript_strategies_backtest/Trademaster_fmz_30_strategies/tradebook/29_ChandeKrollStopStrategy_backtest_trades.csv'
    trades.to_csv(trades_csv_path)

    logging.info(f"Trades have been exported to {trades_csv_path}")

except Exception as e:
    logging.error(f"Error in main script execution: {e}")
