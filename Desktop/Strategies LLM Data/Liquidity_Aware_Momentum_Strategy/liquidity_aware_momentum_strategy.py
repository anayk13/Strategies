import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strat2 import Strategy

class LiquidityAwareMomentumStrategy(Strategy):
    """
    Liquidity-Aware Momentum with VWAP Percentile & OBV Divergence Strategy
    
    Capture momentum in liquid names while avoiding moves with poor participation — 
    combine intraday VWAP percentile, On-Balance Volume divergence, and dollar-volume 
    liquidity filter.
    
    Entry: High liquidity AND VWAP percentile > 70% AND OBV trending up AND Price momentum
    Exit: VWAP percentile < 50% AND OBV turns down OR Price < VWAP OR trailing stop
    """

    def __init__(self, params=None):
        """
        Initialize the strategy with parameters.
        Args:
            params (dict): Dictionary of strategy parameters.
        """
        self.params = params or {
            'vwap_period': 20,
            'vwap_percentile_threshold': 70,
            'vwap_exit_threshold': 50,
            'obv_short_period': 9,
            'obv_long_period': 21,
            'dollar_volume_period': 20,
            'dollar_volume_threshold': 1000000,
            'momentum_period': 14,
            'momentum_threshold': 0.02,
            'atr_period': 14,
            'atr_multiplier': 1.2,
            'max_holding_period': 30,
            'position_size': 1.0
        }
        self.signals = None
        self.trades = None
        self.position = 0  # 0 = flat, 1 = long
        self.entry_price = None
        self.highest_price = None
        self.entry_date = None

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
        required_cols = ['close', 'high', 'low', 'volume']
        if not all(col in data.columns for col in required_cols):
            raise ValueError(f"Data must contain columns: {required_cols}")
        
        # Convert date column to datetime if needed
        if 'date' in data.columns and not pd.api.types.is_datetime64_any_dtype(data['date']):
            data['date'] = pd.to_datetime(data['date'])
        
        # Sort by date if date column exists
        if 'date' in data.columns:
            data = data.sort_values('date').reset_index(drop=True)
        
        return data

    def calculate_vwap(self, high, low, close, volume):
        """
        Calculate Volume Weighted Average Price (VWAP)
        
        Args:
            high (pd.Series): High prices
            low (pd.Series): Low prices
            close (pd.Series): Close prices
            volume (pd.Series): Volume
            
        Returns:
            pd.Series: VWAP values
        """
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).rolling(window=self.params['vwap_period']).sum() / volume.rolling(window=self.params['vwap_period']).sum()
        return vwap

    def calculate_vwap_percentile(self, close, vwap, period):
        """
        Calculate VWAP percentile
        
        Args:
            close (pd.Series): Close prices
            vwap (pd.Series): VWAP values
            period (int): Rolling period for percentile calculation
            
        Returns:
            pd.Series: VWAP percentile values
        """
        # Calculate ratio of close to VWAP
        vwap_ratio = close / vwap
        
        # Calculate rolling percentile
        vwap_percentile = vwap_ratio.rolling(window=period).rank(pct=True) * 100
        
        return vwap_percentile

    def calculate_obv(self, close, volume):
        """
        Calculate On-Balance Volume (OBV)
        
        Args:
            close (pd.Series): Close prices
            volume (pd.Series): Volume
            
        Returns:
            pd.Series: OBV values
        """
        price_change = close.diff()
        obv = volume.copy()
        obv[price_change < 0] = -volume[price_change < 0]
        obv[price_change == 0] = 0
        obv = obv.cumsum()
        
        return obv

    def calculate_obv_ema(self, obv, short_period, long_period):
        """
        Calculate OBV EMAs for trend detection
        
        Args:
            obv (pd.Series): OBV values
            short_period (int): Short EMA period
            long_period (int): Long EMA period
            
        Returns:
            tuple: (short_ema, long_ema)
        """
        short_ema = obv.ewm(span=short_period).mean()
        long_ema = obv.ewm(span=long_period).mean()
        
        return short_ema, long_ema

    def calculate_dollar_volume(self, close, volume):
        """
        Calculate dollar volume
        
        Args:
            close (pd.Series): Close prices
            volume (pd.Series): Volume
            
        Returns:
            pd.Series: Dollar volume values
        """
        return close * volume

    def calculate_atr(self, high, low, close, period):
        """
        Calculate Average True Range (ATR)
        
        Args:
            high (pd.Series): High prices
            low (pd.Series): Low prices
            close (pd.Series): Close prices
            period (int): ATR period
            
        Returns:
            pd.Series: ATR values
        """
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr

    def calculate_momentum(self, close, period):
        """
        Calculate price momentum
        
        Args:
            close (pd.Series): Close prices
            period (int): Momentum period
            
        Returns:
            pd.Series: Momentum values
        """
        return close.pct_change(periods=period)

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
        if data is None or len(data) < max(self.params['vwap_period'], self.params['obv_long_period']):
            return pd.DataFrame(index=data.index if data is not None else [], columns=['Signal'])
        
        # Calculate indicators
        vwap = self.calculate_vwap(data['high'], data['low'], data['close'], data['volume'])
        vwap_percentile = self.calculate_vwap_percentile(data['close'], vwap, self.params['vwap_period'])
        
        obv = self.calculate_obv(data['close'], data['volume'])
        obv_short_ema, obv_long_ema = self.calculate_obv_ema(
            obv, self.params['obv_short_period'], self.params['obv_long_period']
        )
        
        dollar_volume = self.calculate_dollar_volume(data['close'], data['volume'])
        avg_dollar_volume = dollar_volume.rolling(window=self.params['dollar_volume_period']).mean()
        
        momentum = self.calculate_momentum(data['close'], self.params['momentum_period'])
        
        atr = self.calculate_atr(data['high'], data['low'], data['close'], self.params['atr_period'])
        
        # Initialize signals
        signals = pd.Series(0, index=data.index)
        
        # State-based logic for signal generation
        for i in range(max(self.params['vwap_period'], self.params['obv_long_period']), len(data)):
            current_close = data['close'].iloc[i]
            current_high = data['high'].iloc[i]
            current_vwap = vwap.iloc[i]
            current_vwap_percentile = vwap_percentile.iloc[i]
            current_obv_short = obv_short_ema.iloc[i]
            current_obv_long = obv_long_ema.iloc[i]
            current_avg_dollar_volume = avg_dollar_volume.iloc[i]
            current_momentum = momentum.iloc[i]
            current_atr = atr.iloc[i]
            
            # Skip if we don't have enough data for indicators
            if (pd.isna(current_vwap) or pd.isna(current_vwap_percentile) or 
                pd.isna(current_obv_short) or pd.isna(current_obv_long) or 
                pd.isna(current_avg_dollar_volume) or pd.isna(current_momentum) or 
                pd.isna(current_atr)):
                continue
            
            # Check for stop loss and time-based exit
            if self.position == 1:
                # Update highest price since entry
                if self.highest_price is None or current_high > self.highest_price:
                    self.highest_price = current_high
                
                # Trailing stop: ATR multiplier below highest price
                trailing_stop = self.highest_price - (self.params['atr_multiplier'] * current_atr)
                
                # VWAP stop: price below VWAP
                vwap_stop = current_close < current_vwap
                
                # Time-based exit
                time_exit = (self.entry_date is not None and 
                           i - self.entry_date > self.params['max_holding_period'])
                
                # Exit conditions
                if (current_close < trailing_stop or vwap_stop or time_exit):
                    signals.iloc[i] = -1  # Exit signal
                    self.position = 0
                    self.entry_price = None
                    self.highest_price = None
                    self.entry_date = None
                    continue
            
            # Entry Rules (only if no position)
            if self.position == 0:
                # Liquidity filter: sufficient dollar volume
                liquidity_condition = current_avg_dollar_volume > self.params['dollar_volume_threshold']
                
                # VWAP percentile condition: close in upper percentile
                vwap_condition = current_vwap_percentile > self.params['vwap_percentile_threshold']
                
                # OBV confirmation: short EMA > long EMA (trending up)
                obv_condition = current_obv_short > current_obv_long
                
                # Momentum condition: positive momentum above threshold
                momentum_condition = current_momentum > self.params['momentum_threshold']
                
                # All conditions must be met
                if (liquidity_condition and vwap_condition and obv_condition and momentum_condition):
                    signals.iloc[i] = 1  # Buy signal
                    self.position = 1
                    self.entry_price = current_close
                    self.highest_price = current_high
                    self.entry_date = i
        
        self.signals = signals
        return pd.DataFrame({'Signal': signals}, index=data.index)

    def description(self):
        """
        Text description of what the strategy does.
        Useful for UI or LLM explanations.
        """
        return """
        Liquidity-Aware Momentum with VWAP Percentile & OBV Divergence Strategy
        
        Capture momentum in liquid names while avoiding moves with poor participation — 
        combine intraday VWAP percentile, On-Balance Volume divergence, and dollar-volume 
        liquidity filter.
        
        Entry Conditions (ALL must be met):
        - Liquidity filter: 20-day average dollar volume > threshold
        - VWAP Percentile: Close in upper VWAP percentile (> 70th percentile)
        - OBV confirmation: OBV EMA(9) > OBV EMA(21) (trending up)
        - Price momentum: 14-day return > threshold (e.g., 2%)
        
        Exit Conditions (ANY triggers exit):
        - VWAP percentile drops below 50th percentile AND OBV turns down
        - Price falls below VWAP of the day
        - Trailing stop: 1.2 × ATR below highest price
        - Time stop: Maximum holding period (30 days)
        
        Position Management:
        - Size positions proportional to dollar-volume
        - Limit exposure to avoid crowding in low-liquidity names
        - Monitor intraday VWAP for execution improvement
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
            "vwap_period": {
                "type": "int", 
                "min": 10, 
                "max": 50, 
                "default": 20,
                "description": "Period for VWAP calculation"
            },
            "vwap_percentile_threshold": {
                "type": "float", 
                "min": 50.0, 
                "max": 90.0, 
                "default": 70.0,
                "description": "VWAP percentile threshold for entry"
            },
            "vwap_exit_threshold": {
                "type": "float", 
                "min": 30.0, 
                "max": 70.0, 
                "default": 50.0,
                "description": "VWAP percentile threshold for exit"
            },
            "obv_short_period": {
                "type": "int", 
                "min": 5, 
                "max": 20, 
                "default": 9,
                "description": "Short period for OBV EMA"
            },
            "obv_long_period": {
                "type": "int", 
                "min": 15, 
                "max": 50, 
                "default": 21,
                "description": "Long period for OBV EMA"
            },
            "dollar_volume_period": {
                "type": "int", 
                "min": 10, 
                "max": 50, 
                "default": 20,
                "description": "Period for average dollar volume calculation"
            },
            "dollar_volume_threshold": {
                "type": "float", 
                "min": 100000, 
                "max": 10000000, 
                "default": 1000000,
                "description": "Minimum dollar volume threshold"
            },
            "momentum_period": {
                "type": "int", 
                "min": 5, 
                "max": 30, 
                "default": 14,
                "description": "Period for momentum calculation"
            },
            "momentum_threshold": {
                "type": "float", 
                "min": 0.01, 
                "max": 0.10, 
                "default": 0.02,
                "description": "Minimum momentum threshold (2%)"
            },
            "atr_period": {
                "type": "int", 
                "min": 5, 
                "max": 30, 
                "default": 14,
                "description": "Period for ATR calculation"
            },
            "atr_multiplier": {
                "type": "float", 
                "min": 1.0, 
                "max": 3.0, 
                "default": 1.2,
                "description": "ATR multiplier for trailing stop"
            },
            "max_holding_period": {
                "type": "int", 
                "min": 10, 
                "max": 60, 
                "default": 30,
                "description": "Maximum holding period in days"
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
        self.entry_price = None
        self.highest_price = None
        self.entry_date = None
