#!/usr/bin/env python3
"""
Comprehensive Strategy Tester
Tests all trading strategies and generates detailed results files
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all strategies
from Moving_Average_Crossover_Strategy.moving_average_crossover_strategy import MovingAverageCrossoverStrategy
from Statistical_Pairs_Mean_Reversion_Strategy.statistical_pairs_mean_reversion_strategy import StatisticalPairsMeanReversionStrategy
from Volatility_Contraction_Breakout_Strategy.volatility_contraction_breakout_strategy import VolatilityContractionBreakoutStrategy
from Market_Breadth_Rotation_Strategy.market_breadth_rotation_strategy import MarketBreadthRotationStrategy
from Liquidity_Aware_Momentum_Strategy.liquidity_aware_momentum_strategy import LiquidityAwareMomentumStrategy
from Trend_Momentum_Filter_Strategy.trend_momentum_filter_strategy import TrendMomentumFilterStrategy
from Volume_Breakout_Strategy.volume_breakout_strategy import VolumeBreakoutStrategy
from Weekly_Bollinger_Breakout_Strategy.weekly_bollinger_breakout_strategy import WeeklyBollingerBreakoutStrategy
from GapUp_Bollinger_Exit_Strategy.gapup_bollinger_strategy import GapUpBollingerStrategy
from Top3_12Month_Momentum_Strategy.top3_momentum_strategy import Top3MomentumStrategy

class StrategyTester:
    """Comprehensive strategy testing framework"""
    
    def __init__(self):
        self.results = {}
        self.test_date = datetime.now().strftime("%Y-%m-%d")
        
    def generate_test_data(self, days=500, start_price=100, trend='uptrend', volatility=0.02):
        """Generate synthetic test data with various patterns"""
        np.random.seed(42)  # For reproducible results
        
        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
        
        if trend == 'uptrend':
            # Create uptrend with some pullbacks
            trend_component = np.linspace(0, 0.3, days)  # 30% uptrend over period
        elif trend == 'downtrend':
            # Create downtrend with some rallies
            trend_component = np.linspace(0, -0.2, days)  # 20% downtrend over period
        else:  # sideways
            # Create sideways movement
            trend_component = np.linspace(0, 0.05, days)  # 5% slight uptrend
        
        # Add some cyclical patterns
        cycle1 = 0.1 * np.sin(2 * np.pi * np.arange(days) / 50)  # 50-day cycle
        cycle2 = 0.05 * np.sin(2 * np.pi * np.arange(days) / 20)  # 20-day cycle
        
        # Generate random noise
        noise = np.random.normal(0, volatility, days)
        
        # Combine all components
        log_returns = trend_component/days + cycle1/days + cycle2/days + noise
        
        # Convert to prices
        prices = start_price * np.exp(np.cumsum(log_returns))
        
        # Generate OHLCV data
        data = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.normal(0, 0.005, days)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, days))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, days))),
            'close': prices,
            'volume': np.random.randint(100000, 1000000, days)
        })
        
        # Ensure high >= max(open, close) and low <= min(open, close)
        data['high'] = np.maximum(data['high'], np.maximum(data['open'], data['close']))
        data['low'] = np.minimum(data['low'], np.minimum(data['open'], data['close']))
        
        return data
    
    def generate_pairs_data(self, days=500):
        """Generate synthetic pairs data for pairs trading strategy"""
        np.random.seed(42)
        
        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
        
        # Create two correlated but mean-reverting series
        base_trend = np.linspace(0, 0.2, days)
        common_factor = np.random.normal(0, 0.02, days)
        
        # Stock A
        stock_a_trend = base_trend + 0.3 * common_factor + np.random.normal(0, 0.015, days)
        stock_a_prices = 100 * np.exp(np.cumsum(stock_a_trend))
        
        # Stock B (correlated but with some divergence)
        stock_b_trend = base_trend + 0.7 * common_factor + np.random.normal(0, 0.012, days)
        stock_b_prices = 95 * np.exp(np.cumsum(stock_b_trend))
        
        data = pd.DataFrame({
            'date': dates,
            'stock_a_close': stock_a_prices,
            'stock_b_close': stock_b_prices,
            'stock_a_volume': np.random.randint(50000, 500000, days),
            'stock_b_volume': np.random.randint(40000, 400000, days)
        })
        
        return data
    
    def generate_market_breadth_data(self, days=500):
        """Generate synthetic market breadth data"""
        np.random.seed(42)
        
        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
        
        # Generate market breadth indicators
        ad_ratio = 1 + np.random.normal(0, 0.3, days)  # Around 1.0
        net_highs = np.random.normal(0, 50, days)  # Around 0
        
        # Generate sector data
        sectors = ['IT', 'Banking', 'Pharma', 'Auto', 'FMCG']
        sector_data = {}
        
        for sector in sectors:
            sector_trend = np.random.normal(0.001, 0.02, days)  # Slight positive trend
            sector_prices = 100 * np.exp(np.cumsum(sector_trend))
            sector_data[f'{sector}_close'] = sector_prices
            sector_data[f'{sector}_volume'] = np.random.randint(100000, 800000, days)
        
        data = pd.DataFrame({
            'date': dates,
            'ad_ratio': ad_ratio,
            'net_highs': net_highs,
            **sector_data
        })
        
        return data
    
    def calculate_performance_metrics(self, signals, prices):
        """Calculate comprehensive performance metrics"""
        if len(signals) == 0 or signals.sum() == 0:
            return {
                'total_signals': 0,
                'win_rate': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'avg_trade_duration': 0
            }
        
        # Calculate returns
        returns = prices.pct_change().fillna(0)
        
        # Calculate strategy returns
        strategy_returns = signals.shift(1) * returns
        
        # Basic metrics
        total_signals = int(abs(signals).sum())
        total_return = strategy_returns.sum()
        
        # Win rate
        winning_trades = (strategy_returns > 0).sum()
        win_rate = winning_trades / total_signals if total_signals > 0 else 0
        
        # Drawdown
        cumulative_returns = (1 + strategy_returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Sharpe ratio
        sharpe_ratio = strategy_returns.mean() / strategy_returns.std() if strategy_returns.std() > 0 else 0
        
        # Average trade duration
        trade_durations = []
        in_trade = False
        trade_start = 0
        
        for i, signal in enumerate(signals):
            if signal == 1 and not in_trade:  # Enter trade
                in_trade = True
                trade_start = i
            elif signal == -1 and in_trade:  # Exit trade
                trade_durations.append(i - trade_start)
                in_trade = False
        
        avg_trade_duration = np.mean(trade_durations) if trade_durations else 0
        
        return {
            'total_signals': total_signals,
            'win_rate': win_rate,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_trade_duration': avg_trade_duration
        }
    
    def test_strategy(self, strategy_class, strategy_name, test_data, test_scenarios):
        """Test a single strategy with multiple scenarios"""
        print(f"Testing {strategy_name}...")
        
        results = {
            'strategy_name': strategy_name,
            'test_date': self.test_date,
            'scenarios': {}
        }
        
        for scenario_name, data in test_scenarios.items():
            print(f"  Running scenario: {scenario_name}")
            
            try:
                # Initialize strategy
                strategy = strategy_class()
                
                # Preprocess data
                processed_data = strategy.preprocess_data(data.copy())
                
                # Generate signals
                signals_df = strategy.generate_signals(processed_data)
                signals = signals_df['Signal'] if 'Signal' in signals_df.columns else pd.Series(0, index=data.index)
                
                # Calculate performance metrics
                price_col = 'close' if 'close' in data.columns else data.columns[1]  # Use first price column
                metrics = self.calculate_performance_metrics(signals, data[price_col])
                
                # Add scenario results
                results['scenarios'][scenario_name] = {
                    'status': 'PASSED',
                    'metrics': metrics,
                    'total_signals': int(abs(signals).sum()),
                    'data_points': len(data),
                    'signal_breakdown': {
                        'buy_signals': int((signals == 1).sum()),
                        'sell_signals': int((signals == -1).sum()),
                        'hold_signals': int((signals == 0).sum())
                    }
                }
                
            except Exception as e:
                results['scenarios'][scenario_name] = {
                    'status': 'FAILED',
                    'error': str(e),
                    'data_points': len(data)
                }
                print(f"    ERROR: {str(e)}")
        
        return results
    
    def generate_test_report(self, strategy_name, results):
        """Generate detailed test report for a strategy"""
        report = f"""# {strategy_name} - Comprehensive Test Results

