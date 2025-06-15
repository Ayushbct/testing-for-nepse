import requests
import json

def fetch_broker_picks(session_cookie=None):
    """
    Fetches broker picks JSON from NepseAlpha.

    If an FSK (session) cookie is needed, pass it in `session_cookie`.
    """
    url = (
        "https://nepsealpha.com/trading-menu/prime-picks/broker_picks"
        "?fsk=o2MZpxGte5lRCzBS"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    cookies = {}
    if session_cookie:
        cookies["fsk"] = session_cookie

    resp = requests.get(url, headers=headers, cookies=cookies)
    resp.raise_for_status()
    return resp.json()

def parse_broker_picks(data):
    """
    Parses structured JSON data into a clean Python list.
    Adjust field names based on actual JSON structure.
    """
    picks = []
    for entry in data.get("data", []):
        picks.append({
            "symbol": entry.get("symbol"),
            "broker": entry.get("broker"),
            "rating": entry.get("rating"),
            "target_price": entry.get("target_price"),
            "stop_loss": entry.get("stop_loss"),
            "timestamp": entry.get("timestamp"),
        })
    return picks

def main():
    # Optionally replace with a valid fsk value if needed
    broker_data = fetch_broker_picks(session_cookie="o2MZpxGte5lRCzBS")
    parsed = parse_broker_picks(broker_data)
    print(json.dumps(parsed, indent=2))

if __name__ == "__main__":
    main()
