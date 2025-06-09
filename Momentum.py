import pandas as pd
from datetime import datetime
import os

# Timeframe mapping
DAYS_MAP = {
    "One Day Return": 1,
    "One Week Return": 5,
    "One Month Return": 20,
    "Three Month Return": 60,
    
}

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

def get_sheet_dates(sheet_names, ref_date=None):
    sheets_with_dates = []
    for name in sheet_names:
        try:
            date = datetime.strptime(name, "%Y_%m_%d")
            if ref_date is None or date <= ref_date:
                sheets_with_dates.append((date, name))
        except ValueError:
            continue
    sheets_with_dates.sort(reverse=True)
    return sheets_with_dates

def generate_summary_excel_optimized(file_path, output_path=None, reference_date_str=None):
    ref_date = None
    if reference_date_str:
        try:
            ref_date = datetime.strptime(reference_date_str, "%Y_%m_%d")
        except ValueError:
            print("⚠️ Invalid reference date format. Use YYYY-MM-DD. Defaulting to latest date.")


    # Build dynamic output path
    os.makedirs("Results Momentum", exist_ok=True)
    filename = f"Custom Stock Momentum {reference_date_str}.xlsx"
    
    output_path = os.path.join("Results Momentum", filename)


    xls = pd.ExcelFile(file_path)
    sheet_dates = get_sheet_dates(xls.sheet_names, ref_date)

    if not sheet_dates:
        print("❌ No valid sheets found up to the reference date.")
        return

    print("📊 Building price history...")
    price_history = build_price_history(xls, sheet_dates)

    print("📈 Calculating returns...")
    symbols = list(price_history.keys())
    summary_rows = [{"Symbol": symbol} for symbol in symbols]

    # Get reference point index (i.e., most recent date on or before reference_date)
    for label, days in DAYS_MAP.items():
        for i, symbol in enumerate(symbols):
            history = price_history[symbol]
            if len(history) <= days:
                summary_rows[i][label] = "N/A"
                continue

            # Use the first date as the reference (most recent before or equal to ref_date)
            reference_index = 0
            if ref_date:
                for idx, (d, _) in enumerate(history):
                    if d <= ref_date:
                        reference_index = idx
                        break

            if reference_index + days >= len(history):
                summary_rows[i][label] = "N/A"
                continue

            end_price = history[reference_index][1]
            start_price = history[reference_index + days][1]
            ret = ((end_price - start_price) / start_price) * 100
            summary_rows[i][label] = f"{ret:.2f}%"

        print(f"✅ {label} computation completed.")



    for row in summary_rows:
        week = row.get("One Week Return", "N/A")
        month = row.get("One Month Return", "N/A")

        try:
            week_val = float(week.strip('%'))
            month_val = float(month.strip('%'))

            # Compute absolute difference
            row["Week-Month"] = f"{abs(abs(week_val) - abs(month_val)):.2f}%"

            # Check if Month > Week
            row["Month>Week"] = month_val > week_val

        except Exception:
            row["Week-Month"] = "N/A"
            row["Month>Week"] = "N/A"

    print("💾 Writing to Excel...")
    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_excel(output_path, index=False)
    print(f"🎉 Done: Output saved to {output_path}")


# Example usage
if __name__ == "__main__":
    
    # Use a specific reference date (e.g., May 25, 2025)
    reference_date_str=input("Enter date in format YYYY_MM_DD: ")
    generate_summary_excel_optimized("combined_excel.xlsx", reference_date_str=reference_date_str)

