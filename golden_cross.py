import pandas as pd
import numpy as np
from openpyxl import load_workbook
from concurrent.futures import ThreadPoolExecutor

# --- CONFIG ---
excel_path = "combined_excel.xlsx"
short_window = 20
long_window = 50
lookback_days = long_window + 100  # Read just enough data for moving averages
recent_window = 30  # Look for crosses within last 5 days

# --- STEP 1: Read only latest N sheets ---
wb = load_workbook(excel_path, read_only=True)
sheet_names = wb.sheetnames  # Already in order from newest to oldest
selected_sheets = sheet_names[:lookback_days]


def read_sheet(sheet_name):
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, usecols=["Symbol", "Close"], engine="openpyxl")
        df.columns = df.columns.str.strip()  # Remove any whitespace
        df['Date'] = pd.to_datetime(sheet_name, format="%Y_%m_%d")
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        return df.dropna(subset=['Symbol', 'Close'])
    except Exception as e:
        print(f"Skipping {sheet_name} due to error: {e}")
        return pd.DataFrame()

# --- STEP 2: Read all selected sheets in parallel ---
with ThreadPoolExecutor() as executor:
    dfs = list(executor.map(read_sheet, selected_sheets))

combined_df = pd.concat(dfs).sort_values(['Symbol', 'Date'])
# Sort before deduplication
combined_df = combined_df.sort_values(['Symbol', 'Date'])

# Remove duplicate rows per Symbol where Close hasn't changed from previous day
combined_df['Prev_Close'] = combined_df.groupby('Symbol')['Close'].shift(1)
combined_df['Same_Close_As_Before'] = combined_df['Close'] == combined_df['Prev_Close']

# Keep rows only where the price changed (or it's the first one for the symbol)
filtered_df = combined_df[(~combined_df['Same_Close_As_Before']) | (combined_df['Prev_Close'].isna())]

# Drop helper columns
filtered_df = filtered_df.drop(columns=['Prev_Close', 'Same_Close_As_Before'])
start_date = filtered_df['Date'].min().date()
end_date = filtered_df['Date'].max().date()
print(f"\n📅 Data range used for Golden Cross calculation: {start_date} to {end_date}")



# --- STEP 3: Golden Cross Detection ---
def detect_golden_cross(df):
    if len(df) < long_window:
        df['GoldenCross'] = False
        return df

    df = df.sort_values('Date')
    df['MA50'] = df['Close'].rolling(window=short_window).mean()
    df['MA200'] = df['Close'].rolling(window=long_window).mean()

    df['GoldenCross'] = (
        (df['MA50'] > df['MA200']) &
        (df['MA50'].shift(1) <= df['MA200'].shift(1))
    )
    return df


processed = filtered_df.groupby('Symbol', group_keys=False).apply(detect_golden_cross)



# --- STEP 4: Find golden crosses in the most recent few days ---
latest_date = processed['Date'].max()
# Get the last N unique trading dates
unique_dates = processed['Date'].drop_duplicates().sort_values(ascending=False)
recent_unique_dates = unique_dates[:recent_window]

# Now find golden crosses only in those truly distinct trading days
recent_crosses = processed[
    (processed['Date'].isin(recent_unique_dates)) & (processed['GoldenCross'])
]

# --- Output results ---
# ... after filtering and processing your data ...

# Identify recent crosses
golden_symbols = recent_crosses['Symbol'].unique()

print(f"\n🟡 Golden Cross detected in last {recent_window} unique trading days (up to {recent_unique_dates.max().date()}):")
print(f"Symbols: {list(golden_symbols)}")

# Print dates per symbol
if recent_crosses.empty:
    print("\nNo Golden Cross detected in the recent window.")
else:
    print("\n🟡 Golden Cross formed on these dates:")
    for symbol, group in recent_crosses.groupby('Symbol'):
        dates = group['Date'].dt.date.tolist()
        dates_str = ", ".join(str(d) for d in dates)
        print(f" - {symbol}: {dates_str}")