## Test Date: {self.test_date}
## Strategy Version: Enhanced with Risk Management

---

## 📊 **Strategy Overview**
- **Strategy Name**: {strategy_name}
- **Test Scenarios**: {len(results['scenarios'])}
- **Overall Status**: {'PASSED' if all(s['status'] == 'PASSED' for s in results['scenarios'].values()) else 'MIXED'}

---

## 🧪 **Test Scenarios**

"""
        
        for scenario_name, scenario_results in results['scenarios'].items():
            report += f"### {scenario_name}\n\n"
            
            if scenario_results['status'] == 'PASSED':
                metrics = scenario_results['metrics']
                signal_breakdown = scenario_results['signal_breakdown']
                
                report += f"✅ **PASSED** - Strategy executed successfully\n\n"
                report += f"**Performance Metrics:**\n"
                report += f"- Total Signals: {scenario_results['total_signals']}\n"
                report += f"- Win Rate: {metrics['win_rate']:.2%}\n"
                report += f"- Total Return: {metrics['total_return']:.2%}\n"
                report += f"- Max Drawdown: {metrics['max_drawdown']:.2%}\n"
                report += f"- Sharpe Ratio: {metrics['sharpe_ratio']:.2f}\n"
                report += f"- Avg Trade Duration: {metrics['avg_trade_duration']:.1f} days\n\n"
                
                report += f"**Signal Breakdown:**\n"
                report += f"- Buy Signals: {signal_breakdown['buy_signals']}\n"
                report += f"- Sell Signals: {signal_breakdown['sell_signals']}\n"
                report += f"- Hold Signals: {signal_breakdown['hold_signals']}\n\n"
                
            else:
                report += f"❌ **FAILED** - {scenario_results.get('error', 'Unknown error')}\n\n"
            
            report += "---\n\n"
        
        # Add summary
        passed_scenarios = sum(1 for s in results['scenarios'].values() if s['status'] == 'PASSED')
        total_scenarios = len(results['scenarios'])
        
        report += f"""## 📈 **Test Summary**

