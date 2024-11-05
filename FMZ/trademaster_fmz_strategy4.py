import pandas as pd
import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
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



def calculate_daily_indicators(data):


    # Calculate the 50-period Simple Moving Average (SMA)
    data['ma_50'] = ta.sma(data['Close'], length=50)

    # Calculate the 200-period Simple Moving Average (SMA)
    data['ma_200'] = ta.sma(data['Close'], length=200)


    # Define lengths
    len_21 = 21
    len_50 = 50
    len_9 = 9
    
    # Initialize Fibonacci levels with NaN
    data['fib_50_level'] = np.nan
    data['fib_786_level'] = np.nan
    
    # Calculate retracement levels only when close > MA_200 and close > MA_50
    condition = (data['Close'] > data['ma_200']) & (data['Close'] > data['ma_50'])
    
    data.loc[condition, 'retrace_21_high'] = data['High'].rolling(window=len_21).max()
    data.loc[condition, 'retrace_21_low'] = data['Low'].rolling(window=len_21).min()
    data.loc[condition, 'retrace_21_mid'] = (data['retrace_21_high'] + data['retrace_21_low']) / 2

    data.loc[condition, 'retrace_50_high'] = data['High'].rolling(window=len_50).max()
    data.loc[condition, 'retrace_50_low'] = data['Low'].rolling(window=len_50).min()
    data.loc[condition, 'retrace_50_mid'] = (data['retrace_50_high'] + data['retrace_50_low']) / 2

    data.loc[condition, 'retrace_9_high'] = data['High'].rolling(window=len_9).max()
    data.loc[condition, 'retrace_9_low'] = data['Low'].rolling(window=len_9).min()
    data.loc[condition, 'retrace_9_mid'] = (data['retrace_9_high'] + data['retrace_9_low']) / 2
    
    # Calculate the Fibonacci levels only for the filtered rows
    data.loc[condition, 'fib_50_level'] = (data['retrace_21_mid'] + data['retrace_50_mid'] + data['retrace_9_mid']) / 3
        # Apply the calculation for 'fib_786_level' directly to the DataFrame
    data.loc[condition, 'fib_786_level'] = (
        (data.loc[condition, 'retrace_21_high'] + data.loc[condition, 'retrace_50_high'] + data.loc[condition, 'retrace_9_high']) / 3 -
        ((data.loc[condition, 'retrace_21_high'] + data.loc[condition, 'retrace_50_high'] + data.loc[condition, 'retrace_9_high'] - 
        data.loc[condition, 'retrace_21_low'] - data.loc[condition, 'retrace_50_low'] - data.loc[condition, 'retrace_9_low']) * 0.786)
    )
    return data.dropna()
def generate_signals(daily_data):
    try:
        print("Generating signals based on strategy logic")
        daily_data['long_condition'] = (
            (daily_data['Close'] > daily_data['ma_200']) &
            (daily_data['Close'] > daily_data['ma_50']) &
            (daily_data['Close'] <= daily_data['fib_50_level'])
        )

        daily_data['signal'] = np.where(daily_data['long_condition'], 1, 0)
        print("Signal generation complete")
        return daily_data
    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise

class RetracementStrategy(Strategy):
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
            latest_close = self.data.Close[-1]
            latest_signal = self.data.signal[-1]
            # print(f"Processing bar: {self.data.index[-1]} with signal {latest_signal} at price {latest_close}")

            if latest_signal == 1 :
                print(f"Buy signal detected, close={latest_close}")
                self.entry_price = latest_close
                risk_reward_ratio = 2.0
                take_profit_level = self.entry_price + (self.entry_price - self.data.fib_786_level[-1]) * risk_reward_ratio
                stop_loss_level = self.data.fib_786_level[-1]
                # if self.position():
                #      self.position().close()

                self.buy(sl=stop_loss_level,tp= take_profit_level)

                    
                       
                   
           
        except Exception as e:
            print(f"Error in next method: {e}")
            raise





data = load_data(data_path)
data= calculate_daily_indicators(data)
data = generate_signals(data)
bt = Backtest(data, RetracementStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

bt.plot(superimpose=False)