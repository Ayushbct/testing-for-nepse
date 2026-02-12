import os
import pandas as pd
from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import sending_email
manual_input=False
sending_mail=True
email_subject=""
email_body=""

# List of brokers to check for persistent holdings
BROKERS_TO_CHECK = ["B58", "B94", "B62"]  # Modify this list to include/exclude brokers

# Number of sheets to check for persistence
NUM_SHEETS_TO_CHECK = 20  # Total number of previous sheets to analyze

# Minimum consecutive sheets a stock must appear in
MIN_CONSECUTIVE_SHEETS = 3  # Stocks must appear in at least this many consecutive sheets

def load_environment():
    """Load environment variables and return credentials."""
    load_dotenv()
    database_user = os.environ["DATABASE_USER"]
    password = os.environ["PASSWORD"]
    database_name = os.environ["DATABASE_NAME"]
    collection_name = os.environ["COLLECTION_NAME"]

    return database_user, password, database_name, collection_name


def get_mongo_client(user: str, pwd: str) -> MongoClient:
    """Initialize and return a MongoDB client."""
    uri = (
        f"mongodb+srv://{user}:{pwd}@nepsebrokeranalysis.kovphhm.mongodb.net/"
        f"?retryWrites=true&w=majority&appName=NepseBrokerAnalysis"
    )
    client = MongoClient(uri, server_api=ServerApi('1'))
    client.admin.command('ping')  # raises on failure
    return client


