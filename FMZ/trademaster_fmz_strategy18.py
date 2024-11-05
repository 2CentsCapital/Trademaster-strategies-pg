import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
import pandas_ta as ta
from backtesting.lib import crossover
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

# Strategy Class
class BollingerBandsStochasticRSI(Strategy):
    # Parameters (can be optimized)
    bollinger_length = 20
    bollinger_mult = 2.0
    stochrsi_rsi_length = 14
    stochrsi_stoch_length = 14
    stochrsi_smooth_k = 3
    stochrsi_smooth_d = 3
    upper_limit = 90
    lower_limit = 10
    risk_per_trade = 2.0  # Percentage risk per trade
    
    def init(self):
     
        
        # Bollinger Bands
        self.basis = self.I(ta.sma, pd.Series(self.data.Close), self.bollinger_length)
        self.stddev = self.I(ta.stdev, pd.Series(self.data.Close), self.bollinger_length)
        self.upper = self.basis + self.bollinger_mult * self.stddev
        self.lower = self.basis - self.bollinger_mult * self.stddev
        
        # Stochastic RSI
        self.stoch_rsi = self.I(ta.stochrsi, pd.Series(self.data.Close), 
                                length=self.stochrsi_rsi_length, 
                                rsi_length=self.stochrsi_stoch_length, 
                                k=self.stochrsi_smooth_k, 
                                d=self.stochrsi_smooth_d)

        print("stochrsi_rsi",self.stoch_rsi)
        # Extract %K and %D from Stochastic RSI
        self.stoch_k = self.stoch_rsi[0]
        self.stoch_d = self.stoch_rsi[1]
        
        # Initialize stop loss and take profit levels
        self.stop_loss = None
        self.take_profit = None
          # ATR calculation using self.I()
        self.atr = self.I(ta.atr, pd.Series(self.data.High), pd.Series(self.data.Low), pd.Series(self.data.Close), length=14)
        

    def next(self):
        # Current index
        i = len(self.data) - 1
        
        # Ensure we have enough data
        if i < 1:
            return
        
        # Current and previous prices
        current_close = self.data.Close[-1]
        previous_close = self.data.Close[-2]
        
        # Current indicator values
        current_upper = self.upper[-1]
        current_lower = self.lower[-1]
        current_basis = self.basis[-1]
        
        current_stoch_k = self.stoch_k[-1]
        current_stoch_d = self.stoch_d[-1]
        
        previous_upper = self.upper[-2]
        previous_lower = self.lower[-2]
        previous_stoch_k = self.stoch_k[-2]
        previous_stoch_d = self.stoch_d[-2]
        
        # Define Bear and Bull conditions
        bear_condition = (
            (previous_close > previous_upper) &
            (current_close < current_upper) &
            (previous_stoch_k > self.upper_limit) &
            (previous_stoch_d > self.upper_limit)
        )
        
        bull_condition = (
            (previous_close < previous_lower) &
            (current_close > current_lower) &
            (previous_stoch_k < self.lower_limit) &
            (previous_stoch_d < self.lower_limit)
        )
        
        # Initialize signal
        signal = 0
        
        if bear_condition:
            signal = 1  # Enter Short
            
        elif bull_condition:
            signal = -1  # Enter Long
            
        
        # Execute trades based on signals
        if signal == 1:
            # Enter Short Position
            self.enter_short(current_close)
        
        elif signal == -1:
            # Enter Long Position
            self.enter_long(current_close)
    
    def enter_long(self, price):
        # Calculate ATR for stop loss distance

        atr = self.atr[-1]
        candle_body = abs(self.data.Close[-1] - self.data.Open[-1])
        sl_dist = atr + candle_body
        stop_loss = price - sl_dist
        take_profit = price + (sl_dist * 1.2)
        
        # Ensure stop_loss < price < take_profit
        if stop_loss >= price:
            stop_loss = price - 0.0001  # Adjust to be slightly below
        if take_profit <= price:
            take_profit = price + 0.0001  # Adjust to be slightly above
        
        # Close existing short position if any
        if self.position.is_short:
           self.position.close()
        
        # Place Buy Order with Stop Loss and Take Profit
        self.buy(sl=stop_loss, tp=take_profit)
       
    
    def enter_short(self, price):
        # Calculate ATR for stop loss distance
    
        atr = self.atr[-1]
        candle_body = abs(self.data.Close[-1] - self.data.Open[-1])
        sl_dist = atr + candle_body
        stop_loss = price + sl_dist
        take_profit = price - (sl_dist * 1.2)
        
        # Ensure take_profit < price < stop_loss
        if take_profit >= price:
            take_profit = price - 0.0001  # Adjust to be slightly below
        if stop_loss <= price:
            stop_loss = price + 0.0001  # Adjust to be slightly above
        
        # Close existing long position if any
        if self.position.is_long:
           self.position.close()
        
        # Place Sell Order with Stop Loss and Take Profit
        self.sell(sl=stop_loss, tp=take_profit)
       






data = load_data(data_path)

bt = Backtest(data, BollingerBandsStochasticRSI, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)