import os
import pandas as pd
from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv


def load_environment():
    """Load environment variables and return credentials."""
    load_dotenv()
    database_user = os.getenv("DATABASE_USER")
    password = os.getenv("PASSWORD")
    database_name = os.getenv("DATABASE_NAME")
    collection_name = os.getenv("COLLECTION_NAME")


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
    """Read Excel sheet by exact date, or fallback to nearest earlier sheet."""
    xls = pd.ExcelFile(file_path, engine='openpyxl')
    available_sheets = xls.sheet_names

    if sheet_name and sheet_name in available_sheets:
        return pd.read_excel(xls, sheet_name=sheet_name)

    # Try fallback to the closest earlier sheet by date
    try:
        # Parse all sheet names that look like valid dates
        date_sheets = sorted(
            [s for s in available_sheets if _is_valid_date(s) and s <= sheet_name],
            reverse=True
        )
        if not date_sheets:
            raise ValueError("No valid sheet found on or before the target date.")
        closest_sheet = date_sheets[0]
        print(f"Sheet '{sheet_name}' not found. Using closest available: '{closest_sheet}'")
        return pd.read_excel(xls, sheet_name=closest_sheet)
    except Exception as e:
        raise ValueError(f"Failed to find a suitable sheet: {e}")


def _is_valid_date(s: str) -> bool:
    """Check if string is a valid YYYY-MM-DD date."""
    try:
        datetime.strptime(s, '%Y-%m-%d')
        return True
    except ValueError:
        return False

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
    top_company_cols = [f'Top {i}_Company' for i in range(1, 6)]
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
    """Fetch up to 'n' most recent documents <= date_str, or oldest & latest if n <= 0."""
    all_docs = list(collection.find(
        {"date": {"$lte": date_str}},
        sort=[("date", 1)]
    ))

    if not all_docs:
        raise RuntimeError(f"No documents found on or before {date_str}.")

    if len(all_docs) < 2:
        raise RuntimeError(f"Need at least 2 documents to compare, found only {len(all_docs)}")

    if n <= 0 or n > len(all_docs):
        selected = [all_docs[0], all_docs[-1]]
        print(f"Comparing oldest ({selected[0]['date']}) and latest ({selected[1]['date']})")
        return selected

    selected = all_docs[-n:]
    print(f"Comparing {n} most recent entries ending on {date_str}: {[doc['date'] for doc in selected]}")
    return selected


def compute_net_changes(docs: list) -> list:
    """Compute net changes between oldest and latest docs."""
    oldest, latest = docs[0], docs[-1]
    print(f"\n🔍 Comparing dates: {oldest['date']} → {latest['date']}")
    
    companies = set(oldest['companies']) | set(latest['companies'])
    print(f"🧾 Companies found: {len(companies)}\n")

    results = []
    for comp in sorted(companies):
        prev = oldest['companies'].get(comp, 0)
        curr = latest['companies'].get(comp, 0)
        diff = curr - prev

        print(f"{comp:<30} Prev: {prev:<3} Curr: {curr:<3} Diff: {diff:+}")

        if diff != 0:
            results.append({
                "Company": comp,
                "Previous": prev,
                "Current": curr,
                "Change": diff,
                "Trend": "↑" if diff > 0 else "↓"
            })

    if not results:
        print("\n⚠️ No net changes found between the two dates.")

    return sorted(results, key=lambda x: (-abs(x['Change']), -x['Change']))


def main():
    # Setup
    user, pwd, db_name, coll_name = load_environment()
    client = get_mongo_client(user, pwd)
    db = client[db_name]
    coll = db[coll_name]

    # Read today's sheet
    today_str = datetime.today().strftime('%Y-%m-%d')
    # today_str = "2025-06-03"
    df = read_sheet('Broker_Analysis.xlsx', sheet_name=today_str)

    # Process
    df = preprocess(df)
    counts = count_companies(df)

    # Save and upsert
    txt_file = save_counts_to_file(counts, today_str)
    print(f'Created file: {txt_file}')
    upsert_counts(coll, today_str, counts)

    # Compare historical data
    try:
        n = int(input("Enter number of recent dates to compare (0 for oldest vs latest): "))
    except ValueError:
        n = 0
    docs = fetch_recent_docs(coll, today_str, n)
    changes = compute_net_changes(docs)

    # Output results
    print("\nCompany Holdings Net Change (oldest → latest):")
    for e in changes:
        print(f"{e['Company']:<30} {e['Previous']:>3} → {e['Current']:>5}  ({e['Change']:+}, {e['Trend']})")


if __name__ == "__main__":
    main()
