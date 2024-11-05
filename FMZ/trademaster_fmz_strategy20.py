import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
import pandas_ta as ta



data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi/1.STATISTICAL_BASED/0.DATA/BTCUSDT/future/ohlc_data/2023_2024/btc_day_data_2023_2024/btc_day_data_2023_2024.csv'



# Helper functions for indicator calculations
def rolling_max(x, window):
    return pd.Series(x).rolling(window=window).max().fillna(0).values

def rolling_min(x, window):
    return pd.Series(x).rolling(window=window).min().fillna(0).values

def calculate_rsv(close, low, high):
    with np.errstate(divide='ignore', invalid='ignore'):
        rsv = 100 * (pd.Series(close) - pd.Series(low)) / (pd.Series(high) - pd.Series(low))
        rsv = rsv.replace([np.inf, -np.inf], 0).fillna(0)
    return rsv.values

def rolling_mean(x, window):
    return pd.Series(x).rolling(window=window).mean().fillna(0).values

def calculate_j(k, d):
    j = 3 * pd.Series(k) - 2 * pd.Series(d)
    j = j.fillna(0).values
    return j

# Function to load data from CSV
def load_data(csv_file_path):
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
    
    return data

# Strategy Class
class TrendStructureBreakStrategy(Strategy):
    # Strategy parameters (can be optimized)
    kdj_length = 9
    kdj_signal = 3
    ma_length = 20
    kdj_overbought = 80
    kdj_oversold = 20
    atr_length = 14
    reward_to_risk_ratio = 1.2
    max_sl_dist_ratio = 0.1  # Max SL distance as a fraction of price (e.g., 10%)

    def init(self):
        # KDJ Indicators
        self.kdj_highest = self.I(rolling_max, self.data.High, self.kdj_length)
        self.kdj_lowest = self.I(rolling_min, self.data.Low, self.kdj_length)
        self.kdj_rsv = self.I(calculate_rsv, self.data.Close, self.kdj_lowest, self.kdj_highest)
        self.k = self.I(rolling_mean, self.kdj_rsv, self.kdj_signal)
        self.d = self.I(rolling_mean, self.k, self.kdj_signal)
        self.j = self.I(calculate_j, self.k, self.d)
        
        # Moving Average
        self.ma = self.I(rolling_mean, self.data.Close, self.ma_length)
        
        # ATR for Risk Management
        self.atr = self.I(
            lambda high, low, close: ta.atr(
                pd.Series(high), pd.Series(low), pd.Series(close), length=self.atr_length
            ).fillna(0).values,
            self.data.High, self.data.Low, self.data.Close
        )
        
    def next(self):
        # Current index
        i = len(self.data) - 1
        
        # Ensure we have enough data
        if i < self.kdj_length + self.kdj_signal - 1:
            return
        
        # Current and previous prices
        current_close = self.data.Close[-1]
        previous_close = self.data.Close[-2]
        
        # Current indicator values
        current_j = self.j[-1]
        previous_j = self.j[-2]
        
        current_ma = self.ma[-1]
        previous_ma = self.ma[-2]
        
        # Define Bear and Bull conditions
        bear_condition = (
            (previous_close > previous_ma) &
            (current_close < current_ma) &
            (previous_j > self.kdj_overbought) &
            (current_j > self.kdj_overbought)
        )
        
        bull_condition = (
            (previous_close < previous_ma) &
            (current_close > current_ma) &
            (previous_j < self.kdj_oversold) &
            (current_j < self.kdj_oversold)
        )
        
        # Initialize signal
        signal = 0
        
        if bear_condition:
            signal = -1  # Enter Short
            # No logging
        
        elif bull_condition:
            signal = 1  # Enter Long
            # No logging
        
        # Execute trades based on signals
        if signal == 1:
            self.enter_long(current_close)
        
        elif signal == -1:
            self.enter_short(current_close)
    
    def enter_long(self, price):
        # Calculate ATR for stop loss distance
        atr = self.atr[-1]
        candle_body = abs(self.data.Close[-1] - self.data.Open[-1])
        sl_dist = atr + candle_body
        if sl_dist <= 0 or np.isnan(sl_dist):
            return  # Cannot proceed with invalid sl_dist
        
        # Calculate stop loss and take profit levels
        stop_loss = price - sl_dist  # Stop loss for long position
        take_profit = price + (sl_dist * self.reward_to_risk_ratio)  # Take profit for long position
        
        # Ensure stop_loss < price < take_profit
        if stop_loss >= price:
            stop_loss = price - 0.0001  # Adjust to be slightly below
        
        # Close existing short position if any
        if self.position and self.position.is_short:
            self.position.close()
        
        # Execute the buy order with stop loss and take profit
        self.buy(sl=stop_loss, tp=take_profit)
    
    def enter_short(self, price):
        # Calculate ATR for stop loss distance
        atr = self.atr[-1]
        candle_body = abs(self.data.Close[-1] - self.data.Open[-1])
        sl_dist = atr + candle_body
        if sl_dist <= 0 or np.isnan(sl_dist):
            return  # Cannot proceed with invalid sl_dist
        
        # Limit sl_dist to prevent unrealistic values (e.g., max 10% of current price)
        max_sl_dist = price * self.max_sl_dist_ratio
        if sl_dist > max_sl_dist:
            sl_dist = max_sl_dist
        
        # Calculate stop loss and take profit levels
        stop_loss = price + sl_dist  # Stop loss for short position
        take_profit = price - (sl_dist * self.reward_to_risk_ratio)  # Take profit for short position
        
        # Ensure take_profit < price < stop_loss
        if take_profit >= price:
            take_profit = price - 0.0001  # Adjust to be slightly below
        if stop_loss <= price:
            stop_loss = price + 0.0001  # Adjust to be slightly above
        
        # Final validation to ensure correct ordering
        if not (take_profit < price < stop_loss):
            return  # Skip placing the order if the condition is not met
        
        # Close existing long position if any
        if self.position and self.position.is_long:
            self.position.close()
        
        # Execute the sell order with stop loss and take profit
        self.sell(sl=stop_loss, tp=take_profit)



data = load_data(data_path)

bt = Backtest(data, TrendStructureBreakStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)