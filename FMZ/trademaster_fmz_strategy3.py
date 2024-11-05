import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import logging
import coloredlogs
import pandas_ta as ta

#refer strategy 21 -for seeing buy and sell function same like

# Set up logging
log_file_path = '/Users/pranaygaurav/Downloads/AlgoTrading/0.2centscapital/P3/FMZ/fmz_strategies/my_Tradebook/3_bonk_trading_strategy.log'

logging.basicConfig(level=logging.DEBUG, filename=log_file_path, filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

coloredlogs.install(level='DEBUG',
                    fmt='%(asctime)s - %(levelname)s - %(message)s',
                    level_styles={
                        'info': {'color': 'green'},
                        'debug': {'color': 'white'},
                        'error': {'color': 'red'},
                    })

def load_and_prepare_data(csv_file_path):
    try:
        logging.info("Loading data from CSV")
        data = pd.read_csv(csv_file_path)
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data.set_index('timestamp', inplace=True)
        data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        logging.info("Data loading and preparation complete")
        return data
    except Exception as e:
        logging.error(f"Error in load_and_prepare_data: {e}")
        raise

def calculate_daily_indicators(daily_data):
    try:
        logging.info("Resampling data to daily timeframe for indicator calculation")
        # daily_data = data.resample('D').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()

        logging.info("Calculating EMA, MACD, RSI, and Volume indicators on daily data")
        daily_data['ema_short'] = ta.ema(daily_data['Close'], length=9)
        daily_data['ema_long'] = ta.ema(daily_data['Close'], length=20)
        macd = ta.macd(daily_data['Close'], fast=12, slow=26, signal=9)
        daily_data['macd_line'] = macd['MACD_12_26_9']
        daily_data['signal_line'] = macd['MACDs_12_26_9']
        daily_data['rsi'] = ta.rsi(daily_data['Close'], length=14)
        daily_data['volume_ma'] = ta.sma(daily_data['Volume'], length=20)

        
        daily_data.dropna(inplace=True)
        logging.info(f"Daily indicator calculation complete\n{daily_data.head(20)}")
        return daily_data
    except Exception as e:
        logging.error(f"Error in calculate_daily_indicators: {e}")
        raise



def generate_signals(daily_data):
    try:
        logging.info("Generating signals based on strategy logic")

        # Initialize signal column
        daily_data['signal'] = 0
        
        # Iterate through the data to manually check for crossovers
        for i in range(1, len(daily_data)):
            prev_ema_short = daily_data['ema_short'].iloc[i-1]
            prev_ema_long = daily_data['ema_long'].iloc[i-1]
            current_ema_short = daily_data['ema_short'].iloc[i]
            current_ema_long = daily_data['ema_long'].iloc[i]
            current_macd_line = daily_data['macd_line'].iloc[i]
            current_signal_line = daily_data['signal_line'].iloc[i]
            current_rsi = daily_data['rsi'].iloc[i]
            current_volume = daily_data['Volume'].iloc[i]
            volume_ma = daily_data['volume_ma'].iloc[i]
            
            buy_condition = (
                prev_ema_short <= prev_ema_long and
                current_ema_short > current_ema_long and
                current_macd_line > current_signal_line and
                current_rsi < 70 and
                current_volume > volume_ma
            )
            
            sell_condition = (
                prev_ema_long <= prev_ema_short and
                current_ema_long > current_ema_short and
                current_macd_line < current_signal_line and
                current_rsi > 30 and
                current_volume > volume_ma
            )
            
            if buy_condition:
                daily_data['signal'].iloc[i] = 1
            elif sell_condition:
                daily_data['signal'].iloc[i] = -1

        logging.info("Signal generation complete")
        return daily_data
    except Exception as e:
        logging.error(f"Error in generate_signals: {e}")
        raise


class BONKTradingStrategy(Strategy):
    def init(self):
        try:
            logging.info("Initializing strategy")
            self.entry_price = None
            logging.info("Strategy initialization complete")
        except Exception as e:
            logging.error(f"Error in init method: {e}")
            raise


    def next(self):
        try:
            # logging.debug(f"Processing bar: {self.data.index[-1]} with signal {self.data.signal[-1]} at price {self.data.Close[-1]}")
            if self.data.signal[-1] == 1:
                logging.debug(f"Buy signal detected, close={self.data.Close[-1]}")
                self.entry_price = self.data.Close[-1]
                long_stop_loss = self.entry_price * 0.95
                long_take_profit = self.entry_price * 1.05
                if self.position:
                    if self.position.is_short:
                        logging.debug("Closing short position before opening long")
                        self.position.close()
                    elif self.position.is_long:
                        logging.debug("Already in long position, no action needed")
                        return
                self.buy(stop=long_stop_loss,limit=long_take_profit)
                
            elif self.data.signal[-1] == -1 :
                logging.debug(f"Sell signal detected, close={self.data.Close[-1]}")
                self.entry_price = self.data.Close[-1]
                short_stop_loss = self.entry_price * 1.05
                short_take_profit = self.entry_price * 0.95
                if self.position:
                    if self.position.is_long:
                        logging.debug("Closing long position before opening short")
                        self.position.close()
                    elif self.position.is_short:
                        logging.debug("Already in short position, no action needed")
                        return
                self.sell(stop=short_stop_loss,limit=short_take_profit)

      
        except Exception as e:
            logging.error(f"Error in next method: {e}")
            raise

try:
    data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023_2024.csv'
    # logging.info(f"Minute data:\n{minute_data.head(20)}")
    minute_data = load_and_prepare_data(data_path)
    daily_data = calculate_daily_indicators(minute_data)
    daily_signals = generate_signals(daily_data)
   
    bt = Backtest(daily_signals, BONKTradingStrategy, cash=1000000, commission=.002)
    stats = bt.run()
  
    logging.info(stats)
    logging.info("Backtest complete")

    trades = stats['_trades']
    trades.to_csv('/Users/pranaygaurav/Downloads/AlgoTrading/0.2centscapital/P3/FMZ/fmz_strategies/my_Tradebook/3_bonk_trading_strategy_trades.csv')

except Exception as e:
    logging.error(f"Error during strategy execution: {e}")
    raise