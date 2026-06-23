import pandas as pd
import numpy as np

class Backtester:
    def __init__(self, initial_capital=10000, transaction_cost=0.0005):
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.trades = []
        self.equity_curve = []

    def run_backtest(self, df, prediction_col='Prediction', price_col='Close', threshold=0.0, is_return=False):
        """
        Simulates trading based on predictions.
        If is_return=True:
            - Prediction is a Log Return.
            - If Pred > threshold -> BUY
            - If Pred < -threshold -> SELL
        If is_return=False (Legacy):
            - Prediction is a Price.
            - If Pred > Current * (1+th) -> BUY
        """
        capital = self.initial_capital
        position = 0 # 1 for Long, -1 for Short, 0 for Neutral
        entry_price = 0
        entry_date = None # Initialize entry_date
        
        signals = []
        
        # Ensure we have predictions aligned
        
        for i in range(len(df) - 1):
            current_price = df[price_col].iloc[i]
            predicted_val = df[prediction_col].iloc[i]
            next_price = df[price_col].iloc[i+1] # The price we actually get for the next step
            date = df.index[i]
            
            signal = "HOLD"
            
            # Strategy Logic
            if is_return:
                # Return Prediction Logic
                if predicted_val > threshold:
                    new_position = 1 # Long
                elif predicted_val < -threshold:
                    new_position = -1 # Short
                else:
                    new_position = position # Hold
            else:
                # Price Prediction Logic (Legacy)
                if predicted_val > current_price * (1 + threshold):
                    new_position = 1 # Long
                elif predicted_val < current_price * (1 - threshold):
                    new_position = -1 # Short
                else:
                    new_position = position # Hold previous
            
            # Execute Trade if position changes
            if new_position != position:
                # Close previous position
                if position != 0:
                    # Calculate PnL
                    # Long: (Exit - Entry) / Entry
                    # Short: (Entry - Exit) / Entry
                    if position == 1:
                        pnl_pct = (current_price - entry_price) / entry_price
                    else:
                        pnl_pct = (entry_price - current_price) / entry_price
                        
                    pnl_pct -= self.transaction_cost
                    capital *= (1 + pnl_pct)
                    
                    self.trades.append({
                        'Entry Date': entry_date,
                        'Exit Date': date,
                        'Type': 'LONG' if position == 1 else 'SHORT',
                        'Entry Price': entry_price,
                        'Exit Price': current_price,
                        'PnL %': pnl_pct * 100,
                        'Capital': capital
                    })
                
                # Open new position
                position = new_position
                entry_price = current_price
                entry_date = date
                
                if position == 1:
                    signal = "BUY"
                elif position == -1:
                    signal = "SELL"
            
            signals.append({
                'Date': date,
                'Price': current_price,
                'Prediction': predicted_val,
                'Signal': signal,
                'Position': "LONG" if position == 1 else "SHORT" if position == -1 else "NEUTRAL"
            })
            
            self.equity_curve.append(capital)
            
        # Close final position
        if position != 0:
            last_price = df[price_col].iloc[-1]
            if position == 1:
                pnl_pct = (last_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - last_price) / entry_price
            
            pnl_pct -= self.transaction_cost
            capital *= (1 + pnl_pct)
            
            self.trades.append({
                'Entry Date': entry_date,
                'Exit Date': df.index[-1],
                'Type': 'LONG' if position == 1 else 'SHORT',
                'Entry Price': entry_price,
                'Exit Price': last_price,
                'PnL %': pnl_pct * 100,
                'Capital': capital
            })
            
        results = pd.DataFrame(self.trades)
        signals_df = pd.DataFrame(signals)
        
        return results, signals_df, capital

    def get_metrics(self):
        if not self.trades:
            return {
                'Total Trades': 0,
                'Win Rate': 0.0,
                'Profit Factor': 0.0,
                'Total Return %': 0.0
            }
            
        df = pd.DataFrame(self.trades)
        wins = df[df['PnL %'] > 0]
        losses = df[df['PnL %'] <= 0]
        
        win_rate = len(wins) / len(df) * 100
        
        gross_profit = wins['PnL %'].sum()
        gross_loss = abs(losses['PnL %'].sum())
        
        profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
        total_return = (self.equity_curve[-1] - self.initial_capital) / self.initial_capital * 100
        
        return {
            'Total Trades': len(df),
            'Win Rate': win_rate,
            'Profit Factor': profit_factor,
            'Total Return %': total_return
        }
