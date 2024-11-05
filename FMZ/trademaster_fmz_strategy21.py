import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
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
class TRMUSStrategy(Strategy):
    # Strategy parameters
    ma_length = 50
    atr_length = 14
    multiplier = 1.5
    length = 20
    stop_loss_perc = 0.02
    take_profit_perc = 0.04
    
    def init(self):
        # Calculate Simple Moving Average (SMA)
        self.ma = self.I(
            lambda x: pd.Series(x).rolling(window=self.ma_length).mean().fillna(0).values,
            self.data.Close
        )
        
        # Calculate ATR using pandas_ta
        self.atr = self.I(
            lambda high, low, close: ta.atr(
                pd.Series(high), pd.Series(low), pd.Series(close), length=self.atr_length
            ).fillna(0).values,
            self.data.High, self.data.Low, self.data.Close
        )
        
        # Calculate Alpha Trend levels
        self.upperLevel = self.I(
            lambda close, atr: close + (self.multiplier * atr),
            self.data.Close, self.atr
        )
        self.lowerLevel = self.I(
            lambda close, atr: close - (self.multiplier * atr),
            self.data.Close, self.atr
        )
        
        # Calculate highest and lowest close over the specified window
        self.highestClose = self.I(
            lambda x: pd.Series(x).rolling(window=self.length).max().fillna(0).values,
            self.data.Close
        )
        self.lowestClose = self.I(
            lambda x: pd.Series(x).rolling(window=self.length).min().fillna(0).values,
            self.data.Close
        )
        
        # Initialize alphaTrend as a state variable
        self.alpha_trend = np.nan
        
    def next(self):
        # Current index
        i = len(self.data) - 1
        
        # Ensure we have enough data
        if i < self.ma_length + self.length - 1:
            return
        
        # Current and previous prices
        current_close = self.data.Close[-1]
        previous_close = self.data.Close[-2]
        
        # Current indicator values
        current_upper = self.upperLevel[-1]
        current_lower = self.lowerLevel[-1]
        current_highest_close = self.highestClose[-1]
        current_lowest_close = self.lowestClose[-1]
        current_ma = self.ma[-1]
        current_atr = self.atr[-1]
        
        # Update alpha_trend
        if np.isnan(self.alpha_trend):
            self.alpha_trend = current_close
        else:
            # Previous upper and lower levels
            previous_upper = self.upperLevel[-2]
            previous_lower = self.lowerLevel[-2]
            
            if current_close > previous_lower:
                self.alpha_trend = max(self.alpha_trend, current_lower)
            elif current_close < previous_upper:
                self.alpha_trend = min(self.alpha_trend, current_upper)
            # Else, alpha_trend remains unchanged
        
        # Generate buy and sell signals
        # Buy signal
        buy_signal = (
            (current_close > self.highestClose[-2]) and
            (previous_close <= self.highestClose[-2]) and
            (current_close > current_ma) and
            (current_close > self.alpha_trend)
        )
        
        # Sell signal
        sell_signal = (
            (current_close < self.lowestClose[-2]) and
            (previous_close >= self.lowestClose[-2]) and
            (current_close < current_ma) and
            (current_close < self.alpha_trend)
        )
        
        # Execute trades based on signals
        if buy_signal:
            # Close existing short position if any
            if self.position and self.position.is_short:
                self.position.close()
            # Buy with stop loss and take profit
            sl = current_close * (1 - self.stop_loss_perc)
            tp = current_close * (1 + self.take_profit_perc)
            self.buy(sl=sl, tp=tp)
        
        elif sell_signal:
            # Close existing long position if any
            if self.position and self.position.is_long:
                self.position.close()
            # Sell with stop loss and take profit
            sl = current_close * (1 + self.stop_loss_perc)
            tp = current_close * (1 - self.take_profit_perc)
            self.sell(sl=sl, tp=tp)




data = load_data(data_path)

bt = Backtest(data,TRMUSStrategy, cash=100000, commission=.002, exclusive_orders=True)



stats = bt.run()
print(stats)

# bt.plot(superimpose=False)