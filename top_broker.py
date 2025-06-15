import pandas as pd
from datetime import datetime
import os
import sending_email
manual_input=False
sending_mail=True
email_subject=""
email_body=""

def read_sheet(file_path: str, sheet_name: str = None) -> pd.DataFrame:
    """Read Excel sheet by name or fall back to first sheet."""
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
    except ValueError:
        sheets = pd.ExcelFile(file_path, engine='openpyxl').sheet_names
        return pd.read_excel(file_path, sheet_name=sheets[0], engine='openpyxl')




xls = pd.ExcelFile('Broker_Analysis.xlsx')
sheet_names = xls.sheet_names

if os.getenv("GITHUB_ACTIONS") == "true":
        today_str = datetime.today().strftime('%Y-%m-%d')
else:
        try:
            if manual_input:
                today_str = input("Enter date (yyyy-mm-dd) to calculate: ")
            else:
                today_str = datetime.today().strftime('%Y-%m-%d')     
        except ValueError:
            today_str = datetime.today().strftime('%Y-%m-%d')

# Read today's sheet
# today_str = datetime.today().strftime('%Y-%m-%d')

# Use today's date only if it's the first sheet name
if today_str not in sheet_names:
        print(f'{today_str} not found')
        today_str = sheet_names[0]  # fallback to first sheet (assumed latest)
        

# Read the appropriate sheet
df = read_sheet('Broker_Analysis.xlsx', sheet_name=today_str)

# Function to extract company name from "COMPANY/CODE/VALUE"
def extract_company(entry):
    if isinstance(entry, str) and "/" in entry:
        return entry.split('/')[0].strip()
    return None

# Columns to analyze
columns_to_use = ['Top 1', 'Top 2', 'Top 3']

# Extract company names per column
for col in columns_to_use:
    df[col + '_company'] = df[col].apply(extract_company)

# Combine all extracted company names into one Series
all_companies = pd.concat([df[col + '_company'] for col in columns_to_use])

# Get the top 10 most frequent companies
top_10_companies = all_companies.value_counts().head(10).index.tolist()

# Create an empty DataFrame with integer dtype
freq_df = pd.DataFrame(0, index=top_10_companies, columns=columns_to_use, dtype=int)

# Count appearances of each top company in each column
for company in top_10_companies:
    for col in columns_to_use:
        freq_df.loc[company, col] = df[col + '_company'].eq(company).sum()

# Display result

email_subject=f"Frequency of Top 10 companies in (Top 1, Top 2, Top 3): for {today_str}"
print(email_subject)
email_body += freq_df.to_string()
print(email_body)
if sending_mail:
     sending_email.send_email(email_subject,email_body)