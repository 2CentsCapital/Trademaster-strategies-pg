import pandas as pd
from backtesting import Strategy, Backtest
from backtesting.lib import crossover
import numpy as np
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

def calculate_daily_indicators(df):
    # Calculate VWAP
    df['ohlc4'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    df['sumSrc'] = (df['ohlc4'] * df['Volume']).cumsum()
    df['sumVol'] = df['Volume'].cumsum()
    df['vwapW'] = df['sumSrc'] / df['sumVol']
    
    # Custom calculation of source
    df['h'] = np.power(df['High'], 2) / 2
    df['l'] = np.power(df['Low'], 2) / 2
    df['o'] = np.power(df['Open'], 2) / 2
    df['c'] = np.power(df['Close'], 2) / 2
    df['source'] = np.sqrt((df['h'] + df['l'] + df['o'] + df['c']) / 4)
    
    # Moving Average and Range calculation
    length = 27
    mult = 0
    df['ma'] = df['source'].rolling(window=length).mean()
    df['range'] = df['High'] - df['Low']
    df['rangema'] = df['range'].rolling(window=length).mean()
    df['upper'] = df['ma'] + df['rangema'] * mult
    df['lower'] = df['ma'] - df['rangema'] * mult
    
    return df




def generate_signals(df):
    # Signal conditions based on indicator crossovers and VWAP conditions
    df['crossUpper'] = (df['source'] > df['upper']) & (df['source'].shift(1) <= df['upper'].shift(1))
    df['crossLower'] = (df['source'] < df['lower']) & (df['source'].shift(1) >= df['lower'].shift(1))
    
    df['bprice'] = np.where(df['crossUpper'], df['High'] + 0.01, np.nan)
    df['bprice'] = df['bprice'].fillna(method='ffill')
    
    df['sprice'] = np.where(df['crossLower'], df['Low'] - 0.01, np.nan)
    df['sprice'] = df['sprice'].fillna(method='ffill')
    
    df['crossBcond'] = df['crossUpper']
    df['crossBcond'] = np.where(df['crossBcond'].isna(), False, df['crossBcond'])
    
    df['crossScond'] = df['crossLower']
    df['crossScond'] = np.where(df['crossScond'].isna(), False, df['crossScond'])
    
    df['cancelBcond'] = df['crossBcond'] & ((df['source'] < df['ma']) | (df['High'] >= df['bprice']))
    df['cancelScond'] = df['crossScond'] & ((df['source'] > df['ma']) | (df['Low'] <= df['sprice']))
    
    # Long and short conditions based on VWAP
    df['longCondition'] = (df['Close'] > df['vwapW'])
    df['shortCondition'] = (df['Close'] < df['vwapW'])
    
    df['signal'] = 0
    df.loc[df['crossUpper'], 'signal'] = 1
    df.loc[df['crossLower'], 'signal'] = -1
    
    return df





# Strategy Class
class VWAPMTFStockStrategy(Strategy):
    def init(self):
        # Parameters
        length = 27
        mult = 0  # Multiplier as per your code

        # Access data
        open_ = self.data.Open
        high = self.data.High
        low = self.data.Low
        close = self.data.Close
        volume = self.data.Volume

        # Calculate VWAP
        ohlc4 = (open_ + high + low + close) / 4
        sum_src = (ohlc4 * volume).cumsum()
        sum_vol = volume.cumsum()
        self.vwapW = self.I(lambda: sum_src / sum_vol)

        # Custom calculation of source
        h = np.power(high, 2) / 2
        l = np.power(low, 2) / 2
        o = np.power(open_, 2) / 2
        c = np.power(close, 2) / 2
        source = np.sqrt((h + l + o + c) / 4)
        self.source = self.I(lambda: source)

        # Moving Average and Range calculation
        self.ma = self.I(lambda src: pd.Series(src).rolling(window=length).mean(), self.source)
        range_ = high - low
        self.rangema = self.I(lambda r: pd.Series(r).rolling(window=length).mean(), range_)
        self.upper = self.I(lambda ma, rangema: ma + rangema * mult, self.ma, self.rangema)
        self.lower = self.I(lambda ma, rangema: ma - rangema * mult, self.ma, self.rangema)

        # Initialize bprice and sprice
        self.bprice = np.nan
        self.sprice = np.nan

    def next(self):
        i = len(self.data) - 1  # Current index

        # Check if we have enough data
        if i < 1:
            return

        # Calculate crossovers
        cross_upper = (self.source[-1] > self.upper[-1]) and (self.source[-2] <= self.upper[-2])
        cross_lower = (self.source[-1] < self.lower[-1]) and (self.source[-2] >= self.lower[-2])

        # Update bprice and sprice based on crossovers
        if cross_upper:
            self.bprice = self.data.High[-1] + 0.01
        elif not np.isnan(self.bprice):
            self.bprice = self.bprice  # Keep previous value
        else:
            self.bprice = np.nan

        if cross_lower:
            self.sprice = self.data.Low[-1] - 0.01
        elif not np.isnan(self.sprice):
            self.sprice = self.sprice  # Keep previous value
        else:
            self.sprice = np.nan

        # Long and short conditions based on VWAP
        long_condition = self.data.Close[-1] > self.vwapW[-1]
        short_condition = self.data.Close[-1] < self.vwapW[-1]

        # Entry logic
        if cross_upper and long_condition and not self.position.is_long:
            self.buy(stop=self.bprice, sl=self.bprice * 0.99)  # Example stop loss at 1% below bprice

        elif cross_lower and short_condition and not self.position.is_short:
            self.sell(stop=self.sprice, sl=self.sprice * 1.01)  # Example stop loss at 1% above sprice

        # Exit logic for long positions
        if self.position.is_long:
            # Close long if source drops below ma or price hits stop loss
            if self.source[-1] < self.ma[-1]:
                self.position.close()
                self.bprice = np.nan  # Reset bprice

        # Exit logic for short positions
        if self.position.is_short:
            # Close short if source rises above ma or price hits stop loss
            if self.source[-1] > self.ma[-1]:
                self.position.close()
                self.sprice = np.nan  # Reset sprice

     






data = load_data(data_path)

bt = Backtest(data, VWAPMTFStockStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

# bt.plot(superimpose=False)