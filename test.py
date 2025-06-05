import pandas as pd
from datetime import datetime

def calculate_active_day_return_large(file_path, stock_symbol, num_days):
    xls = pd.ExcelFile(file_path)
    sheet_names = xls.sheet_names

    sheets_with_dates = []
    for sn in sheet_names:
        try:
            dt = datetime.strptime(sn, "%Y_%m_%d")
            sheets_with_dates.append((dt, sn))
        except ValueError:
            pass
    sheets_with_dates.sort(reverse=True)  # newest first

    real_trading_days = []
    prev_close = None

    for sheet_date, sheet_name in sheets_with_dates:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, usecols=["Symbol", "Close"])
        except Exception:
            continue

        df_symbol = df[df['Symbol'] == stock_symbol]
        if df_symbol.empty:
            continue

        close_val = df_symbol.iloc[0]['Close']
        if isinstance(close_val, str):
            close_val = close_val.replace(',', '')
        try:
            close = float(close_val)
        except ValueError:
            continue

        if prev_close is None or close != prev_close:
            real_trading_days.append((sheet_date, close, sheet_name))
            prev_close = close

        # We want to read enough days for index num_days as well
        if len(real_trading_days) > num_days:
            break

    if len(real_trading_days) <= num_days:
        return None, f"Not enough active trading days. Found only {len(real_trading_days)} days, need at least {num_days + 1}."

    end_day = real_trading_days[0]          # newest day
    start_day = real_trading_days[num_days] # day after num_days-th day

    close_end = end_day[1]
    close_start = start_day[1]

    return_percent = ((close_end - close_start) / close_start) * 100

    result = (
        f"Return over {num_days} active trading days for {stock_symbol}: {return_percent:.2f}%\n"
        f"From {start_day[2]} (Close: {close_start}) to {end_day[2]} (Close: {close_end})"
    )
    return return_percent, result


# Example usage:
if __name__ == "__main__":
    file_path = "combined_excel.xlsx"
    symbol = "AKPL"
    days = 60

    ret, msg = calculate_active_day_return_large(file_path, symbol, days)
    print(msg)
