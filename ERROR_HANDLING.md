# Error Handling Improvements

## Problem
The Alpaca API was raising errors (from `alpaca_trade_api/rest.py` line 248) that weren't being caught properly, causing the trader to crash.

## Common Alpaca API Errors

1. **429 Rate Limit**: Too many requests
2. **401 Unauthorized**: Invalid API credentials
3. **403 Forbidden**: API permissions issue
4. **404 Not Found**: Resource doesn't exist (normal for positions)
5. **400 Bad Request**: Invalid order parameters (price, quantity, etc.)

## Improvements Made

### 1. **Better Error Handling in `get_latest_bar()`**
- Wraps API call in try/except
- Provides clear error messages
- Re-raises to be caught by outer handler

### 2. **Safer `cancel_open_orders()`**
- Handles errors when listing orders
- Handles errors when canceling individual orders
- Continues even if some orders fail to cancel

### 3. **Robust `submit_quote()`**
- Validates prices before submitting (not NaN, not negative)
- Validates quantities (must be positive integers)
- Handles errors for bid and ask separately
- Rounds prices to 2 decimal places (required by Alpaca)
- Provides detailed error messages with order details

### 4. **Improved `update_position()`**
- Only logs non-404 errors (404 is normal when no position exists)
- Handles missing positions gracefully

### 5. **Enhanced Main Loop Error Handling**
- Detects specific error types (rate limit, auth, etc.)
- Adjusts wait times based on error type:
  - Rate limit: 30 seconds
  - Auth errors: 60 seconds
  - Normal errors: 5-10 seconds
- Provides actionable error messages

### 6. **Pre-Submission Validation**
- Checks for NaN/invalid prices before submitting
- Validates quantities are positive
- Ensures ask > bid (valid spread)
- Disables invalid quotes instead of submitting them

## Error Messages You'll See

### Normal (Not Errors):
- `Note: Could not get position` - Normal when you have no position
- `⚠️  Resource not found` - Normal for missing resources

### Warnings (Non-Fatal):
- `⚠️  Invalid bid_price/ask_price` - Strategy returned invalid price
- `⚠️  Invalid spread` - Ask price <= bid price
- `⚠️  Rate limit hit` - Too many requests, waiting longer

### Errors (Need Attention):
- `❌ Authentication error` - Check API credentials
- `❌ Forbidden` - Check API permissions
- `Error submitting bid/ask order` - Order submission failed

## How to Debug

1. **Check API Credentials**:
   ```bash
   echo $ALPACA_API_KEY
   echo $ALPACA_API_SECRET
   ```

2. **Check Rate Limits**:
   - Alpaca has rate limits (200 requests per minute)
   - If you see rate limit errors, reduce polling frequency

3. **Check Order Parameters**:
   - Prices must be > 0 and not NaN
   - Quantities must be positive integers
   - Spread must be valid (ask > bid)

4. **Check Market Hours**:
   - Stock market is closed outside trading hours
   - Some operations may fail outside market hours

5. **Check Symbol Format**:
   - Stocks: "AAPL", "MSFT" (no "/")
   - Crypto: "BTC/USD" (with "/")

## Testing Error Handling

The improved error handling will:
- ✅ Continue running even if some API calls fail
- ✅ Provide clear error messages
- ✅ Handle rate limits gracefully
- ✅ Validate orders before submitting
- ✅ Prevent crashes from invalid data

## Next Steps

If you're still seeing errors:

1. **Check the error message** - It will tell you what's wrong
2. **Verify API credentials** - Make sure they're set correctly
3. **Check rate limits** - Reduce polling if hitting limits
4. **Validate strategy outputs** - Make sure strategy returns valid prices
5. **Check market hours** - Some operations only work during market hours

The trader should now be much more robust and continue running even when encountering API errors!



