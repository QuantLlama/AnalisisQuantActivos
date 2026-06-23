import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import Dataset, DataLoader
import torch
import talib

class FuturesDataset(Dataset):
    def __init__(self, data, seq_length):
        self.data = torch.FloatTensor(data)
        self.seq_length = seq_length

    def __len__(self):
        return len(self.data) - self.seq_length

    def __getitem__(self, index):
        return (self.data[index:index+self.seq_length], self.data[index+1:index+self.seq_length+1])

import yfinance as yf

def load_data(ticker, period='2y', interval='1h'):
    """
    Downloads data from Yahoo Finance.
    ticker: Symbol (e.g., 'NQ=F', 'ES=F', 'MNQ=F', 'MES=F')
    period: Data period (e.g., '1y', '2y', '5y', 'max')
    interval: Data interval (e.g., '1d', '1h', '15m')
    """
    print(f"Downloading data for {ticker}...")
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    
    if df.empty:
        raise ValueError(f"No data found for ticker {ticker}. Check internet connection or ticker symbol.")
        
    # Ensure we have the standard columns
    # yfinance returns MultiIndex columns sometimes, flatten if necessary
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # Reset index to have Date/Datetime as a column if needed, or keep as index
    # For this system, keeping as index is fine, but let's ensure 'Close' exists
    if 'Close' not in df.columns:
         # Try 'Adj Close' if 'Close' is missing
         if 'Adj Close' in df.columns:
             df['Close'] = df['Adj Close']
         else:
             raise ValueError("Data does not contain 'Close' price column.")
             
    print(f"Data loaded successfully: {len(df)} records.")
    return df

def preprocess_data(df, seq_length):
    # Calculate Technical Indicators (on raw prices first)
    if len(df) > 30:
        df['RSI'] = talib.RSI(df['Close'], timeperiod=14)
        df['ADX'] = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=14)
        df['ATR'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
        
    # --- Feature Engineering: Log Returns ---
    # We use Log Returns to make data stationary and avoid "lazy model" issues
    df['Log_Ret_Close'] = np.log(df['Close'] / df['Close'].shift(1))
    df['Log_Ret_High']  = np.log(df['High'] / df['High'].shift(1))
    df['Log_Ret_Low']   = np.log(df['Low'] / df['Low'].shift(1))
    
    # Log Volume (to compress range)
    # Add 1 to avoid log(0)
    df['Log_Vol'] = np.log1p(df['Volume'])
    
    # Drop NaNs created by shifting and indicators
    df = df.dropna()
    
    scaler = MinMaxScaler(feature_range=(-1, 1))
    
    # Select features for the model
    # We NO LONGER use raw prices. We use Returns + Indicators.
    cols = ['Log_Ret_Close', 'Log_Ret_High', 'Log_Ret_Low', 'Log_Vol', 'RSI', 'ADX', 'ATR']
    
    # Verify all columns exist
    missing_cols = [c for c in cols if c not in df.columns]
    if missing_cols:
        print(f"Warning: Missing columns {missing_cols}. Filling with 0.")
        for c in missing_cols:
            df[c] = 0.0
    
    # Fit Scaler
    data = scaler.fit_transform(df[cols].values)
    
    dataset = FuturesDataset(data, seq_length)
    return dataset, scaler
