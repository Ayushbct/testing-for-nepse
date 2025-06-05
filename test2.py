import pandas as pd
from datetime import datetime

# Timeframe mapping
DAYS_MAP = {
    "One Day Return": 1,
    "One Week Return": 5,
    "One Month Return": 20,
    "Three Month Return": 60,
}

def get_sheet_dates(sheet_names):
    sheets_with_dates = []
    for name in sheet_names:
        try:
            date = datetime.strptime(name, "%Y_%m_%d")
            sheets_with_dates.append((date, name))
        except ValueError:
            continue
    sheets_with_dates.sort(reverse=True)
    return sheets_with_dates

def build_price_history(xls, sheet_dates):
    """Extracts price history for each symbol across active trading days."""
    price_history = {}
    last_prices = {}

    for date, sheet_name in sheet_dates:
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, usecols=["Symbol", "Close"])
        except Exception:
            continue

        for _, row in df.iterrows():
            symbol = row["Symbol"]
            close = row["Close"]
            if pd.isna(symbol) or pd.isna(close):
                continue

            if isinstance(close, str):
                close = close.replace(",", "")
            try:
                close = float(close)
            except ValueError:
                continue

            prev_close = last_prices.get(symbol)
            if prev_close != close:
                price_history.setdefault(symbol, []).append((date, close))
                last_prices[symbol] = close

    return price_history

def generate_summary_excel_optimized(file_path, output_path="returns_summary.xlsx"):
    xls = pd.ExcelFile(file_path)
    sheet_dates = get_sheet_dates(xls.sheet_names)

    print("📊 Building price history...")
    price_history = build_price_history(xls, sheet_dates)

    print("📈 Calculating returns...")
    symbols = list(price_history.keys())
    summary_rows = [{"Symbol": symbol} for symbol in symbols]

    for label, days in DAYS_MAP.items():
        for i, symbol in enumerate(symbols):
            history = price_history[symbol]
            prices = [c for _, c in history]
            if len(prices) > days:
                start, end = prices[days], prices[0]
                ret = ((end - start) / start) * 100
                summary_rows[i][label] = f"{ret:.2f}%"
            else:
                summary_rows[i][label] = "N/A"

        print(f"✅ {label} computation completed.")

    print("💾 Writing to Excel...")
    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_excel(output_path, index=False)
    print(f"🎉 Done: Output saved to {output_path}")

# Example usage
if __name__ == "__main__":
    generate_summary_excel_optimized("combined_excel.xlsx")