def read_sheet(file_path: str, sheet_name: str = None) -> pd.DataFrame:
    """Read Excel sheet by name or fall back to first sheet."""
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')
    except ValueError:
        sheets = pd.ExcelFile(file_path, engine='openpyxl').sheet_names
        return pd.read_excel(file_path, sheet_name=sheets[0], engine='openpyxl')


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Split top columns and convert amounts to numeric."""
    top_cols = ['Top 1', 'Top 2', 'Top 3', 'Top 4', 'Top 5']
    for col in top_cols:
        if col in df.columns:
            df[[f'{col}_Company', f'{col}_Code', f'{col}_Amount']] = (
                df[col].str.split('/', expand=True)
            )
    # Convert amount strings to float
    for col in df.columns:
        if col.endswith('_Amount'):
            df[col] = df[col].str.replace(',', '', regex=False).astype(float)
    return df


def count_companies(df: pd.DataFrame) -> pd.Series:
    """Count occurrences of companies in Top 1-5 columns."""
    top_company_cols = [f'Top {i}_Company' for i in range(1, 3)]
    all_companies = pd.concat([df[col] for col in top_company_cols if col in df])
    return all_companies.value_counts()


def save_counts_to_file(counts: pd.Series, date_str: str) -> str:
    """Save company counts to a text file and return filename."""
    filename = f'Top_5_Broker_holdings_{date_str}.txt'
    with open(filename, 'w') as f:
        f.write(counts.reset_index().to_string(index=False, header=False))
    return filename


def upsert_counts(collection, date_str: str, counts: pd.Series):
    """Upsert the counts into MongoDB with unique date index."""
    doc = {
        "date": date_str,
        "companies": counts.to_dict()
    }
    collection.create_index("date", unique=True)
    collection.update_one(
        {"date": date_str},
        {"$set": doc},
        upsert=True
    )


def fetch_recent_docs(collection, date_str: str, n: int = 0) -> list:
    """Fetch up to 'n' recent documents, or oldest & latest if n<=0."""
    all_docs = list(collection.find(
        {"date": {"$lte": date_str}},
        sort=[("date", 1)]
    ))
    if len(all_docs) < 2:
        raise RuntimeError(f"Need at least 2 documents to compare, found {len(all_docs)}")
    if n <= 0 or n > len(all_docs):
        return [all_docs[0], all_docs[-1]]
    return all_docs[-n:]


def compute_net_changes(docs: list) -> list:
    """Compute net changes between oldest and latest docs."""
    # Map dates and companies
    dates = [d["date"] for d in docs]
    oldest, latest = docs[0], docs[-1]
    companies = set(oldest['companies']) | set(latest['companies'])
    results = []
    for comp in sorted(companies):
        prev = oldest['companies'].get(comp, 0)
        curr = latest['companies'].get(comp, 0)
        diff = curr - prev
        if diff != 0 and (prev>=9 or curr>=9):
            results.append({
                "Company": comp,
                "Previous": prev,
                "Current": curr,
                "Change": diff,
                "Trend": "↑" if diff > 0 else "↓"
            })
        
    # sort by absolute change, positives first
    # print(f"\nOldest date:{oldest['date']} and Latest date:{latest['date']}")
    global email_subject
    email_subject=f"Broker Holdings change from ({oldest['date']} → {latest['date']}):"

    return sorted(
        results,
        key=lambda x: (-abs(x['Change']), -x['Change'])
    )


def get_broker_stocks(df: pd.DataFrame, top_n: int = 2) -> dict:
    """
    Extract stocks held by each broker from Top 1 to Top N.
    Returns dict: {broker_name: {stock1, stock2, ...}}
    """
    broker_stocks = {}
    
    # Assuming first column is broker name
    broker_col = df.columns[0]
    top_cols = [f'Top {i}' for i in range(1, top_n + 1)]
    
    for idx, row in df.iterrows():
        broker = row[broker_col]
        stocks = set()
        
        for col in top_cols:
            if col in df.columns and pd.notna(row[col]):
                # Extract stock name (before first "/")
                stock = str(row[col]).split('/')[0].strip()
                stocks.add(stock)
        
        if stocks:
            broker_stocks[broker] = stocks
    
    return broker_stocks


def get_previous_sheets(sheet_names: list, today_str: str, num_sheets: int = 3) -> list:
    """
    Get the previous N sheets before today_str.
    Returns list of sheet names sorted by date.
    """
    try:
        today_date = datetime.strptime(today_str, '%Y-%m-%d')
    except ValueError:
        return []
    
    # Filter sheets that are before today and sort them
    previous_sheets = []
    for sheet in sheet_names:
        try:
            sheet_date = datetime.strptime(sheet, '%Y-%m-%d')
            if sheet_date < today_date:
                previous_sheets.append((sheet_date, sheet))
        except ValueError:
            continue
    
    # Sort by date and get the last N sheets
    previous_sheets.sort(key=lambda x: x[0], reverse=True)
    return [sheet for _, sheet in previous_sheets[:num_sheets]][::-1]  # Reverse to chronological order


def find_persistent_stocks(dfs_list: list, sheet_dates: list, num_sheets: int = 3) -> dict:
    """
    Find stocks that persist for at least MIN_CONSECUTIVE_SHEETS consecutive sheets for brokers in BROKERS_TO_CHECK.
    Only checks Top 1 and Top 2.
    Returns dict: {broker: {(stock, consecutive_count): consecutive_count, ...}}
    """
    if len(dfs_list) == 0:
        return {}
    
    all_broker_stocks = []
    for df in dfs_list:
        all_broker_stocks.append(get_broker_stocks(df, top_n=2))
    
    persistent = {}
    
    for broker in BROKERS_TO_CHECK:
        # Collect all stocks this broker holds across all sheets
        all_stocks = set()
        for broker_holdings in all_broker_stocks:
            all_stocks.update(broker_holdings.get(broker, set()))
        
        # For each stock, find the longest consecutive streak
        stock_persistence = {}
        
        for stock in all_stocks:
            max_consecutive = 0
            current_consecutive = 0
            
            # Check each sheet in chronological order
            for broker_holdings in all_broker_stocks:
                if stock in broker_holdings.get(broker, set()):
                    current_consecutive += 1
                    max_consecutive = max(max_consecutive, current_consecutive)
                else:
                    current_consecutive = 0
            
            # Only include stocks that persist for at least MIN_CONSECUTIVE_SHEETS
            if max_consecutive >= MIN_CONSECUTIVE_SHEETS:
                stock_persistence[stock] = max_consecutive
        
        if stock_persistence:
            persistent[broker] = stock_persistence
    
    return persistent


def compare_today_with_persistent(today_df: pd.DataFrame, persistent_holdings: dict) -> dict:
    """
    Compare stocks from today's sheet (Top 1, 2, 3) with persistent holdings.
    Returns dict: {broker: {stock: consecutive_count}} for stocks appearing in both today and persistent
    """
    today_stocks = get_broker_stocks(today_df, top_n=3)
    
    comparison = {}
    
    for broker in BROKERS_TO_CHECK:
        today_broker_stocks = today_stocks.get(broker, set())
        persistent_broker_stocks = persistent_holdings.get(broker, {})
        
        # Find stocks that appear in both today's Top 1-3 and are persistent
        matching_stocks = {}
        for stock, consecutive_count in persistent_broker_stocks.items():
            if stock in today_broker_stocks:
                matching_stocks[stock] = consecutive_count
        
        if matching_stocks:
            comparison[broker] = matching_stocks
    
    return comparison


def main():
    # Setup
    user, pwd, db_name, coll_name = load_environment()
    client = get_mongo_client(user, pwd)
    db = client[db_name]
    coll = db[coll_name]

    
    
    

    xls = pd.ExcelFile('Broker_Analysis.xlsx')
    sheet_names = xls.sheet_names

    # Read today's sheet
    today_str = datetime.today().strftime('%Y-%m-%d')
    today_str="2026-02-11"
    sheet_date_str = sheet_names[0]

    # Convert to datetime for comparison
    today_date = datetime.strptime(today_str, '%Y-%m-%d')
    sheet_date = datetime.strptime(sheet_date_str, '%Y-%m-%d')  

    # Use today's date only if it's greater than the sheet name date
    if today_date > sheet_date:
        print(f'Today str {today_str} greater than latest sheet date {sheet_date_str}')
        # today_str = sheet_date_str  
        exit()
        
        
    
    
    # Read the appropriate sheet
    df = read_sheet('Broker_Analysis.xlsx', sheet_name=today_str)
    
    
    # Process
    df = preprocess(df)
    counts = count_companies(df)
    # print(counts.head(15))
    global email_body
    print("\nTop 15 Broker Holdings "+today_str+"\n")
    email_body += "Top 15 Broker Holdings "+today_str+"\n"
    for company, count in counts.head(15).items():
        line=f"{company:<30} {count:>5}"
        email_body +=line+"\n"
        print(line)

    # Save and upsert
    # txt_file = save_counts_to_file(counts, today_str)
    # print(f'Created file: {txt_file}')
    upsert_counts(coll, today_str, counts)
    

    # Compare historical data
    if os.getenv("GITHUB_ACTIONS") == "true":
        n=2
    else:
        try:
            if manual_input:
                n = int(input("Enter number of recent dates to compare: "))
            else:
                n=2
        except ValueError:
            n = 2

    
    
    # print("\n📅 Dates in collection:")
    # for doc in coll.find({}, {"date": 1, "_id": 0}).sort("date", 1):
    #     print(doc["date"])
    # print(f"\n🧭 Today_str: {today_str}")
    
    docs = fetch_recent_docs(coll,today_str, n)
    changes = compute_net_changes(docs)

    # Output results
    
    # email_subject=f"Company Holdings Net Change (oldest → latest):"
    
    print(f"\n{email_subject}\n")
    email_body +="\n"+"Change in Broker Holdings:"
    for e in changes:
        output=(f"{e['Company']:<30} {e['Previous']:>3} → {e['Current']:>5}  ({e['Change']:+}, {e['Trend']})")
        
        email_body +="\n"+output
        
        print(output)
    if len(email_body)==0:
        global sending_mail
        sending_mail=False
        output="No difference found with the filter"
        email_body +=output
        print(output)
    
    # NEW FEATURE: Check for persistent stocks and compare with today's holdings
    previous_sheet_names = get_previous_sheets(sheet_names, today_str, num_sheets=NUM_SHEETS_TO_CHECK)
    
    persistent_holdings = {}
    if len(previous_sheet_names) > 0:
        # Read the previous sheets
        previous_dfs = []
        for sheet_name in previous_sheet_names:
            df_prev = read_sheet('Broker_Analysis.xlsx', sheet_name=sheet_name)
            df_prev = preprocess(df_prev)
            previous_dfs.append(df_prev)
        
        # Find persistent stocks
        persistent_holdings = find_persistent_stocks(previous_dfs, previous_sheet_names, num_sheets=NUM_SHEETS_TO_CHECK)
    
    # COMPARISON: Compare today's stocks (Top 1-3) with persistent holdings
    print("\n" + "="*80)
    print(f"STOCKS IN TODAY'S TOP 1-3 WITH PERSISTENT HISTORY")
    print("="*80)
    
    if persistent_holdings and len(previous_sheet_names) > 0:
        comparison = compare_today_with_persistent(df, persistent_holdings)
        
        oldest_date = previous_sheet_names[0] if previous_sheet_names else "N/A"
        email_body += "\n\n" + f"Analysis Period: {oldest_date} to {today_str} ({len(previous_sheet_names)} sheets checked)"
        email_body += "\n" + f"Stocks in Today's Top 1-3 that have Persistent History:"
        
        print(f"\nAnalysis Period: {oldest_date} to {today_str} ({len(previous_sheet_names)} sheets)")
        
        if comparison:
            for broker, matching_stocks in sorted(comparison.items()):
                print(f"\n{broker}:")
                email_body += f"\n\n{broker}:"
                for stock, consecutive_count in sorted(matching_stocks.items()):
                    output = f"  {stock:<20} (previously held for {consecutive_count} consecutive sheets)"
                    print(output)
                    email_body += "\n" + output
        else:
            output = "No stocks from today's Top 1-3 found in the persistent holdings list."
            print(output)
            email_body += "\n" + output
    else:
        output = "Cannot compare: No persistent holdings data available."
        print(output)
        email_body += "\n" + output


    


if __name__ == "__main__":
    main()
    if sending_mail:
        sending_email.send_email(email_subject,email_body)
