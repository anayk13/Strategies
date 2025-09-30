# Trend + Momentum Filter Strategy

## Overview

The Trend + Momentum Filter Strategy aims to capture strong upward trends while filtering out weak signals by combining three key technical analysis components: trend-following using Moving Averages, momentum confirmation using RSI, and volatility breakout using Bollinger Bands.

## Strategy Description

### Objective
This strategy aims to capture strong upward trends while filtering out weak signals, by combining:
- **Trend-following** using Moving Averages
- **Momentum confirmation** using RSI
- **Volatility breakout** using Bollinger Bands

The combination ensures the stock is in an uptrend, has momentum, and is showing a breakout before entering.

### Indicators Used

#### 1. 50-Day and 200-Day Moving Averages (MA50, MA200)
- **Purpose**: Identify the long-term trend
- **Usage**: MA50 > MA200 indicates uptrend

#### 2. RSI (14-period)
- **Purpose**: Confirm momentum and avoid overbought conditions
- **Usage**: RSI between 40-70 for entry, RSI > 75 for exit

#### 3. Bollinger Bands (20,2)
- **Purpose**: Detect volatility breakouts and price extremes
- **Usage**: Price above middle band for entry, below lower band for exit

### Entry Rule (Buy)

**Conditions to enter a long position (ALL must be met):**

1. **Trend filter**: 50-day MA > 200-day MA (uptrend)
2. **Momentum filter**: RSI(14) between 40–70 (strong momentum, not overbought)
3. **Volatility filter**: Price closes above the middle Bollinger Band

**Action**: Buy at the next candle open or close (depending on execution rules)

### Exit Rule (Sell)

**Conditions to exit the position (ANY triggers exit):**

1. **Trend weakening**: Price closes below the 50-day MA
2. **Momentum exhaustion**: RSI(14) > 75 (overbought)
3. **Extreme reversal**: Price closes below lower Bollinger Band

**Action**: Exit the position immediately when any of the exit conditions are met

### Position Management

- Only one position per stock at a time
- Can be applied to multiple stocks in a portfolio, but each stock is managed independently
- Optional: Use position sizing rules to limit risk per trade

## Implementation Details

### Key Features
- **Multi-Filter Approach**: Combines trend, momentum, and volatility filters
- **State-based Logic**: Maintains position state to ensure proper entry/exit management
- **Custom RSI Calculation**: Implements RSI calculation from scratch
- **Bollinger Bands**: Custom implementation with configurable parameters
- **Performance Metrics**: Built-in performance calculation methods

### Parameters
- `short_ma_period` (int): Period for short-term moving average (default: 50)
- `long_ma_period` (int): Period for long-term moving average (default: 200)
- `rsi_period` (int): Period for RSI calculation (default: 14)
- `rsi_lower` (float): Lower RSI threshold for entry (default: 40)
- `rsi_upper` (float): Upper RSI threshold for entry (default: 70)
- `rsi_exit` (float): RSI threshold for exit (default: 75)
- `bb_period` (int): Period for Bollinger Bands (default: 20)
- `bb_std` (float): Standard deviation multiplier for Bollinger Bands (default: 2.0)
- `position_size` (float): Position size multiplier (default: 1.0)

### Usage Example

```python
from trend_momentum_filter_strategy import TrendMomentumFilterStrategy

# Initialize strategy with default parameters
strategy = TrendMomentumFilterStrategy()

# Or with custom parameters
strategy = TrendMomentumFilterStrategy({
    'short_ma_period': 50,
    'long_ma_period': 200,
    'rsi_period': 14,
    'rsi_lower': 40,
    'rsi_upper': 70,
    'rsi_exit': 75,
    'bb_period': 20,
    'bb_std': 2.0,
    'position_size': 1.0
})

# Generate signals
signals = strategy.generate_signals(data)

# Calculate performance metrics
metrics = strategy.get_performance_metrics(data)
```

## Strategy Logic

### Entry Logic
1. **Data Preprocessing**: Validates input data and ensures required columns are present
2. **Indicator Calculation**: Computes MA50, MA200, RSI(14), and Bollinger Bands
3. **Multi-Filter Check**: Verifies all three conditions are met simultaneously
4. **Signal Generation**: Creates buy signal when all conditions are satisfied

### Exit Logic
1. **Continuous Monitoring**: Checks exit conditions on each bar
2. **Any-Condition Exit**: Exits immediately when any exit condition is triggered
3. **Position Management**: Maintains single position with proper state tracking

## Backtesting / Live Execution Logic

### Daily/Weekly Check Process
1. Calculate MA50, MA200, RSI(14), Bollinger Bands
2. Verify all entry conditions
3. If conditions met → Buy
4. Monitor each day for exit signals
5. Close positions immediately if exit condition is triggered

### Performance Metrics to Evaluate
- **CAGR** (annualized return)
- **Maximum drawdown**
- **Win rate**
- **Average trade duration**
- **Sharpe ratio** / risk-adjusted return
- **Volatility**

## Advantages

- **Multi-Filter Approach**: Reduces false signals by requiring multiple confirmations
- **Trend Following**: Captures major trend movements
- **Momentum Confirmation**: Avoids overbought conditions
- **Volatility Awareness**: Uses Bollinger Bands for breakout detection
- **Risk Management**: Built-in exit conditions for risk control
- **Flexible Parameters**: Highly configurable for different market conditions

## Limitations

- **Lagging Indicators**: All indicators are lagging, so signals come after price movements
- **Whipsaws**: Can generate false signals in sideways markets
- **Parameter Sensitivity**: Performance depends heavily on parameter selection
- **Market Dependency**: Works best in trending markets, struggles in choppy conditions
- **No Short Selling**: Only captures upward trends, missing downward opportunities

## Risk Considerations

- **Market Risk**: Subject to general market movements
- **Trend Risk**: Performs poorly in sideways or choppy markets
- **Parameter Risk**: Incorrect parameter settings can lead to poor performance
- **Timing Risk**: May enter/exit positions at suboptimal times
- **Concentration Risk**: Single position at a time limits diversification

## Backtesting Notes

- Ensure sufficient historical data (at least 200+ periods for proper indicator calculation)
- Consider transaction costs and slippage in performance evaluation
- Test across different market conditions (trending, sideways, volatile)
- Validate parameter sensitivity and robustness
- Use walk-forward analysis to test parameter stability
- Consider different timeframes (daily, weekly) for execution

## Files

- `trend_momentum_filter_strategy.py`: Main strategy implementation
- `README_trend_momentum_filter.md`: This documentation file