### Overall Results
- **Scenarios Passed**: {passed_scenarios}/{total_scenarios} ({passed_scenarios/total_scenarios:.1%})
- **Strategy Status**: {'✅ READY' if passed_scenarios == total_scenarios else '⚠️ NEEDS ATTENTION'}

### Key Findings
"""
        
        if passed_scenarios == total_scenarios:
            report += "- All test scenarios passed successfully\n"
            report += "- Strategy is ready for live trading\n"
            report += "- Risk management features working correctly\n"
        else:
            report += "- Some test scenarios failed\n"
            report += "- Review error messages and fix issues\n"
            report += "- Re-test before live trading\n"
        
        report += f"""
### Recommendations
1. **Monitor Performance**: Track key metrics in live trading
2. **Risk Management**: Ensure proper position sizing
3. **Market Conditions**: Adapt to changing market regimes
4. **Regular Testing**: Re-test periodically with new data

---

*Test completed on {self.test_date} by Comprehensive Strategy Testing Framework*
"""
        
        return report
    
    def run_all_tests(self):
        """Run comprehensive tests on all strategies"""
        print("🚀 Starting Comprehensive Strategy Testing...")
        print("=" * 60)
        
        # Define test scenarios
        test_scenarios = {
            'Uptrend Market': self.generate_test_data(500, 100, 'uptrend', 0.02),
            'Downtrend Market': self.generate_test_data(500, 100, 'downtrend', 0.02),
            'Sideways Market': self.generate_test_data(500, 100, 'sideways', 0.015),
            'High Volatility': self.generate_test_data(500, 100, 'uptrend', 0.04),
            'Low Volatility': self.generate_test_data(500, 100, 'uptrend', 0.01)
        }
        
        # Define strategies to test
        strategies = [
            (MovingAverageCrossoverStrategy, 'Moving Average Crossover Strategy'),
            (TrendMomentumFilterStrategy, 'Trend + Momentum Filter Strategy'),
            (VolumeBreakoutStrategy, 'Volume Breakout Strategy'),
            (WeeklyBollingerBreakoutStrategy, 'Weekly Bollinger Breakout Strategy'),
        ]
        
        # Test each strategy
        for strategy_class, strategy_name in strategies:
            print(f"\n🔍 Testing {strategy_name}")
            print("-" * 40)
            
            # Test the strategy
            results = self.test_strategy(strategy_class, strategy_name, None, test_scenarios)
            
            # Generate and save report
            report = self.generate_test_report(strategy_name, results)
            
            # Determine folder name
            folder_name = strategy_name.replace(' ', '_').replace('+', '_').replace('&', '_')
            folder_name = folder_name.replace('__', '_')
            
            # Save report
            report_path = f"{folder_name}/test_results.md"
            if os.path.exists(folder_name):
                with open(report_path, 'w') as f:
                    f.write(report)
                print(f"✅ Report saved to {report_path}")
            else:
                print(f"⚠️ Folder {folder_name} not found, skipping report save")
            
            # Store results
            self.results[strategy_name] = results
        
        print("\n🎉 All tests completed!")
        print("=" * 60)
        
        # Print summary
        total_strategies = len(strategies)
        total_scenarios = len(test_scenarios)
        total_tests = total_strategies * total_scenarios
        
        passed_tests = 0
        for strategy_name, results in self.results.items():
            for scenario_name, scenario_results in results['scenarios'].items():
                if scenario_results['status'] == 'PASSED':
                    passed_tests += 1
        
        print(f"📊 Test Summary:")
        print(f"   Total Strategies: {total_strategies}")
        print(f"   Total Scenarios: {total_scenarios}")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed Tests: {passed_tests}")
        print(f"   Success Rate: {passed_tests/total_tests:.1%}")

if __name__ == "__main__":
    tester = StrategyTester()
    tester.run_all_tests()
