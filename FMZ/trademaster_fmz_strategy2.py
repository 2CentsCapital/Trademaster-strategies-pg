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



import pandas as pd
import pandas_ta as ta
from backtesting import Backtest, Strategy

# Function to load data from CSV
def load_data(csv_file_path):
    data = pd.read_csv(csv_file_path)
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data.set_index('timestamp', inplace=True)
    data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
    return data





def calculate_daily_indicators(df):
    # Calculate the required indicators
    df['SMA01'] = ta.sma(df['Close'], length=3)
    df['SMA02'] = ta.sma(df['Close'], length=8)
    df['SMA03'] = ta.sma(df['Close'], length=10)
    df['EMA01'] = ta.ema(df['Close'], length=5)
    df['EMA02'] = ta.ema(df['Close'], length=3)
    df['OHLC'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4.0

    # Ensure no NaN values from indicator calculations
    df.dropna(inplace=True)

    return df

def generate_signals(df):
    # Initialize signal columns
    df['signal'] = 0

    # Entry01 conditions
    df['Cond01'] = df['Close'] < df['SMA03']
    df['Cond02'] = df['Close'] <= df['SMA01']
    df['Cond03'] = df['Close'].shift(1) > df['SMA01'].shift(1)
    df['Cond04'] = df['Open'] > df['EMA01']
    df['Cond05'] = df['SMA02'] < df['SMA02'].shift(1)
    
    df['Entry01'] = df['Cond01'] & df['Cond02'] & df['Cond03'] & df['Cond04'] & df['Cond05']

    # Entry02 conditions
    df['Cond06'] = df['Close'] < df['EMA02']
    df['Cond07'] = df['Open'] > df['OHLC']
    df['Cond08'] = df['Volume'] <= df['Volume'].shift(1)

    # Fixing Cond09
    shifted_open = df['Open'].shift(1)
    shifted_close = df['Close'].shift(1)
    
    df['Cond09'] = (df['Close'] < shifted_open.combine(shifted_close, min)) | (df['Close'] > shifted_open.combine(shifted_close, max))
    
    df['Entry02'] = df['Cond06'] & df['Cond07'] & df['Cond08'] & df['Cond09']

    # Generate signals
    df['buy_condition'] = (df['Entry01'] | df['Entry02']).astype(int)

    # Update signal column where buy_condition is True (set to 1 for buy signal)
    df.loc[df['buy_condition'] == 1, 'signal'] = 1

    return df


class ComboStrategy(Strategy):
    def init(self):
        # Initialize variables
        self.BarsSinceEntry = None
        self.MaxProfitCount = 0  # Initialize MaxProfitCount as 0
        self.MaxBars = 10  # Maximum bars to hold position
        self.position_avg_price = None  # Track average price of the position

    def next(self):
        # Initialize BarsSinceEntry if it's the first bar of the strategy
        if self.BarsSinceEntry is None:
            self.BarsSinceEntry = 0

        # Cond00: Check if no position is open
        Cond00 = self.position.size == 0

        # Update BarsSinceEntry
        if Cond00:
            self.BarsSinceEntry = 0  # Reset BarsSinceEntry if no position
        else:
            # Increment BarsSinceEntry if there is an open position
            self.BarsSinceEntry += 1

          # Update BarsSinceEntry
        if Cond00:
             self.MaxProfitCount = 0  # Reset BarsSinceEntry if no position
        else:
              # If the current close price is greater than the average entry price and BarsSinceEntry > 1
            if self.data.Close[-1] > self.position_avg_price and self.BarsSinceEntry > 1:
                self.MaxProfitCount += 1  # Increment MaxProfitCount
                print(f"MaxProfitCount incremented: {self.MaxProfitCount}")

           

        # Check if we should enter a position based on signals
        if self.data.signal[-1] == 1 and self.position.size == 0:
            self.buy(size=1)
            self.position_avg_price = self.data.Close[-1]  # Store the entry price
           

        # Exit the position if BarsSinceEntry exceeds MaxBars or MaxProfitCount exceeds threshold
        if (self.BarsSinceEntry-1) >= self.MaxBars or self.MaxProfitCount >= 5:
            self.position.close()
            print(f"Position closed at {self.data.Close[-1]}")





data = load_data(data_path)
data= calculate_daily_indicators(data)
data = generate_signals(data)
bt = Backtest(data,ComboStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)

   


