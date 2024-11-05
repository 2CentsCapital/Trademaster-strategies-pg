import pandas as pd
from backtesting import Backtest, Strategy
import pandas as pd
from backtesting.lib import crossover, TrailingStrategy
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)

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




class FukuizTradingStrategy(Strategy):
    n1 = 24  # RSI Short period
    n2 = 100  # RSI Long period
    lbR = 5
    lbL = 5
    rangeUpper = 60
    rangeLower = 5
    plotBull = True
    plotBear = True

    def init(self):
        self.rsi_short = self.I(self.rsi, self.data.Close, self.n1)
        self.rsi_long = self.I(self.rsi, self.data.Close, self.n2)
        self.signals = self.I(self.generate_signals)
        self.entry_price = None

    def ema(self, series, length):
        alpha = 2 / (length + 1)
        ema = np.zeros_like(series)
        ema[0] = series[0]
        for i in range(1, len(series)):
            ema[i] = alpha * series[i] + (1 - alpha) * ema[i - 1]
        return ema

    def rma(self, series, length):
        alpha = 1 / length
        return self.ema(series, 2 * length - 1)  # Approximation of RMA using EMA

    def rsi(self, series, length):
        delta = np.diff(series, prepend=series[0])
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = self.rma(gain, length)
        avg_loss = self.rma(loss, length)
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def generate_signals(self):
        signals = np.zeros(len(self.data))
        osc = self.rsi_short
        osc_long = self.rsi_long

        for i in range(self.lbR + self.lbL, len(self.data)):
            osc_window = osc[i - self.lbL - self.lbR:i + 1]

            plFound = osc_window[self.lbL] == np.min(osc_window)
            phFound = osc_window[self.lbL] == np.max(osc_window)

            oscHL = osc_window[-self.lbR] > osc_window[-(self.lbR + self.lbL)]
            priceLL = self.data.Low[i - self.lbR] < self.data.Low[i - (self.lbR + self.lbL)]
            bullCond = self.plotBull and priceLL and oscHL and plFound

            oscLH = osc_window[-self.lbR] < osc_window[-(self.lbR + self.lbL)]
            priceHH = self.data.High[i - self.lbR] > self.data.High[i - (self.lbR + self.lbL)]
            bearCond = self.plotBear and priceHH and oscLH and phFound

            if bullCond:
                signals[i] = 1
            elif bearCond:
                signals[i] = -1

        return signals

    def next(self):
        try:
            current_signal = self.signals[-1]
            current_price = self.data.Close[-1]

            if current_signal == 1:
                logging.debug(f"Buy signal detected at close={current_price}")
                self.entry_price = current_price
                if self.position.is_short:
                    self.position.close()
                self.buy()

            elif current_signal == -1:
                logging.debug(f"Sell signal detected at close={current_price}")
                self.entry_price = current_price
                if self.position.is_long:
                    self.position.close()
                self.sell()

        except Exception as e:
            logging.error(f"Error in next method: {e}")
            raise



try:
    # Load and prepare data
    data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi_strategy_backtest/0.DATA/BTCUSDT/spot/ohlc_data/2023_2024/btc_1h_data_2023_2024/btc_1h_data_2023_2024.csv'
    minute_data = load_data(data_path)

    # Run backtest
    bt = Backtest(minute_data, FukuizTradingStrategy, cash=1000000, commission=.002)
    stats = bt.run()
    print(stats)
    # Convert the trades to a DataFrame
    trades = stats['_trades']  # Accessing the trades DataFrame from the stats object

    # Save the trades to a CSV file
    trades_csv_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi_strategy_backtest/1.STATISTICAL_AND_PROBABILITY_BASED/1.fmz_pinescript_strategies_backtest/Trademaster_fmz_30_strategies/tradebook/trades.csv'
    trades.to_csv(trades_csv_path)

    

except Exception as e:
    print(f"Error in main script execution: {e}")
