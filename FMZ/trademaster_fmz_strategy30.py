import pandas as pd
import numpy as np
from backtesting import Strategy, Backtest
import pandas_ta as ta
import logging
import coloredlogs

# Set up logging
log_file_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi_strategy_backtest/1.STATISTICAL_AND_PROBABILITY_BASED/1.fmz_pinescript_strategies_backtest/Trademaster_fmz_30_strategies/tradebook/30_FlawlessVictoryDCA.log'

# Configure basic logging to file
logging.basicConfig(level=logging.DEBUG, filename=log_file_path, filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Set up colored logs for console output
coloredlogs.install(level='DEBUG',
                    fmt='%(asctime)s - %(levelname)s - %(message)s',
                    level_styles={
                        'info': {'color': 'green'},
                        'debug': {'color': 'white'},
                        'error': {'color': 'red'},
                    })

def load_and_prepare_data(csv_file_path):
    try:
        logging.info("Loading and preparing data.")
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
        logging.info("Data loading and preparation complete.")
        return data.dropna()
    except Exception as e:
        logging.error(f"Error in load_and_prepare_data: {e}")
        raise



def heikDownColor(df):
    return df.get('tradedowns', pd.Series([False] * len(df), index=df.index))

def heikUpColor(df):
    return df.get('tradeups', pd.Series([False] * len(df), index=df.index))

def heikExitColor(df):
    return df.get('tradeexitsignals', pd.Series([False] * len(df), index=df.index)) & df.get('tradeexits', pd.Series([False] * len(df), index=df.index))

def calculate_daily_indicators(df):
    """
    Calculate the indicators for the trading strategy using pandas_ta.
    
    :param df: DataFrame containing 'High', 'Low', 'Close', and 'Volume' columns.
    :return: DataFrame with calculated indicators.
    """
    try:
        # Ensure necessary columns are present
        required_columns = ['High', 'Low', 'Close', 'Open']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # EMA calculations
        p10 = 10
        p200 = 200

        df['ema10'] = ta.ema(df['Close'], length=p10)
        df['ema200'] = ta.ema(df['Close'], length=p200)

        # ATR calculations
        lengthatr = 12
        df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=lengthatr)
        df['ema_atr'] = ta.ema(df['Close'], length=lengthatr)

        df['ema_plus_atr'] = df['ema_atr'] + df['atr']
        df['ema_minus_atr'] = df['ema_atr'] - df['atr']

        # MACD Histogram calculation
        fastLengthHist = 12
        slowLengthHist = 26
        signalLength = 9

        macd = ta.macd(df['Close'], fast=fastLengthHist, slow=slowLengthHist, signal=signalLength)
        df['macd'] = macd['MACD_12_26_9']
        df['macd_signal'] = macd['MACDs_12_26_9']
        df['hist'] = df['macd'] - df['macd_signal']

        # Initialize trading signals columns if they are missing
        df['tradeups'] = False
        df['tradeexits'] = False
        df['tradedowns'] = False
        df['exitshort'] = False
        df['tradeshorts'] = False  # Added this initialization

        # Trade signals
        df['tradeups'] = (df['ema10'] > df['ema10'].shift(1)) & (df['Low'] > df['ema_minus_atr']) & (df['hist'] > df['hist'].shift(1))
        df['tradeexits'] = df['tradeups'].shift(1) & (df['ema10'] < df['ema10'].shift(1))
        df['tradedowns'] = ((df['ema10'] < df['ema10'].shift(1)) & (df['hist'] < df['hist'].shift(1))) | \
                           ((df['High'] > df['ema_plus_atr']) & (df['Close'] < df['ema_plus_atr']) & \
                            (df['Close'] < df['Open']) & (df['hist'] < df['hist'].shift(1)))
        df['exitshort'] = (df['Low'] < df['ema_minus_atr']) & (df['Close'] > df['Open']) & \
                           (df['ema10'] > df['ema10'].shift(1)) & (df['hist'] > df['hist'].shift(1))

        # Heiki Filters
        df['heikDownColor'] = heikDownColor(df)
        df['heikUpColor'] = heikUpColor(df)
        df['heikExitColor'] = heikExitColor(df)

        df['inashort_filt'] = df['heikDownColor'] & df['tradeshorts'] & ~df['heikUpColor']
        df['inalong_filt'] = df['heikUpColor'] & ~df['heikDownColor'] & ~df['tradeexits']
        df['inaexit_filt'] = df['heikExitColor'] & ~df['heikDownColor'] & ~df['heikUpColor']
        df['inasexits_filt'] = df['exitshort'] & (df['inashort_filt']) & ~df['tradeups']

        # Heiki Line Logic
        df['prev5'] = 0
        df.loc[df['inalong_filt'], 'prev5'] = 1000
        df.loc[df['inashort_filt'], 'prev5'] = -1000
        df.loc[df['inaexit_filt'], 'prev5'] = 0
        df.loc[df['inasexits_filt'], 'prev5'] = 0
        
        df['prev5'] = df['prev5'].fillna(method='ffill')

        # Generate signals
        df['shortdata2'] = (df['prev5'] == -1000) & (df['inashort_filt'])
        df['longdata2'] = (df['prev5'] == 1000) & (df['inalong_filt'])
        df['exitdata2'] = (df['prev5'] == 0) & ~df['inalong_filt'] & ~df['inashort_filt']

        # Convert boolean signals to integer codes
        df['signal'] = 0
        df.loc[df['longdata2'], 'signal'] = 1
        df.loc[df['shortdata2'], 'signal'] = -1
        df.loc[df['exitdata2'], 'signal'] = -2

        return df
    
    except Exception as e:
        print(f"Error in calculate_daily_indicators function: {e}")
        raise

