import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os

class Visualizer:
    def __init__(self, output_dir='outputs/plots', filename_prefix=''):
        self.output_dir = output_dir
        self.filename_prefix = filename_prefix
        os.makedirs(self.output_dir, exist_ok=True)
        self._set_style()

    def _set_style(self):
        """Configures a modern, professional dark theme for all plots."""
        plt.style.use('dark_background')
        
        # Custom Colors (Neon/Cyberpunk Palette)
        self.colors = {
            'bg': '#13131a',       # Main Background
            'card': '#1e1e1e',     # Card/Plot Background
            'text': '#e2e8f0',     # Main Text
            'grid': '#2d2d3a',     # Grid Lines
            'primary': '#3b82f6',  # Neon Blue (Real Price)
            'secondary': '#ef4444',# Neon Red (Prediction/Loss)
            'accent': '#10b981',   # Neon Green (Success/Indicators)
            'warning': '#fbbf24',  # Yellow (Warning/Signals)
            'cyan': '#06b6d4',
            'purple': '#8b5cf6'
        }
        
        # RC Params for Global Styling
        plt.rcParams.update({
            'figure.facecolor': self.colors['bg'],
            'axes.facecolor': self.colors['card'],
            'axes.edgecolor': self.colors['grid'],
            'axes.labelcolor': self.colors['text'],
            'text.color': self.colors['text'],
            'xtick.color': self.colors['text'],
            'ytick.color': self.colors['text'],
            'grid.color': self.colors['grid'],
            'grid.linestyle': '--',
            'grid.alpha': 0.6,
            'font.family': 'sans-serif',
            'font.sans-serif': ['Arial', 'DejaVu Sans', 'Liberation Sans', 'Bitstream Vera Sans', 'sans-serif'],
            'figure.titlesize': 16,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.facecolor': self.colors['card'],
            'legend.edgecolor': self.colors['grid'],
            'legend.fontsize': 10
        })
        # sns.set_theme(style="darkgrid") # Overridden by custom style

    def _add_glow(self, ax, x, y, color, label=None, alpha=1.0, linewidth=1.5):
        """Adds a neon glow effect to a line."""
        # Main line
        line, = ax.plot(x, y, color=color, label=label, alpha=alpha, linewidth=linewidth, zorder=10)
        
        # Glow effect (multiple transparent lines)
        for n in range(1, 4):
            ax.plot(x, y, color=color, alpha=0.15/n, linewidth=linewidth + (n*3), zorder=10-n)
            
        return line

    def _add_watermark(self, ax):
        """Adds a subtle watermark to the plot."""
        ax.text(0.5, 0.5, 'QUANTUM GAN', transform=ax.transAxes,
                fontsize=40, color='white', alpha=0.03,
                ha='center', va='center', rotation=30, zorder=0)

    def plot_training_losses(self, d_losses, g_losses, is_supervised=False):
        fig, ax = plt.subplots(figsize=(12, 6))
        
        if is_supervised:
            # Supervised Mode: Plot single MSE loss curve
            self._add_glow(ax, range(len(d_losses)), d_losses, self.colors['primary'], label='MSE Loss')
            ax.fill_between(range(len(d_losses)), d_losses, color=self.colors['primary'], alpha=0.05)
            ax.set_title('Training Loss: Supervised LSTM', pad=20)
        else:
            # GAN Mode: Plot discriminator vs generator
            self._add_glow(ax, range(len(d_losses)), d_losses, self.colors['primary'], label='Discriminator Loss')
            self._add_glow(ax, range(len(g_losses)), g_losses, self.colors['secondary'], label='Generator Loss')
            ax.fill_between(range(len(d_losses)), d_losses, color=self.colors['primary'], alpha=0.05)
            ax.fill_between(range(len(g_losses)), g_losses, color=self.colors['secondary'], alpha=0.05)
            ax.set_title('Training Losses: Generator vs Discriminator', pad=20)
        
        self._add_watermark(ax)
        
        ax.set_xlabel('Epoch')
        ax.set_ylabel('Loss')
        ax.legend(loc='upper right')
        ax.grid(True, linestyle='--', alpha=0.2)
        
        plt.tight_layout()
        filename = f'{self.filename_prefix}_training_losses.png' if self.filename_prefix else 'training_losses.png'
        plt.savefig(f'{self.output_dir}/{filename}', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_predictions(self, real_prices, predicted_prices, title='Real vs Predicted Prices'):
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # Real Price (Blue Glow)
        self._add_glow(ax, range(len(real_prices)), real_prices, self.colors['primary'], label='Real Price')
        
        # Predicted Price (Red Glow, Dashed)
        # Note: Glow doesn't support linestyle easily, so we plot main line dashed and glow solid but faint
        ax.plot(predicted_prices, color=self.colors['secondary'], label='Predicted Price', 
                linestyle='--', linewidth=2, zorder=10)
        # Faint glow for prediction
        for n in range(1, 4):
            ax.plot(predicted_prices, color=self.colors['secondary'], alpha=0.1/n, linewidth=2 + (n*3), zorder=10-n)

        self._add_watermark(ax)
        
        # Annotate Last Price
        last_real = real_prices[-1] if len(real_prices) > 0 else 0
        last_pred = predicted_prices[-1] if len(predicted_prices) > 0 else 0
        
        ax.annotate(f'{last_real:.2f}', xy=(len(real_prices)-1, last_real), 
                    xytext=(10, 0), textcoords='offset points', color=self.colors['primary'], fontweight='bold')
        ax.annotate(f'{last_pred:.2f}', xy=(len(predicted_prices)-1, last_pred), 
                    xytext=(10, -15), textcoords='offset points', color=self.colors['secondary'], fontweight='bold')

        ax.set_title(title, pad=20)
        ax.set_xlabel('Time Steps')
        ax.set_ylabel('Price')
        ax.legend(loc='upper left')
        
        plt.tight_layout()
        filename = f'{self.filename_prefix}_predictions.png' if self.filename_prefix else 'predictions.png'
        plt.savefig(f'{self.output_dir}/{filename}', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_features(self, df, features=['Close', 'RSI', 'MACD']):
        # Normalize for visualization if needed, or plot on subplots
        n = len(features)
        fig, axes = plt.subplots(n, 1, figsize=(14, 4*n), sharex=True)
        if n == 1: axes = [axes]
        
        for i, feature in enumerate(features):
            ax = axes[i]
            if feature in df.columns:
                color = self.colors['cyan'] if i % 2 == 0 else self.colors['purple']
                self._add_glow(ax, df.index, df[feature], color)
                ax.set_title(feature, color=self.colors['text'], fontsize=10)
                ax.set_ylabel('Value')
                ax.grid(True, alpha=0.1)
                
        self._add_watermark(axes[-1]) # Watermark on bottom plot
            
        plt.xlabel('Date')
        plt.tight_layout()
        filename = f'{self.filename_prefix}_features_overview.png' if self.filename_prefix else 'features_overview.png'
        plt.savefig(f'{self.output_dir}/{filename}', dpi=300)
        plt.close()

    def plot_fourier_components(self, df, original_col='Close', components=[3, 6, 9]):
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # Real Price
        self._add_glow(ax, df.index, df[original_col], self.colors['primary'], label='Real Price', alpha=0.3)
        
        colors = [self.colors['accent'], self.colors['warning'], self.colors['cyan']]
        
        for i, comp in enumerate(components):
            if f'Fourier_{comp}' in df.columns:
                color = colors[i % len(colors)]
                self._add_glow(ax, df.index, df[f'Fourier_{comp}'], color, label=f'Fourier {comp} Components')
                
        self._add_watermark(ax)
        ax.set_title('Fourier Transform Components (Trend Analysis)', pad=20)
        ax.set_xlabel('Date')
        ax.set_ylabel('Price')
        ax.set_ylabel('Price')
        ax.legend()
        filename = f'{self.filename_prefix}_fourier_analysis.png' if self.filename_prefix else 'fourier_analysis.png'
        plt.savefig(f'{self.output_dir}/{filename}', dpi=300)
        plt.close()

    def plot_feature_importance(self, feature_names, importance_scores):
        fig, ax = plt.subplots(figsize=(12, 8))
        indices = np.argsort(importance_scores)
        
        # Horizontal Bar Chart with Glow
        y_pos = range(len(indices))
        ax.barh(y_pos, importance_scores[indices], align='center', color=self.colors['accent'], alpha=0.8)
        
        # Add values to bars
        for i, v in enumerate(importance_scores[indices]):
            ax.text(v + 0.001, i, f'{v:.4f}', color='white', va='center', fontsize=9)
            
        self._add_watermark(ax)
        
        ax.set_title('Feature Importance (XGBoost)', pad=20)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([feature_names[i] for i in indices])
        ax.set_xlabel('Relative Importance')
        
        plt.tight_layout()
        filename = f'{self.filename_prefix}_feature_importance.png' if self.filename_prefix else 'feature_importance.png'
        plt.savefig(f'{self.output_dir}/{filename}', dpi=300)
        plt.close()

    def plot_correlation_matrix(self, df, title='Correlation Matrix'):
        plt.figure(figsize=(12, 10))
        # Use a dark-friendly colormap
        sns.heatmap(df.corr(), annot=True, cmap='magma', fmt=".2f", 
                    linewidths=0.5, linecolor=self.colors['bg'],
                    cbar_kws={'label': 'Correlation Coefficient'})
        plt.title(title, pad=20)
        plt.tight_layout()
        filename = f'{self.filename_prefix}_correlation_matrix.png' if self.filename_prefix else 'correlation_matrix.png'
        plt.savefig(f'{self.output_dir}/{filename}', dpi=300)
        plt.close()

    def plot_technical_dashboard(self, df, ticker_name="Asset"):
        # Create a dashboard with Price, Volume, MACD
        fig = plt.figure(figsize=(18, 12))
        gs = fig.add_gridspec(3, 1, height_ratios=[3, 1, 1], hspace=0.1)
        
        # Panel 1: Price + MA + BB
        ax1 = fig.add_subplot(gs[0])
        self._add_glow(ax1, df.index, df['Close'], self.colors['text'], label='Close Price', linewidth=1)
        
        if 'MA7' in df.columns: 
            self._add_glow(ax1, df.index, df['MA7'], self.colors['cyan'], label='MA 7', alpha=0.7)
        if 'MA21' in df.columns: 
            self._add_glow(ax1, df.index, df['MA21'], self.colors['purple'], label='MA 21', alpha=0.7)
            
        if 'BB_Upper' in df.columns: 
            ax1.plot(df.index, df['BB_Upper'], color=self.colors['accent'], linestyle='--', alpha=0.3)
            ax1.plot(df.index, df['BB_Lower'], color=self.colors['accent'], linestyle='--', alpha=0.3)
            ax1.fill_between(df.index, df['BB_Upper'], df['BB_Lower'], color=self.colors['accent'], alpha=0.05)
            
        self._add_watermark(ax1)
        ax1.set_title(f'{ticker_name} - Technical Analysis', fontsize=18, pad=20)
        ax1.set_ylabel('Price')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.1)
        
        # Panel 2: Volume
        ax2 = fig.add_subplot(gs[1], sharex=ax1)
        if 'Volume' in df.columns:
            ax2.bar(df.index, df['Volume'], color=self.colors['cyan'], alpha=0.5)
        ax2.set_ylabel('Volume')
        ax2.grid(True, alpha=0.1)
        
        # Panel 3: MACD
        ax3 = fig.add_subplot(gs[2], sharex=ax1)
        if 'MACD' in df.columns:
            ax3.plot(df.index, df['MACD'], label='MACD', color=self.colors['warning'])
            ax3.plot(df.index, df['Signal'], label='Signal', color=self.colors['secondary'])
            
            # Color coded histogram
            hist = df['MACD'] - df['Signal']
            colors = [self.colors['accent'] if x >= 0 else self.colors['secondary'] for x in hist]
            ax3.bar(df.index, hist, color=colors, alpha=0.5)
            
        ax3.set_ylabel('MACD')
        ax3.legend(loc='upper left')
        ax3.grid(True, alpha=0.1)
        
        plt.tight_layout()
        filename = f'{self.filename_prefix}_technical_dashboard.png' if self.filename_prefix else 'technical_dashboard.png'
        plt.savefig(f'{self.output_dir}/{filename}', dpi=300, facecolor=fig.get_facecolor())
        plt.close()

    def plot_arima(self, train_data, test_data, forecast, title='ARIMA Forecast'):
        fig, ax = plt.subplots(figsize=(14, 7))
        
        ax.plot(train_data.index, train_data, label='Train Data', color='gray', alpha=0.4)
        self._add_glow(ax, test_data.index, test_data, self.colors['primary'], label='Real Price (Test)')
        
        # Forecast with dashed glow
        ax.plot(test_data.index, forecast, label='ARIMA Forecast', color=self.colors['warning'], linestyle='--', linewidth=2)
        
        self._add_watermark(ax)
        ax.set_title(title, pad=20)
        ax.legend()
        ax.grid(True, alpha=0.1)
        
        filename = f'{self.filename_prefix}_arima_forecast.png' if self.filename_prefix else 'arima_forecast.png'
        plt.savefig(f'{self.output_dir}/{filename}', dpi=300)
        plt.close()

    def plot_sentiment(self, df, sentiment_col='VIX', price_col='Close'):
        if sentiment_col not in df.columns:
            return
            
        fig, ax1 = plt.subplots(figsize=(14, 7))

        color = self.colors['primary']
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Price', color=color)
        self._add_glow(ax1, df.index, df[price_col], color, label='Price')
        ax1.tick_params(axis='y', labelcolor=color)

        ax2 = ax1.twinx()
        color = self.colors['secondary']
        ax2.set_ylabel('Market Sentiment (VIX)', color=color)
        ax2.plot(df.index, df[sentiment_col], color=color, alpha=0.6, linestyle='--', label='VIX (Fear Index)')
        ax2.fill_between(df.index, df[sentiment_col], color=color, alpha=0.1)
        ax2.tick_params(axis='y', labelcolor=color)
        
        self._add_watermark(ax1)
        plt.title('Price vs Market Sentiment (VIX)', pad=20)
        fig.tight_layout()
        filename = f'{self.filename_prefix}_sentiment_analysis.png' if self.filename_prefix else 'sentiment_analysis.png'
        plt.savefig(f'{self.output_dir}/{filename}', dpi=300)
        plt.close()

    def plot_gaussian_process(self, train_data, test_data, prediction, sigma, title='Gaussian Process Regression'):
        fig, ax = plt.subplots(figsize=(14, 7))
        
        ax.plot(train_data.index, train_data, label='Observations', color='gray', linestyle=':', alpha=0.5)
        self._add_glow(ax, test_data.index, test_data, self.colors['primary'], label='Real Price (Target)')
        self._add_glow(ax, test_data.index, prediction, self.colors['secondary'], label='GPR Prediction')
        
        # Plot confidence interval with gradient-like transparency if possible, or just simple fill
        ax.fill_between(
            test_data.index,
            prediction - 1.96 * sigma,
            prediction + 1.96 * sigma,
            alpha=0.1,
            color=self.colors['secondary'],
            label='95% Confidence Interval'
        )
        
        self._add_watermark(ax)
        ax.set_title(title, pad=20)
        ax.set_xlabel('Date')
        ax.set_ylabel('Price')
        ax.legend(loc='upper left')
        
        filename = f'{self.filename_prefix}_gaussian_process.png' if self.filename_prefix else 'gaussian_process.png'
        plt.savefig(f'{self.output_dir}/{filename}', dpi=300)
        plt.close()

    def plot_training_snapshot(self, real, predicted, epoch=None, title=None, filename=None):
        fig, ax = plt.subplots(figsize=(14, 7))
        
        self._add_glow(ax, range(len(real)), real, self.colors['primary'], label='Real Price')
        
        # Predicted
        ax.plot(predicted, label='Predicted Price', color=self.colors['secondary'], linestyle='--', linewidth=2)
        
        self._add_watermark(ax)
        
        if title:
            ax.set_title(title, pad=20)
        else:
            ax.set_title(f'Prediction Snapshot - Epoch {epoch}', pad=20)
            
        ax.set_xlabel('Time Steps')
        ax.set_ylabel('Price')
        ax.legend()
        
        if filename:
            final_filename = f'{self.filename_prefix}_{filename}' if self.filename_prefix else filename
            plt.savefig(f'{self.output_dir}/{final_filename}', dpi=300)
        else:
            final_filename = f'{self.filename_prefix}_snapshot_epoch_{epoch}.png' if self.filename_prefix else f'snapshot_epoch_{epoch}.png'
            plt.savefig(f'{self.output_dir}/{final_filename}', dpi=300)
        plt.close()
