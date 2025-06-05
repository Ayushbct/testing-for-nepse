import pandas as pd
from datetime import datetime

def calculate_return_for_days(xls, sheet_info, symbol, days_needed):
    real_trading_days = []
    prev_close = None

    for sheet_date, sheet_name in sheet_info:
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, usecols=["Symbol", "Close"])
        except Exception:
            continue

        df_symbol = df[df["Symbol"] == symbol]
        if df_symbol.empty:
            continue

        close_val = df_symbol.iloc[0]["Close"]
        if isinstance(close_val, str):
            close_val = close_val.replace(",", "")
        try:
            close = float(close_val)
        except ValueError:
            continue

        if prev_close is None or close != prev_close:
            real_trading_days.append(close)
            prev_close = close

        if len(real_trading_days) > max(days_needed):
            break

    returns = {}
    for d in days_needed:
        if len(real_trading_days) > d:
            ret = ((real_trading_days[0] - real_trading_days[d]) / real_trading_days[d]) * 100
            returns[d] = f"{ret:.2f}%"
        else:
            returns[d] = "N/A"
    return returns

def generate_summary_excel(file_path, output_path="returns_summary.xlsx"):
    xls = pd.ExcelFile(file_path)
    sheet_names = xls.sheet_names

    # Sort sheets by date (latest first)
    sheet_info = []
    for sn in sheet_names:
        try:
            dt = datetime.strptime(sn, "%Y_%m_%d")
            sheet_info.append((dt, sn))
        except ValueError:
            continue
    sheet_info.sort(reverse=True)

    latest_sheet = sheet_info[0][1]
    latest_df = pd.read_excel(xls, sheet_name=latest_sheet, usecols=["Symbol"])
    symbols = latest_df["Symbol"].dropna().unique()

    days_map = {
        "One Day Return": 1,
        "One Week Return": 5,
        "One Month Return": 20,
        "Three Month Return": 70
    }

    summary_data = []
    for symbol in symbols:
        returns = calculate_return_for_days(xls, sheet_info, symbol, list(days_map.values()))
        row = {"Symbol": symbol}
        for label, days in days_map.items():
            row[label] = returns.get(days, "N/A")
        summary_data.append(row)

    result_df = pd.DataFrame(summary_data)
    result_df.to_excel(output_path, index=False)
    print(f"Summary written to: {output_path}")

# Example usage
if __name__ == "__main__":
    generate_summary_excel("combined_excel.xlsx")
