#!/usr/bin/env python3
"""
Comprehensive test script for all 4 new trading strategies
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path to import strat2
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all strategies
from Statistical_Pairs_Mean_Reversion_Strategy.statistical_pairs_mean_reversion_strategy import StatisticalPairsMeanReversionStrategy
from Volatility_Contraction_Breakout_Strategy.volatility_contraction_breakout_strategy import VolatilityContractionBreakoutStrategy
from Market_Breadth_Rotation_Strategy.market_breadth_rotation_strategy import MarketBreadthRotationStrategy
from Liquidity_Aware_Momentum_Strategy.liquidity_aware_momentum_strategy import LiquidityAwareMomentumStrategy

def create_test_data(n_periods=300):
    """Create comprehensive test data for all strategies"""
    np.random.seed(42)
    
    # Generate price data with different market phases
    base_price = 100
    trend = np.linspace(0, 30, n_periods)  # Upward trend
    noise = np.random.normal(0, 2, n_periods)
    prices = base_price + trend + noise
    
    # Generate OHLCV data
    data = []
    for i, price in enumerate(prices):
        high = price + abs(np.random.normal(0, 1))
        low = price - abs(np.random.normal(0, 1))
        open_price = prices[i-1] if i > 0 else price
        close = price
        volume = np.random.randint(1000, 10000)
        
        data.append({
            'date': pd.Timestamp('2023-01-01') + pd.Timedelta(days=i),
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    return pd.DataFrame(data)

def test_strategy(strategy_class, strategy_name, data, params=None):
    """Test a single strategy"""
    print(f"\n{'='*60}")
    print(f"TESTING {strategy_name.upper()}")
    print(f"{'='*60}")
    
    try:
        # Initialize strategy
        strategy = strategy_class(params)
        print(f"✅ Strategy initialized successfully")
        
        # Test data preprocessing
        processed_data = strategy.preprocess_data(data.copy())
        print(f"✅ Data preprocessing completed. Shape: {processed_data.shape}")
        
        # Generate signals
        signals_df = strategy.generate_signals(processed_data)
        signals = signals_df['Signal']
        print(f"✅ Signal generation completed. Shape: {signals_df.shape}")
        
        # Analyze signals
        buy_signals = (signals == 1).sum()
        sell_signals = (signals == -1).sum()
        total_signals = buy_signals + sell_signals
        
        print(f"\nSignal Analysis:")
        print(f"  Buy signals: {buy_signals}")
        print(f"  Sell signals: {sell_signals}")
        print(f"  Total signals: {total_signals}")
        
        # Test entry and exit rules
        entry_signals = strategy.entry_rules(processed_data)
        exit_signals = strategy.exit_rules(processed_data)
        
        print(f"\nEntry/Exit Rules:")
        print(f"  Entry signals: {entry_signals.sum()}")
        print(f"  Exit signals: {exit_signals.sum()}")
        
        # Test position sizing
        position_sizes = strategy.position_sizing(processed_data)
        print(f"  Position sizing: {position_sizes.iloc[0]}")
        
        # Test parameter schema
        schema = strategy.parameter_schema()
        print(f"\nParameter Schema ({len(schema)} parameters):")
        for param, details in schema.items():
            print(f"  {param}: {details['type']} (default: {details['default']})")
        
        # Test description
        description = strategy.description()
        print(f"\nStrategy Description:")
        print(f"  {description[:200]}...")
        
        # Test with different parameters if applicable
        if params is None:
            print(f"\nTesting with custom parameters...")
            try:
                custom_params = {
                    'position_size': 2.0,
                    'max_holding_period': 20
                }
                # Only set parameters that exist in the schema
                valid_params = {k: v for k, v in custom_params.items() if k in schema}
                
                if valid_params:
                    custom_strategy = strategy_class(valid_params)
                    custom_signals = custom_strategy.generate_signals(processed_data)
                    custom_buy = (custom_signals['Signal'] == 1).sum()
                    custom_sell = (custom_signals['Signal'] == -1).sum()
                    print(f"  Custom parameters - Buy: {custom_buy}, Sell: {custom_sell}")
                else:
                    print(f"  No valid custom parameters to test")
            except Exception as e:
                print(f"  Custom parameter test skipped: {e}")
        
        print(f"✅ {strategy_name} test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing {strategy_name}: {str(e)}")
        return False

def main():
    """Main test function"""
    print("="*80)
    print("COMPREHENSIVE STRATEGY TESTING SUITE")
    print("="*80)
    
    # Create test data
    data = create_test_data(300)
    print(f"Created test data with {len(data)} periods")
    print(f"Date range: {data['date'].min()} to {data['date'].max()}")
    print(f"Price range: ${data['close'].min():.2f} to ${data['close'].max():.2f}")
    
    # Define strategies to test
    strategies = [
        (StatisticalPairsMeanReversionStrategy, "Statistical Pairs Mean-Reversion"),
        (VolatilityContractionBreakoutStrategy, "Volatility Contraction Breakout"),
        (MarketBreadthRotationStrategy, "Market Breadth Rotation"),
        (LiquidityAwareMomentumStrategy, "Liquidity-Aware Momentum")
    ]
    
    # Test each strategy
    results = []
    for strategy_class, strategy_name in strategies:
        success = test_strategy(strategy_class, strategy_name, data)
        results.append((strategy_name, success))
    
    # Summary
    print(f"\n{'='*80}")
    print("TESTING SUMMARY")
    print(f"{'='*80}")
    
    successful = 0
    for strategy_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{strategy_name}: {status}")
        if success:
            successful += 1
    
    print(f"\nOverall Results: {successful}/{len(results)} strategies passed")
    
    if successful == len(results):
        print("🎉 All strategies are working correctly!")
    else:
        print("⚠️  Some strategies need attention")
    
    print("="*80)

if __name__ == "__main__":
    main()
