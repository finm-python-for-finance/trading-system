# Quick Fixes to Address Losses

## Summary of Changes Made

### 1. ✅ Added Transaction Costs
**File**: `order_manager.py`
- Added `commission_per_share` and `commission_pct` parameters
- Commissions are now deducted from cash on every execution
- Default: $0.005 per share + 0.1% of notional

**Impact**: This will reduce profitability by the amount of transaction costs. For a market-making strategy making $0.01 per trade, if costs are $0.005, you're only making $0.005 net.

### 2. ✅ Added Realistic Market Spread Modeling
**File**: `Strategy_Backtesting.py`
- Added `model_real_spreads` parameter (default: True)
- When enabled, orders must cross the market spread to get filled
- You pay the ask when buying, take the bid when selling
- Default spread: 2 basis points (0.02%)

**Impact**: Market-making strategies now pay the spread cost, which can eat into small edges.

### 3. ✅ Added Adverse Selection Model
**File**: `Strategy_Backtesting.py`
- Added `model_adverse_selection` parameter (default: True)
- Models that fills often occur when market moves against you
- This is a simplified model - can be enhanced further

## How to Use

### Option 1: Test with Realistic Costs (Recommended)
```python
from Strategy_Backtesting import Backtester, run_sample_backtest
from order_manager import OrderManager

# Create order manager with transaction costs
order_manager = OrderManager(
    capital=50_000,
    commission_per_share=0.005,  # $0.005 per share
    commission_pct=0.001,  # 0.1% of notional
)

# Create backtester with realistic market modeling
backtester = Backtester(
    data_gateway=gateway,
    strategy=strategy,
    order_manager=order_manager,
    order_book=order_book,
    matching_engine=matching_engine,
    model_real_spreads=True,  # Model real spreads
    model_adverse_selection=True,  # Model adverse selection
    spread_bps=2.0,  # 2 basis points spread
)
```

### Option 2: Compare Old vs New
```python
# Old (unrealistic) backtest
backtester_old = Backtester(
    ...,
    model_real_spreads=False,
    model_adverse_selection=False,
)

# New (realistic) backtest
backtester_new = Backtester(
    ...,
    model_real_spreads=True,
    model_adverse_selection=True,
)

# Compare results
```

## Expected Impact

### Before (Unrealistic)
- No transaction costs
- Orders fill at limit price (no spread cost)
- No adverse selection
- **Result**: Strategy appears profitable

### After (Realistic)
- Transaction costs: ~$0.005 per share + 0.1%
- Spread cost: ~0.02% per trade
- Adverse selection: Market moves against you
- **Result**: Strategy likely shows losses or much smaller profits

## Next Steps

1. **Run backtests with new settings** to see realistic performance
2. **Adjust strategy parameters**:
   - Increase `base_edge` to account for costs
   - Reduce `base_qty` to reduce risk
   - Tighten `inventory_soft_limit` to reduce exposure
3. **Consider strategy changes**:
   - Only quote when edge > costs + risk premium
   - Add stop-losses on inventory
   - Reduce quoting in high volatility

## Parameter Recommendations

### For Stocks (e.g., AAPL)
```python
PennyInPennyOutStrategy(
    base_edge=0.03,  # Increased from 0.01 to account for costs
    base_qty=3,  # Reduced from 5 to reduce risk
    inventory_soft_limit=100,  # Reduced from 200
    fade_strength=0.03,  # Increased from 0.02
)
```

### For Crypto (e.g., BTC/USD)
```python
PennyInPennyOutStrategy(
    base_edge=10.0,  # Increased from 5.0
    base_qty=1,  # Keep small
    inventory_soft_limit=5,  # Very small for crypto volatility
    fade_strength=0.05,  # Stronger fade for volatile assets
)
```

## Key Insight

**Market-making is hard!** The edge you capture must exceed:
1. Transaction costs (commissions + fees)
2. Spread costs (you pay to cross)
3. Adverse selection (market moves against you)
4. Risk premium (compensation for holding inventory)

If your edge is only $0.01 but costs are $0.005 and adverse selection costs $0.003, you're only making $0.002 per trade. With 1000 trades, that's $2 profit - not much!

Consider:
- Increasing edge requirements
- Reducing trade frequency
- Better inventory management
- More sophisticated risk controls



