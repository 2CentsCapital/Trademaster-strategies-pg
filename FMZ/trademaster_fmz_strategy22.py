import pandas as pd
import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
import pandas_ta as ta





data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi/1.STATISTICAL_BASED/0.DATA/BTCUSDT/future/ohlc_data/2023_2024/btc_day_data_2023_2024/btc_day_data_2023_2024.csv'


def calculate_vwap(close, high, low, volume, window=14):
    typical_price = (high + low + close) / 3
    typical_price_volume = typical_price * volume
    cumulative_typical_price_volume = pd.Series(typical_price_volume).rolling(window=window).sum().fillna(0)
    cumulative_volume = pd.Series(volume).rolling(window=window).sum().fillna(0)
    vwap = cumulative_typical_price_volume / cumulative_volume
    return vwap.values


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

class VWAPStrategy(Strategy):
    # Strategy parameters
    vwap_window = 14
    stop_loss_perc = 0.02  # 2% Stop Loss
    take_profit_perc = 0.04  # 4% Take Profit
    
    def init(self):
        # Calculate VWAP
        self.vwap = self.I(
            calculate_vwap, 
            self.data.Close, 
            self.data.High, 
            self.data.Low, 
            self.data.Volume, 
            window=self.vwap_window
        )
        
        # Initialize variables for trade management
        self.entry_price = None
        self.long_profit_target = None
        self.short_profit_target = None
    
    def next(self):
        # Ensure VWAP is calculated
        if len(self.vwap) < self.vwap_window:
            return
        
        # Current and previous prices and VWAP
        current_close = self.data.Close[-1]
        previous_close = self.data.Close[-2]
        current_vwap = self.vwap[-1]
        previous_vwap = self.vwap[-2]
        
        # Generate buy/sell signals based on VWAP crossover
        buy_signal = (
            (current_close > current_vwap) and
            (previous_close <= previous_vwap)
        )
        
        sell_signal = (
            (current_close < current_vwap) and
            (previous_close >= previous_vwap)
        )
        
        # Execute buy signal
        if buy_signal:
            # Close existing short position if any
            if self.position and self.position.is_short:
                self.position.close()
            
            # Enter long position with Stop Loss and Take Profit
            self.buy(
                sl=current_close * (1 - self.stop_loss_perc),
                tp=current_close * (1 + self.take_profit_perc)
            )
            self.entry_price = current_close
            self.long_profit_target = current_close * (1 + self.take_profit_perc)
        
        # Execute sell signal
        elif sell_signal:
            # Close existing long position if any
            if self.position and self.position.is_long:
                self.position.close()
            
            # Enter short position with Stop Loss and Take Profit
            self.sell(
                sl=current_close * (1 + self.stop_loss_perc),
                tp=current_close * (1 - self.take_profit_perc)
            )
            self.entry_price = current_close
            self.short_profit_target = current_close * (1 - self.take_profit_perc)
        
        # Managing long position (take profit)
        if self.position.is_long and self.long_profit_target:
            if current_close >= self.long_profit_target:
                self.position.close()
                self.long_profit_target = None
        
        # Managing short position (take profit)
        if self.position.is_short and self.short_profit_target:
            if current_close <= self.short_profit_target:
                self.position.close()
                self.short_profit_target = None




data = load_data(data_path)

bt = Backtest(data, VWAPStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)