def generate_signals(df):
    """
    Generate trading signals based on the 'prev5' values and add a signal column.
    
    :param df: DataFrame with 'prev5' column.
    :return: DataFrame with added 'signal' column.
    """
    try:
        # Initialize the signal column
        df['signal'] = 0
        
        # Generate long signals
        df.loc[(df['prev5'].shift(1) < 900) & (df['prev5'] > 0), 'signal'] = 1
        
        # Generate short signals
        df.loc[(df['prev5'].shift(1) > -900) & (df['prev5'] < 0), 'signal'] = -1
        
        # Generate exit signals
        df.loc[(df['prev5'] == 0) & ((df['prev5'].shift(1) > 0) | (df['prev5'].shift(1) < 0)), 'signal'] = -2
        
        return df

    except Exception as e:
        print(f"Error in generate_signals function: {e}")
        raise

class FlawlessVictoryDCA(Strategy):
    def init(self):
      logging.info("Starting")

    def next(self):
        signal = self.data.signal[-1]

        if signal == 1:
            self.buy()

        elif signal == -1:
            self.sell()

        elif signal == -2:
            self.position.close()



# Main script execution
try:
    # Load and prepare data
    data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi_strategy_backtest/0.DATA/BTCUSDT/spot/ohlc_data/2023_2024/btc_day_data_2023_2024/btc_day_data_2023_2024.csv'

    minute_data = load_and_prepare_data(data_path)
   

    # Calculate daily indicators and generate signals
    daily_data = calculate_daily_indicators(minute_data)
    logging.info(f"indicator generation complete data\n{daily_data}")
    daily_signals = generate_signals(daily_data)

   

    
    # Run backtest
    bt = Backtest(daily_signals, FlawlessVictoryDCA, cash=1000000, commission=.002)
    stats = bt.run()
    logging.info(stats)
    logging.info("Backtest complete")

    # Convert the trades to a DataFrame
    trades = stats['_trades']  # Accessing the trades DataFrame from the stats object

    # Save the trades to a CSV file
    trades_csv_path = '/Users/pranaygaurav/Downloads/AlgoTrading/p4_crypto_2cents/cefi_strategy_backtest/1.STATISTICAL_AND_PROBABILITY_BASED/1.fmz_pinescript_strategies_backtest/Trademaster_fmz_30_strategies/tradebook/30_FlawlessVictoryDCA_backtest_trades.csv'
    trades.to_csv(trades_csv_path)

    logging.info(f"Trades have been exported to {trades_csv_path}")

except Exception as e:
    logging.error(f"Error in main script execution: {e}")
