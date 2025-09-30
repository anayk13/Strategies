# Statistical Pairs Mean-Reversion Strategy

## Overview

The Statistical Pairs Mean-Reversion Strategy exploits temporary divergences between two historically related instruments (pairs) by trading when their price relationship deviates significantly from its long-run mean and expecting reversion.

## Strategy Description

### Objective
Exploit temporary divergences between two historically related instruments (pairs) by trading when their price relationship deviates significantly from its long-run mean and expecting reversion.

### Indicators / Metrics Used

#### 1. Price Ratio or Spread
- **Calculation**: `spread = PriceA - β·PriceB` (β from OLS regression)
- **Purpose**: Measure the relationship between two correlated assets

#### 2. Rolling Mean of Spread
- **Window**: 90 days (configurable)
- **Purpose**: Calculate the long-run mean of the spread

#### 3. Rolling Std Dev of Spread
- **Window**: 90 days (configurable)
- **Purpose**: Calculate the standard deviation for Z-score calculation

#### 4. Z-score
- **Formula**: `(Spread - RollingMean) / RollingStdDev`
- **Purpose**: Standardize the spread to identify extreme deviations

#### 5. Cointegration Test (ADF / Engle-Granger)
- **Purpose**: Ensure pair is mean-reverting historically (optional filter)

### Entry Rule (Trades)

**Long Spread / Buy A & Sell B:**
- Condition: Z-score < -2 (spread is unusually low)
- Action: Enter long spread position

**Short Spread / Sell A & Buy B:**
- Condition: Z-score > +2 (spread is unusually high)
- Action: Enter short spread position

**Additional Requirements:**
- Require cointegration (or acceptable historical stationarity) for pair selection if available

### Exit Rule (Close Trades)

**Primary Exit:**
- Close position when Z-score crosses 0 (mean reversion completed)

**Secondary Exit:**
- Close when Z-score reverts inside a smaller band (e.g., |Z| < 0.5)

**Risk Management:**
- Optional stop-loss: exit if |Z| > 4 or after maximum holding period

### Position Management

- Use equal risk sizing across legs (dollar-neutral)
- Size A and B so net position has near-zero dollar exposure
- Limit capital per pair (e.g., 1–2% of portfolio)
- Max concurrent pairs configurable

## Implementation Details

### Key Features
- **Cointegration Testing**: ADF test to ensure pair is mean-reverting
- **Dynamic Beta Calculation**: OLS regression to calculate hedge ratio
- **Z-score Based Signals**: Statistical approach to identify extreme deviations
- **Risk Management**: Stop-loss and time-based exits
- **Dollar-Neutral Positioning**: Equal risk sizing across both legs

### Parameters
- `lookback_window` (int): Rolling window for mean and std calculation (default: 90)
- `z_score_entry` (float): Z-score threshold for entry signals (default: 2.0)
- `z_score_exit` (float): Z-score threshold for exit signals (default: 0.5)
- `z_score_stop` (float): Z-score threshold for stop loss (default: 4.0)
- `max_holding_period` (int): Maximum holding period in days (default: 40)
- `min_correlation` (float): Minimum correlation for pair selection (default: 0.7)
- `cointegration_test` (bool): Enable cointegration test (default: True)
- `position_size` (float): Position size multiplier (default: 1.0)

### Usage Example

```python
from statistical_pairs_mean_reversion_strategy import StatisticalPairsMeanReversionStrategy

# Initialize strategy with default parameters
strategy = StatisticalPairsMeanReversionStrategy()

# Or with custom parameters
strategy = StatisticalPairsMeanReversionStrategy({
    'lookback_window': 90,
    'z_score_entry': 2.0,
    'z_score_exit': 0.5,
    'z_score_stop': 4.0,
    'max_holding_period': 40,
    'cointegration_test': True,
    'position_size': 1.0
})

# Generate signals
signals = strategy.generate_signals(data)
```

## Backtesting / Live Execution Logic

### Daily Check Process
1. Select candidate pairs (same sector/ETF, high historical correlation)
2. Compute β if using spread = A - β·B or use simple ratio
3. Compute rolling mean/std and z-score each day
4. Generate entries when z-score breaches thresholds
5. Exit on mean reversion or stop conditions

### Performance Tracking
- Track PnL, time-to-mean, and pair-specific hit-rate
- Monitor correlation stability over time
- Assess cointegration persistence

## Advantages

- **Statistical Foundation**: Based on mean reversion theory
- **Risk Management**: Dollar-neutral positioning reduces market risk
- **Diversification**: Can trade multiple pairs simultaneously
- **Quantitative Approach**: Objective entry/exit criteria
- **Market Neutral**: Profits from relative price movements, not market direction

## Limitations

- **Pair Selection Risk**: Requires careful pair selection and monitoring
- **Execution Complexity**: Two legs, slippage on both
- **Structural Breaks**: Fails if fundamental relationship changes
- **Correlation Decay**: Pairs may become less correlated over time
- **Transaction Costs**: Higher costs due to two-legged trades

## Risk Considerations

- **Correlation Risk**: Pairs may decouple permanently
- **Execution Risk**: Slippage on both legs of the trade
- **Model Risk**: Statistical relationships may break down
- **Liquidity Risk**: One or both assets may become illiquid
- **Regime Risk**: Market conditions may change fundamentally

## Backtesting Notes

- Ensure sufficient historical data for reliable statistics
- Test across different market regimes (trending, sideways, volatile)
- Validate cointegration persistence over time
- Consider transaction costs and slippage
- Monitor correlation stability and adjust pairs as needed
- Use walk-forward analysis to test parameter robustness

## Key Notes

- Requires careful pair selection (cointegration helps)
- Execution complexity: two legs, slippage on both
- Good for range-bound relationships; fails if structural breaks occur
- Monitor correlation and cointegration continuously
- Consider market regime changes that may affect pair relationships

## Files

- `statistical_pairs_mean_reversion_strategy.py`: Main strategy implementation
- `README_pairs_mean_reversion.md`: This documentation file
