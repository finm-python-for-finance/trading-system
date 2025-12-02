# Setting Up Alpaca API Keys

This guide shows how to set up your Alpaca API keys as environment variables.

## Step 1: Get Your API Keys from Alpaca

1. Go to [Alpaca Paper Trading Dashboard](https://app.alpaca.markets/paper/dashboard/overview)
2. Log in to your account
3. Navigate to **Your API Keys** section
4. Copy your **API Key ID** and **Secret Key**

## Step 2: Set Environment Variables

### Option A: Permanent Setup (Recommended)

Add the keys to your `~/.zshrc` file so they're available in all terminal sessions:

```bash
# Open your .zshrc file in a text editor
nano ~/.zshrc
# or
code ~/.zshrc  # if you use VS Code
```

Add these lines at the end of the file (replace with your actual keys):

```bash
# Alpaca API Keys
export ALPACA_API_KEY='your_api_key_here'
export ALPACA_API_SECRET='your_api_secret_here'
```

Save the file, then reload your shell configuration:

```bash
source ~/.zshrc
```

### Option B: Temporary Setup (Current Session Only)

Run these commands in your terminal:

```bash
export ALPACA_API_KEY='your_api_key_here'
export ALPACA_API_SECRET='your_api_secret_here'
```

**Note:** These will only last for the current terminal session.

## Step 3: Verify Setup

Test that the variables are set correctly:

```bash
echo $ALPACA_API_KEY
echo $ALPACA_API_SECRET
```

You should see your API keys printed (be careful not to share these!).

## Step 4: Test the Trader

Now you can run the forex trader:

```bash
python alpaca_fx_trader.py
```

## Security Notes

⚠️ **Important:**
- Never commit your API keys to git
- Never share your API keys publicly
- The `.zshrc` file is in your home directory and should not be shared
- Consider using a `.env` file with `python-dotenv` for more secure key management in projects

## Alternative: Using a .env File (More Secure)

If you prefer not to set global environment variables, you can use a `.env` file:

1. Install python-dotenv:
   ```bash
   pip install python-dotenv
   ```

2. Create a `.env` file in your project directory:
   ```
   ALPACA_API_KEY=your_api_key_here
   ALPACA_API_SECRET=your_api_secret_here
   ```

3. Add `.env` to your `.gitignore` file

4. Modify the trader script to load from `.env`:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```



