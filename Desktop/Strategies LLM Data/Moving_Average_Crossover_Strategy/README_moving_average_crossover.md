# Moving Average Crossover Strategy

## Overview

The Moving Average Crossover Strategy is a trend-following strategy that identifies long-term trend shifts using two moving averages of different lengths. This strategy aims to enter during the start of an uptrend and exit when the trend reverses.

## Strategy Description

### Objective
This strategy identifies long-term trend shifts using two moving averages of different lengths. It aims to enter during the start of an uptrend and exit when the trend reverses.

### Indicators Used
- **50-Day Moving Average (Short-Term Trend)**: Faster moving average that responds quickly to price changes
- **200-Day Moving Average (Long-Term Trend)**: Slower moving average that represents the long-term trend

### Entry Rule (Buy)
- **Condition**: When the 50-day moving average crosses above the 200-day moving average (Golden Cross)
- **Action**: Enter a long position

### Exit Rule (Sell)
- **Condition**: When the 50-day moving average crosses below the 200-day moving average (Death Cross)
- **Action**: Exit the position

### Position Management
- One position at a time
- No pyramiding
- Long-only strategy

## Implementation Details

### Key Features
- **State-based Logic**: Maintains position state to ensure only one position at a time
- **Crossover Detection**: Properly detects when moving averages cross over each other
- **Parameter Flexibility**: Configurable short and long MA periods
- **Risk Management**: Built-in position sizing and risk management framework

### Parameters
- `short_ma_period` (int): Period for short-term moving average (default: 50)
- `long_ma_period` (int): Period for long-term moving average (default: 200)
- `position_size` (float): Position size multiplier (default: 1.0)

### Usage Example

```python
from moving_average_crossover_strategy import MovingAverageCrossoverStrategy

# Initialize strategy with default parameters
strategy = MovingAverageCrossoverStrategy()

# Or with custom parameters
strategy = MovingAverageCrossoverStrategy({
    'short_ma_period': 50,
    'long_ma_period': 200,
    'position_size': 1.0
})

# Generate signals
signals = strategy.generate_signals(data)
```

## Strategy Logic

1. **Data Preprocessing**: Validates input data and ensures required columns are present
2. **Moving Average Calculation**: Computes 50-day and 200-day moving averages
3. **Crossover Detection**: Identifies when short MA crosses above/below long MA
4. **Signal Generation**: Creates buy/sell signals based on crossover events
5. **Position Management**: Maintains single position with proper entry/exit logic

## Advantages

- **Trend Following**: Captures major trend changes in the market
- **Simple Logic**: Easy to understand and implement
- **Long-term Focus**: Reduces noise from short-term price fluctuations
- **Proven Strategy**: Well-established approach used by many traders

## Limitations

- **Lagging Indicator**: Moving averages are lagging indicators, so signals come after trend changes
- **Whipsaws**: Can generate false signals in sideways markets
- **No Short Selling**: Only captures upward trends, missing downward opportunities
- **Single Timeframe**: Doesn't consider multiple timeframes or market conditions

## Risk Considerations

- **Market Risk**: Subject to general market movements
- **Trend Risk**: Performs poorly in choppy, sideways markets
- **Timing Risk**: May enter/exit positions at suboptimal times
- **Concentration Risk**: Single position at a time limits diversification

## Backtesting Notes

- Ensure sufficient historical data (at least 200+ periods for proper MA calculation)
- Consider transaction costs and slippage in performance evaluation
- Test across different market conditions (trending, sideways, volatile)
- Validate parameter sensitivity and robustness

## Files

- `moving_average_crossover_strategy.py`: Main strategy implementation
- `README_moving_average_crossover.md`: This documentation file


