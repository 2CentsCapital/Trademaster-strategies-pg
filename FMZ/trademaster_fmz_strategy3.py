import pandas as pd
import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover

import pandas_ta as ta

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
        print("Resampling data to daily timeframe for indicator calculation")
        # daily_data = data.resample('D').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()

        print("Calculating EMA, MACD, RSI, and Volume indicators on daily data")
        daily_data['ema_short'] = ta.ema(daily_data['Close'], length=9)
        daily_data['ema_long'] = ta.ema(daily_data['Close'], length=20)
        macd = ta.macd(daily_data['Close'], fast=12, slow=26, signal=9)
        daily_data['macd_line'] = macd['MACD_12_26_9']
        daily_data['signal_line'] = macd['MACDs_12_26_9']
        daily_data['rsi'] = ta.rsi(daily_data['Close'], length=14)
        daily_data['volume_ma'] = ta.sma(daily_data['Volume'], length=20)

        
        daily_data.dropna(inplace=True)
        print(f"Daily indicator calculation complete\n{daily_data.head(20)}")
        return daily_data
    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise

# def generate_signals(daily_data):
#     try:
#         print("Generating signals based on strategy logic")

#         daily_data['buy_condition'] = (
#             crossover(daily_data['ema_short'], daily_data['ema_long']) &
#             (daily_data['macd_line'] > daily_data['signal_line']) &
#             (daily_data['rsi'] < 70) &
#             (daily_data['Volume'] > daily_data['volume_ma'])
#         )

#         daily_data['sell_condition'] = (
#             crossover(daily_data['ema_long'], daily_data['ema_short']) &
#             (daily_data['macd_line'] < daily_data['signal_line']) &
#             (daily_data['rsi'] > 30) &
#             (daily_data['Volume'] > daily_data['volume_ma'])
#         )

#         daily_data['signal'] = np.where(daily_data['buy_condition'], 1, np.where(daily_data['sell_condition'], -1, 0))

#         print("Signal generation complete")
#         return daily_data
#     except Exception as e:
#         print(f"Error in generate_signals: {e}")
#         raise

def generate_signals(daily_data):
    try:
        print("Generating signals based on strategy logic")

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

        print("Signal generation complete")
        return daily_data
    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise


class BONKTradingStrategy(Strategy):
    def init(self):
        try:
            print("Initializing strategy")
            self.entry_price = None
            print("Strategy initialization complete")
        except Exception as e:
            print(f"Error in init method: {e}")
            raise


    def next(self):
        try:
            # print(f"Processing bar: {self.data.index[-1]} with signal {self.data.signal[-1]} at price {self.data.Close[-1]}")
            if self.data.signal[-1] == 1:
                print(f"Buy signal detected, close={self.data.Close[-1]}")
                self.entry_price = self.data.Close[-1]
                long_stop_loss = self.entry_price * 0.95
                long_take_profit = self.entry_price * 1.05
                if self.position():
                    if self.position().is_short:
                        print("Closing short position before opening long")
                        self.position().close()
                    elif self.position().is_long:
                        print("Already in long position, no action needed")
                        return
                self.buy(stop=long_stop_loss,limit=long_take_profit)
                
            elif self.data.signal[-1] == -1 :
                print(f"Sell signal detected, close={self.data.Close[-1]}")
                self.entry_price = self.data.Close[-1]
                short_stop_loss = self.entry_price * 1.05
                short_take_profit = self.entry_price * 0.95
                if self.position():
                    if self.position().is_long:
                        print("Closing long position before opening short")
                        self.position().close()
                    elif self.position().is_short:
                        print("Already in short position, no action needed")
                        return
                self.sell(stop=short_stop_loss,limit=short_take_profit)

      
        except Exception as e:
            print(f"Error in next method: {e}")
            raise




data = load_data(data_path)
data= calculate_daily_indicators(data)
data = generate_signals(data)
bt = Backtest(data, BONKTradingStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)