import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

def load_symbol_data_from_excel(file_path, symbol):
    xls = pd.ExcelFile(file_path)
    combined_data = []

    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        if 'Symbol' not in df.columns:
            continue  # skip malformed sheets

        symbol_data = df[df['Symbol'] == symbol]
        if not symbol_data.empty:
            symbol_data = symbol_data.copy()
            symbol_data['Date'] = pd.to_datetime(sheet, format="%Y_%m_%d")

            combined_data.append(symbol_data)

    if not combined_data:
        raise ValueError(f"No data found for symbol '{symbol}'")

    full_df = pd.concat(combined_data)
    full_df.sort_values('Date', inplace=True)
    return full_df.reset_index(drop=True)

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
    fig, ax = plt.subplots(figsize=(16, 8))

    colors = ['green' if c >= o else 'red' for c, o in zip(df['Close'], df['Open'])]
    ax.bar(df['Date'], df['High'] - df['Low'], bottom=df['Low'], color='gray', width=0.5, alpha=0.3)
    ax.bar(df['Date'], df['Close'] - df['Open'], bottom=df['Open'], color=colors, width=0.5)

    ax.plot(df['Date'], df['EMA38'], label='EMA38', color='orange', linewidth=1.5)
    ax.plot(df['Date'], df['EMA62'], label='EMA62', color='blue', linewidth=2)

    ax.scatter(df['Date'][df['Aggressive_Long']], df['Low'][df['Aggressive_Long']] * 0.995,
               label='Aggressive Long', marker='v', color='yellow', alpha=0.8)
    ax.scatter(df['Date'][df['Aggressive_Short']], df['High'][df['Aggressive_Short']] * 1.005,
               label='Aggressive Short', marker='^', color='yellow', alpha=0.8)

    ax.scatter(df['Date'][df['Cons_Long']], df['Low'][df['Cons_Long']] * 0.995,
               label='Conservative Long', marker='^', color='lime')
    ax.scatter(df['Date'][df['Cons_Short']], df['High'][df['Cons_Short']] * 1.005,
               label='Conservative Short', marker='v', color='red')

    for i in range(1, len(df)):
        if df['Trend'].iloc[i] == 'Up' and df['Trend'].iloc[i-1] != 'Up':
            ax.annotate('▲', (df['Date'].iloc[i], df['Low'].iloc[i]*0.99), color='lime', fontsize=12, ha='center')
        elif df['Trend'].iloc[i] == 'Down' and df['Trend'].iloc[i-1] != 'Down':
            ax.annotate('▼', (df['Date'].iloc[i], df['High'].iloc[i]*1.01), color='red', fontsize=12, ha='center')

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.set_title(f"SlingShot System: {symbol}")
    ax.legend()
    plt.xticks(rotation=45)
    plt.grid()
    plt.tight_layout()

    plt.savefig(filename, dpi=300)
    plt.close()
    print(f"Saved chart as: {filename}")

# 🔁 MAIN: symbol input and processing
symbol = "NIFRA"  # ⬅️ Replace this with user input if needed

excel_file = "combined_excel.xlsx"
df = load_symbol_data_from_excel(excel_file, symbol)
df = calculate_sling_shot(df)
plot_sling_shot(df, symbol, filename=f"sling_shot_{symbol}.png")
