import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
import logging
import coloredlogs
import pandas_ta as ta
from backtesting.lib import crossover

data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023_2024.csv'



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
class CombinedScalpingSwingStrategy(Strategy):
    def init(self):
        # Parameters for indicators
        lengthBB = 20
        multBB = 2.0
        lengthKC = 20
        multKC = 1.5
        use_true_range = True
        
        close = pd.Series(self.data.Close)
        
        # Calculate Moving Averages
        self.ShortScalpMA = self.I(ta.ema, close, 5)
        self.LongScalpMA = self.I(ta.ema, close, 15)
        self.ShortSwingMA = self.I(ta.sma, close, 20)
        self.LongSwingMA = self.I(ta.sma, close, 50)

        # Calculate MACD
        macd = self.I(ta.macd, close)
        self.MACDLine = macd[0]
        self.SignalLine = macd[1]
        self.MACDHist = macd[2]

        # Calculate Bollinger Bands
        self.basisBB = self.I(ta.sma, close, lengthBB)
        self.devBB = self.I(ta.stdev, close, lengthBB)
        self.BollingerUpper = self.I(lambda b, d: b + multBB * d, self.basisBB, self.devBB)
        self.BollingerLower = self.I(lambda b, d: b - multBB * d, self.basisBB, self.devBB)

        # Calculate Keltner Channels
        self.tr = self.I(lambda h, l, c: pd.concat([
            pd.Series(h) - pd.Series(l),
            (pd.Series(h) - pd.Series(c).shift(1)).abs(),
            (pd.Series(l) - pd.Series(c).shift(1)).abs()
        ], axis=1).max(axis=1), pd.Series(self.data.High), pd.Series(self.data.Low), pd.Series(close))
        
        self.maKC = self.I(ta.sma, close, lengthKC)

        # Convert the _Indicator (rangeKC) to a Series before applying rolling
        self.rangeKC = pd.Series(self.tr) if use_true_range else pd.Series(self.data.High - self.data.Low)
        self.rangeKCMA = self.I(lambda r: pd.Series(r).rolling(window=lengthKC).mean(), self.rangeKC)
        
        self.KeltnerUpper = self.I(lambda b, r: b + r * multKC, self.maKC, self.rangeKCMA)
        self.KeltnerLower = self.I(lambda b, r: b - r * multKC, self.maKC, self.rangeKCMA)

        # Calculate Momentum Value
        self.highest_high = self.I(lambda h: pd.Series(h).rolling(lengthKC).max(), self.data.High)
        self.lowest_low = self.I(lambda l: pd.Series(l).rolling(lengthKC).min(), self.data.Low)
        self.avgPrice = self.I(lambda hh, ll: (hh + ll) / 2, self.highest_high, self.lowest_low)
        self.MomentumValue = self.I(ta.linreg, pd.Series(close) - self.avgPrice, lengthKC, 0)

        # Squeeze condition
        self.SqueezeOn = self.I(lambda b_low, k_low, b_up, k_up: (b_low > k_low) & (b_up < k_up), self.BollingerLower, self.KeltnerLower, self.BollingerUpper, self.KeltnerUpper)
        self.SqueezeOff = self.I(lambda b_low, k_low, b_up, k_up: (b_low < k_low) & (b_up > k_up), self.BollingerLower, self.KeltnerLower, self.BollingerUpper, self.KeltnerUpper)

        self.last_position_type = None  # To track last position type


    def next(self):
        # Scalp Buy Signal: ShortScalpMA crosses above LongScalpMA
        scalpBuySignal = self.ShortScalpMA[-2] < self.LongScalpMA[-2] and self.ShortScalpMA[-1] > self.LongScalpMA[-1]
        
        # Scalp Sell Signal: ShortScalpMA crosses below LongScalpMA
        scalpSellSignal = self.ShortScalpMA[-2] > self.LongScalpMA[-2] and self.ShortScalpMA[-1] < self.LongScalpMA[-1]
        
        # Swing Buy Signal: ShortSwingMA crosses above LongSwingMA
        swingBuySignal = self.ShortSwingMA[-2] < self.LongSwingMA[-2] and self.ShortSwingMA[-1] > self.LongSwingMA[-1]
        
        # Swing Sell Signal: ShortSwingMA crosses below LongSwingMA
        swingSellSignal = self.ShortSwingMA[-2] > self.LongSwingMA[-2] and self.ShortSwingMA[-1] < self.LongSwingMA[-1]

        # Squeeze and Momentum conditions
        noSqueeze = not self.SqueezeOn[-1] and not self.SqueezeOff[-1]
        momentum_positive = self.MomentumValue[-1] > 0
        momentum_negative = self.MomentumValue[-1] < 0

        # Execute strategy logic
        if scalpBuySignal and not noSqueeze and momentum_positive:
            self.buy()
            self.last_position_type = 'scalp'
        
        elif scalpSellSignal and not noSqueeze and momentum_negative and self.last_position_type == 'scalp':
            self.position.close()
            self.last_position_type = None
        
        elif swingBuySignal and not noSqueeze and momentum_positive:
            self.buy()
            self.last_position_type = 'swing'
        
        elif swingSellSignal and not noSqueeze and momentum_negative and self.last_position_type == 'swing':
            self.position.close()
            self.last_position_type = None

data = load_data(data_path)

bt = Backtest(data, CombinedScalpingSwingStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)