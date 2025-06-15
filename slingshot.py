import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def load_symbol_data_from_excel(file_path, symbol):
    xls = pd.ExcelFile(file_path)
    combined_data = []

    for sheet in xls.sheet_names:
        df = xls.parse(sheet)

        # Strip whitespace from column names
        df.columns = df.columns.str.strip()

        if 'Symbol' not in df.columns:
            continue

        # Strip whitespace and uppercase symbols in the column to match exactly
        df['Symbol'] = df['Symbol'].astype(str).str.strip().str.upper()
        symbol = symbol.upper()

        symbol_data = df[df['Symbol'] == symbol].copy()
        if symbol_data.empty:
            continue

        try:
            # Parse date from sheet name
            symbol_data['Date'] = pd.to_datetime(sheet, format="%Y_%m_%d")
        except ValueError:
            print(f"Skipping sheet: {sheet} - invalid date format.")
            continue

        # Columns to clean: remove commas and convert to numeric
        cols_to_clean = ['Open', 'High', 'Low', 'Close', 'Vol']

        for col in cols_to_clean:
            if col in symbol_data.columns:
                symbol_data[col] = symbol_data[col].astype(str).str.replace(',', '')
                symbol_data[col] = pd.to_numeric(symbol_data[col], errors='coerce')

        # Drop rows with missing data after conversion
        symbol_data.dropna(subset=cols_to_clean, inplace=True)

        combined_data.append(symbol_data)

    if not combined_data:
        raise ValueError(f"No data found for symbol '{symbol}'")

    full_df = pd.concat(combined_data)
    full_df.sort_values('Date', inplace=True)
    full_df.reset_index(drop=True, inplace=True)

    return full_df

def calculate_sling_shot(df):
    df['EMA38'] = df['Close'].ewm(span=38, adjust=False).mean()
    df['EMA62'] = df['Close'].ewm(span=62, adjust=False).mean()

    df['Trend'] = np.where(df['EMA38'] > df['EMA62'], 'Up',
                   np.where(df['EMA38'] < df['EMA62'], 'Down', 'Neutral'))

    df['Aggressive_Long'] = (df['EMA38'] > df['EMA62']) & (df['Close'] < df['EMA38'])
    df['Aggressive_Short'] = (df['EMA38'] < df['EMA62']) & (df['Close'] > df['EMA38'])

    df['Cons_Long'] = (df['EMA38'] > df['EMA62']) & (df['Close'].shift(1) < df['EMA38']) & (df['Close'] > df['EMA38'])
    df['Cons_Short'] = (df['EMA38'] < df['EMA62']) & (df['Close'].shift(1) > df['EMA38']) & (df['Close'] < df['EMA38'])
    return df

def plot_sling_shot(df, symbol, filename="sling_shot_chart.png"):
    if df.empty:
        print(f"No data to plot for {symbol}")
        return

    fig, ax = plt.subplots(figsize=(16, 8))

    # Candle body colors: green if Close >= Open else red
    colors = ['green' if c >= o else 'red' for c, o in zip(df['Close'], df['Open'])]

    # Plot wicks
    ax.vlines(df['Date'], df['Low'], df['High'], color='black', linewidth=1)

    # Plot candle bodies
    ax.bar(df['Date'], df['Close'] - df['Open'], bottom=df['Open'], color=colors, width=0.6, edgecolor='black')

    # Plot EMA lines
    ax.plot(df['Date'], df['EMA38'], label='EMA38', color='orange', linewidth=1.5)
    ax.plot(df['Date'], df['EMA62'], label='EMA62', color='blue', linewidth=2)

    # Scatter for entries
    ax.scatter(df.loc[df['Aggressive_Long'], 'Date'], df.loc[df['Aggressive_Long'], 'Low'] * 0.995,
               label='Aggressive Long', marker='v', color='yellow', alpha=0.8)
    ax.scatter(df.loc[df['Aggressive_Short'], 'Date'], df.loc[df['Aggressive_Short'], 'High'] * 1.005,
               label='Aggressive Short', marker='^', color='yellow', alpha=0.8)

    ax.scatter(df.loc[df['Cons_Long'], 'Date'], df.loc[df['Cons_Long'], 'Low'] * 0.995,
               label='Conservative Long', marker='^', color='lime')
    ax.scatter(df.loc[df['Cons_Short'], 'Date'], df.loc[df['Cons_Short'], 'High'] * 1.005,
               label='Conservative Short', marker='v', color='red')

    # Annotate trend changes
    for i in range(1, len(df)):
        if df['Trend'].iloc[i] == 'Up' and df['Trend'].iloc[i - 1] != 'Up':
            ax.annotate('▲', (df['Date'].iloc[i], df['Low'].iloc[i] * 0.99), color='lime', fontsize=12, ha='center')
        elif df['Trend'].iloc[i] == 'Down' and df['Trend'].iloc[i - 1] != 'Down':
            ax.annotate('▼', (df['Date'].iloc[i], df['High'].iloc[i] * 1.01), color='red', fontsize=12, ha='center')

    # Date formatting
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.set_title(f"SlingShot System: {symbol}")
    ax.legend()
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(filename, dpi=300)
    plt.close()
    print(f"Saved chart as: {filename}")

if __name__ == "__main__":
    symbol = "NIFRA"  # Change to user input or desired symbol
    excel_file = "combined_excel.xlsx"

    df = load_symbol_data_from_excel(excel_file, symbol)
    df = calculate_sling_shot(df)
    plot_sling_shot(df, symbol, filename=f"sling_shot_{symbol}.png")
