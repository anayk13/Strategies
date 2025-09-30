import pandas as pd
import numpy as np
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strat2 import Strategy

class Top3MomentumStrategy(Strategy):
    """
    Top-3 12-Month Momentum Strategy
    
    This strategy aims to capture strong upward trends by buying the three stocks 
    with the highest trailing 12-month returns and holding them for the next three months.
    """

    def __init__(self, params=None):
        """
        Initialize the strategy with parameters.
        Args:
            params (dict): Dictionary of strategy parameters.
        """
        self.params = params or {
            'momentum_period': 12,  # months
            'holding_period': 3,    # months
            'top_n_stocks': 3,      # number of stocks to select
            'rebalance_frequency': 3  # months between rebalancing
        }
        self.signals = None
        self.trades = None
        self.current_positions = {}  # {symbol: {'entry_date': date, 'entry_price': price}}
        self.last_rebalance_date = None

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
        
        # Ensure we have the required columns
        required_cols = ['symbol', 'date', 'close']
        if not all(col in data.columns for col in required_cols):
            raise ValueError(f"Data must contain columns: {required_cols}")
        
        # Convert date column to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(data['date']):
            data['date'] = pd.to_datetime(data['date'])
        
        # Sort by date
        data = data.sort_values('date').reset_index(drop=True)
        
        return data

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
        if data is None or len(data) == 0:
            return pd.DataFrame(columns=['Signal'])
        
        # Initialize signals
        signals = pd.Series(0, index=data.index)
        
        # Get unique dates for rebalancing
        unique_dates = data['date'].dt.date.unique()
        unique_dates = sorted(unique_dates)
        
        # Process each rebalancing date
        for i, current_date in enumerate(unique_dates):
            # Check if it's time to rebalance
            if self._should_rebalance(current_date):
                # Calculate 12-month returns for all stocks
                returns_data = self._calculate_momentum_returns(data, current_date)
                
                if len(returns_data) >= self.params['top_n_stocks']:
                    # Select top N stocks
                    top_stocks = returns_data.nlargest(self.params['top_n_stocks'], 'momentum_return')
                    
                    # Generate buy signals for top stocks
                    for _, stock in top_stocks.iterrows():
                        stock_mask = (data['symbol'] == stock['symbol']) & (data['date'].dt.date == current_date)
                        signals[stock_mask] = 1
                    
                    # Generate sell signals for current positions not in top stocks
                    current_symbols = set(self.current_positions.keys())
                    top_symbols = set(top_stocks['symbol'])
                    symbols_to_sell = current_symbols - top_symbols
                    
                    for symbol in symbols_to_sell:
                        stock_mask = (data['symbol'] == symbol) & (data['date'].dt.date == current_date)
                        signals[stock_mask] = -1
                    
                    # Update positions
                    self._update_positions(top_stocks, current_date)
                    self.last_rebalance_date = current_date
        
        self.signals = signals
        return pd.DataFrame({'Signal': signals}, index=data.index)

    def _should_rebalance(self, current_date):
        """Check if it's time to rebalance based on the rebalancing frequency."""
        if self.last_rebalance_date is None:
            return True
        
        # Calculate months between last rebalance and current date
        months_diff = (current_date.year - self.last_rebalance_date.year) * 12 + \
                     (current_date.month - self.last_rebalance_date.month)
        
        return months_diff >= self.params['rebalance_frequency']

    def _calculate_momentum_returns(self, data, current_date):
        """Calculate 12-month momentum returns for all stocks."""
        # Calculate the date 12 months ago
        current_dt = pd.to_datetime(current_date)
        start_date = current_dt - pd.DateOffset(months=self.params['momentum_period'])
        
        # Get data for the momentum calculation period
        momentum_data = data[
            (data['date'] >= start_date) & 
            (data['date'] <= current_dt)
        ].copy()
        
        if momentum_data.empty:
            return pd.DataFrame(columns=['symbol', 'momentum_return'])
        
        # Calculate returns for each stock
        returns_list = []
        for symbol in momentum_data['symbol'].unique():
            stock_data = momentum_data[momentum_data['symbol'] == symbol].sort_values('date')
            
            if len(stock_data) >= 2:
                # Get first and last prices in the period
                first_price = stock_data['close'].iloc[0]
                last_price = stock_data['close'].iloc[-1]
                
                # Calculate 12-month return
                momentum_return = ((last_price - first_price) / first_price) * 100
                
                returns_list.append({
                    'symbol': symbol,
                    'momentum_return': momentum_return,
                    'current_price': last_price
                })
        
        return pd.DataFrame(returns_list)

    def _update_positions(self, top_stocks, current_date):
        """Update current positions with new selections."""
        # Clear existing positions
        self.current_positions.clear()
        
        # Add new positions
        for _, stock in top_stocks.iterrows():
            self.current_positions[stock['symbol']] = {
                'entry_date': current_date,
                'entry_price': stock['current_price']
            }

    def description(self):
        """
        Text description of what the strategy does.
        Useful for UI or LLM explanations.
        """
        return """
        Top-3 12-Month Momentum Strategy
        
        This strategy selects the top 3 stocks with the highest 12-month trailing returns
        and holds them for 3 months before rebalancing. It aims to capture momentum
        effects where stocks with strong past performance tend to continue trending
        upward in the short term.
        
        Entry: Top 3 stocks by 12-month momentum at rebalancing dates
        Exit: After 3-month holding period or when not in top 3
        Rebalancing: Every 3 months
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
            "momentum_period": {
                "type": "int",
                "min": 6,
                "max": 24,
                "default": 12,
                "description": "Number of months for momentum calculation"
            },
            "holding_period": {
                "type": "int",
                "min": 1,
                "max": 12,
                "default": 3,
                "description": "Number of months to hold positions"
            },
            "top_n_stocks": {
                "type": "int",
                "min": 1,
                "max": 10,
                "default": 3,
                "description": "Number of top stocks to select"
            },
            "rebalance_frequency": {
                "type": "int",
                "min": 1,
                "max": 12,
                "default": 3,
                "description": "Months between rebalancing"
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
        if self.signals is not None:
            # Equal weight allocation
            active_positions = (self.signals == 1).sum()
            if active_positions > 0:
                return pd.Series(1.0 / active_positions, index=data.index)
        return pd.Series(0, index=data.index)

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

