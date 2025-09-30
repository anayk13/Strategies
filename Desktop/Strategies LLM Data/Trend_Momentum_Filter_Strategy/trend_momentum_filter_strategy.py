import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strat2 import Strategy

class TrendMomentumFilterStrategy(Strategy):
    """
    Trend + Momentum Filter Strategy
    
    This strategy aims to capture strong upward trends while filtering out weak signals, 
    by combining trend-following using Moving Averages, momentum confirmation using RSI, 
    and volatility breakout using Bollinger Bands.
    
    Entry: MA50 > MA200 AND 40 < RSI(14) < 70 AND Price > Middle Bollinger Band
    Exit: Price < MA50 OR RSI(14) > 75 OR Price < Lower Bollinger Band
    """

    def __init__(self, params=None):
        """
        Initialize the strategy with parameters.
        Args:
            params (dict): Dictionary of strategy parameters.
        """
        self.params = params or {
            'short_ma_period': 50,
            'long_ma_period': 200,
            'rsi_period': 14,
            'rsi_lower': 40,
            'rsi_upper': 70,
            'rsi_exit': 75,
            'bb_period': 20,
            'bb_std': 2.0,
            'position_size': 1.0
        }
        self.signals = None
        self.trades = None
        self.position = 0  # 0 = flat, 1 = long, -1 = short

    def preprocess_data(self, data, context=None):
        """
        Preprocess input data before signal generation.
        Can handle missing values, normalization, resampling, 
        feature engineering, etc.
        
        Args:
            data (pd.DataFrame): Input OHLCV or feature data.
            context (dict, optional): Extra datasets or metadata.
        
        Returns:
            pd.DataFrame: Preprocessed data.
        """
        if data is None or len(data) == 0:
            return data
        
        # Ensure we have required columns
        required_cols = ['close']
        if not all(col in data.columns for col in required_cols):
            raise ValueError(f"Data must contain columns: {required_cols}")
        
        # Convert date column to datetime if needed
        if 'date' in data.columns and not pd.api.types.is_datetime64_any_dtype(data['date']):
            data['date'] = pd.to_datetime(data['date'])
        
        # Sort by date if date column exists
        if 'date' in data.columns:
            data = data.sort_values('date').reset_index(drop=True)
        
        return data

    def calculate_rsi(self, prices, period):
        """
        Calculate RSI (Relative Strength Index)
        
        Args:
            prices (pd.Series): Price series
            period (int): RSI period
            
        Returns:
            pd.Series: RSI values
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_bollinger_bands(self, prices, period, std_dev):
        """
        Calculate Bollinger Bands
        
        Args:
            prices (pd.Series): Price series
            period (int): Moving average period
            std_dev (float): Standard deviation multiplier
            
        Returns:
            tuple: (upper_band, middle_band, lower_band)
        """
        middle_band = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = middle_band + (std_dev * std)
        lower_band = middle_band - (std_dev * std)
        return upper_band, middle_band, lower_band

    def generate_signals(self, data, context=None):
        """
        Core strategy logic: generate trading signals.
        
        Args:
            data (pd.DataFrame): Input OHLCV (and optionally other features).
            context (dict, optional): Additional datasets (pairs, options, ML predictions).
        
        Returns:
            pd.DataFrame: Must include a 'Signal' column 
                          (1=long, -1=short, 0=flat, or fractional weights).
        """
        if data is None or len(data) < max(self.params['long_ma_period'], self.params['bb_period']):
            return pd.DataFrame(index=data.index if data is not None else [], columns=['Signal'])
        
        # Calculate indicators
        short_ma = data['close'].rolling(window=self.params['short_ma_period']).mean()
        long_ma = data['close'].rolling(window=self.params['long_ma_period']).mean()
        rsi = self.calculate_rsi(data['close'], self.params['rsi_period'])
        upper_bb, middle_bb, lower_bb = self.calculate_bollinger_bands(
            data['close'], self.params['bb_period'], self.params['bb_std']
        )
        
        # Initialize signals
        signals = pd.Series(0, index=data.index)
        
        # State-based logic for signal generation
        for i in range(max(self.params['long_ma_period'], self.params['bb_period']), len(data)):
            current_close = data['close'].iloc[i]
            current_short_ma = short_ma.iloc[i]
            current_long_ma = long_ma.iloc[i]
            current_rsi = rsi.iloc[i]
            current_middle_bb = middle_bb.iloc[i]
            current_lower_bb = lower_bb.iloc[i]
            
            # Skip if we don't have enough data for indicators
            if (pd.isna(current_short_ma) or pd.isna(current_long_ma) or 
                pd.isna(current_rsi) or pd.isna(current_middle_bb) or pd.isna(current_lower_bb)):
                continue
            
            # Entry Rule: All conditions must be met
            if self.position == 0:
                trend_condition = current_short_ma > current_long_ma  # MA50 > MA200
                momentum_condition = (self.params['rsi_lower'] < current_rsi < self.params['rsi_upper'])  # 40 < RSI < 70
                volatility_condition = current_close > current_middle_bb  # Price > Middle BB
                
                if trend_condition and momentum_condition and volatility_condition:
                    signals.iloc[i] = 1  # Buy signal
                    self.position = 1
                    
            # Exit Rule: Any condition triggers exit
            elif self.position == 1:
                trend_exit = current_close < current_short_ma  # Price < MA50
                momentum_exit = current_rsi > self.params['rsi_exit']  # RSI > 75
                volatility_exit = current_close < current_lower_bb  # Price < Lower BB
                
                if trend_exit or momentum_exit or volatility_exit:
                    signals.iloc[i] = -1  # Sell signal
                    self.position = 0
        
        self.signals = signals
        return pd.DataFrame({'Signal': signals}, index=data.index)

    def description(self):
        """
        Text description of what the strategy does.
        Useful for UI or LLM explanations.
        """
        return """
        Trend + Momentum Filter Strategy
        
        This strategy aims to capture strong upward trends while filtering out weak signals, 
        by combining trend-following using Moving Averages, momentum confirmation using RSI, 
        and volatility breakout using Bollinger Bands.
        
        Entry Conditions (ALL must be met):
        - Trend filter: 50-day MA > 200-day MA (uptrend)
        - Momentum filter: RSI(14) between 40–70 (strong momentum, not overbought)
        - Volatility filter: Price closes above the middle Bollinger Band
        
        Exit Conditions (ANY triggers exit):
        - Price closes below the 50-day MA (trend weakening)
        - RSI(14) > 75 (overbought, momentum exhausted)
        - Price closes below lower Bollinger Band (extreme reversal)
        
        Position Management:
        - One position per stock at a time
        - Can be applied to multiple stocks independently
        - Optional position sizing rules to limit risk per trade
        """

    def parameter_schema(self):
        """
        Define the parameters with metadata (for no-code UI).
        
        Returns:
            dict: Example format:
                {
                    "lookback": {"type": "int", "min": 5, "max": 200, "default": 20},
                    "threshold": {"type": "float", "min": 0.1, "max": 5.0, "default": 2.0}
                }
        """
        return {
            "short_ma_period": {
                "type": "int", 
                "min": 5, 
                "max": 100, 
                "default": 50,
                "description": "Period for short-term moving average (MA50)"
            },
            "long_ma_period": {
                "type": "int", 
                "min": 50, 
                "max": 500, 
                "default": 200,
                "description": "Period for long-term moving average (MA200)"
            },
            "rsi_period": {
                "type": "int", 
                "min": 5, 
                "max": 50, 
                "default": 14,
                "description": "Period for RSI calculation"
            },
            "rsi_lower": {
                "type": "float", 
                "min": 20, 
                "max": 50, 
                "default": 40,
                "description": "Lower RSI threshold for entry"
            },
            "rsi_upper": {
                "type": "float", 
                "min": 50, 
                "max": 80, 
                "default": 70,
                "description": "Upper RSI threshold for entry"
            },
            "rsi_exit": {
                "type": "float", 
                "min": 70, 
                "max": 90, 
                "default": 75,
                "description": "RSI threshold for exit (overbought)"
            },
            "bb_period": {
                "type": "int", 
                "min": 10, 
                "max": 50, 
                "default": 20,
                "description": "Period for Bollinger Bands calculation"
            },
            "bb_std": {
                "type": "float", 
                "min": 1.0, 
                "max": 3.0, 
                "default": 2.0,
                "description": "Standard deviation multiplier for Bollinger Bands"
            },
            "position_size": {
                "type": "float", 
                "min": 0.1, 
                "max": 10.0, 
                "default": 1.0,
                "description": "Position size multiplier"
            }
        }

    def entry_rules(self, data):
        """
        Define conditions for entering trades.
        By default, uses 'Signal' values directly.
        
        Args:
            data (pd.DataFrame): Data with 'Signal' column.
        
        Returns:
            pd.Series: Series of entry signals (1, -1, or 0).
        """
        if self.signals is not None:
            return (self.signals == 1).astype(int)
        return pd.Series(0, index=data.index)

    def exit_rules(self, data):
        """
        Define conditions for exiting trades.
        Supports holding periods, trailing stops, custom exit logic.
        
        Args:
            data (pd.DataFrame): Strategy data.
        
        Returns:
            pd.Series: Series of exit signals (1=exit, 0=hold).
        """
        if self.signals is not None:
            return (self.signals == -1).astype(int)
        return pd.Series(0, index=data.index)

    def position_sizing(self, data):
        """
        Define how much to allocate per trade.
        Default is equal sizing (1 unit).
        
        Args:
            data (pd.DataFrame): Strategy data.
        
        Returns:
            pd.Series: Position sizes per timestamp.
        """
        return pd.Series(self.params['position_size'], index=data.index)

    def risk_management(self, data):
        """
        Apply stop-loss, take-profit, or max drawdown rules.
        Override for custom risk logic.
        
        Args:
            data (pd.DataFrame): Strategy data.
        
        Returns:
            pd.DataFrame: Adjusted data after applying risk management.
        """
        return data

    def reset_position(self):
        """Reset position state (useful for backtesting)."""
        self.position = 0

    def get_performance_metrics(self, data, returns=None):
        """
        Calculate performance metrics for the strategy.
        
        Args:
            data (pd.DataFrame): Strategy data with signals
            returns (pd.Series, optional): Returns series
            
        Returns:
            dict: Performance metrics
        """
        if returns is None:
            returns = data['close'].pct_change()
        
        # Calculate basic metrics
        total_return = (data['close'].iloc[-1] / data['close'].iloc[0] - 1) * 100
        volatility = returns.std() * np.sqrt(252) * 100
        sharpe_ratio = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        
        # Calculate drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100
        
        # Calculate win rate
        if self.signals is not None:
            trades = self.signals[self.signals != 0]
            if len(trades) > 0:
                # Simple win rate calculation based on signal direction
                win_rate = (trades == 1).sum() / len(trades) * 100
            else:
                win_rate = 0
        else:
            win_rate = 0
        
        return {
            'total_return': total_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate
        }
