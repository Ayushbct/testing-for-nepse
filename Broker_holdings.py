import os
import pandas as pd
from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import sending_email
manual_input=False
sending_mail=False
email_subject=""
email_body=""

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


def main():
    # Setup
    user, pwd, db_name, coll_name = load_environment()
    client = get_mongo_client(user, pwd)
    db = client[db_name]
    coll = db[coll_name]

    # Read today's sheet
    today_str = datetime.today().strftime('%Y-%m-%d')
    # today_str = '2025-06-09'
    

    xls = pd.ExcelFile('Broker_Analysis.xlsx')
    sheet_names = xls.sheet_names

    # if today_str not in sheet_names:
    #     today_str = sheet_names[0]  # fallback to first sheet (assumed latest)
    
    # Read the appropriate sheet
    df = read_sheet('Broker_Analysis.xlsx', sheet_name=today_str)
    
    
    # Process
    df = preprocess(df)
    counts = count_companies(df)

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
    global email_body
    print(f"\n{email_subject}")
    
    for e in changes:
        output=(f"{e['Company']:<30} {e['Previous']:>3} → {e['Current']:>5}  ({e['Change']:+}, {e['Trend']})")
        
        email_body +="\n"+output
        
        print(output)
    if len(email_body)==0:
        output="No difference found with the filter"
        email_body +=output
        print(output)
    


if __name__ == "__main__":
    main()
    if sending_mail:
        sending_email.send_email(email_subject,email_body)
