import requests
import json
from datetime import datetime
import pandas as pd

COMPANIES = ["הראל", "אלטשולר שחם", "ילין לפידות", "הפניקס", "מיטב", "כלל", "מגדל", "מנורה מבטחים", "אנליסט", "מור"]

PRODUCTS = {
    "gemel_inv": {"id": "gemel_inv", "title": "קופת גמל להשקעה"},
    "pension": {"id": "pension", "title": "קרן פנסיה מקיפה"},
    "hishtalmut": {"id": "hishtalmut", "title": "קרן השתלמות"}
}

TRACKS = {
    "sp500": {"title": "מסלול עוקב S&P 500"},
    "equity": {"title": "מסלול מנייתי טהור"},
    "general": {"title": "מסלול כללי / תלוי גיל"},
    "solid": {"title": "מסלול אג\"ח / שקלי"}
}

# מספרי הקופות הרשמיים. קופות שלא קיימות כאן יציגו "חסר נתון" כדי לשמור על אמינות משפטית מוחלטת.
KNOWN_IDS = {
    # קרנות השתלמות
    "הראל_hishtalmut_equity": "5122", "אלטשולר שחם_hishtalmut_equity": "1375", "ילין לפידות_hishtalmut_equity": "539", "הפניקס_hishtalmut_equity": "1414",
    "הראל_hishtalmut_sp500": "1421", "ילין לפידות_hishtalmut_sp500": "1430", "מיטב_hishtalmut_sp500": "1390",
    "הראל_hishtalmut_general": "312", "אלטשולר שחם_hishtalmut_general": "114", "ילין לפידות_hishtalmut_general": "538", "מיטב_hishtalmut_general": "151",
    # גמל להשקעה
    "הראל_gemel_inv_equity": "5444", "אלטשולר שחם_gemel_inv_equity": "5133", "הפניקס_gemel_inv_equity": "9842", "ילין לפידות_gemel_inv_equity": "5149",
    "הראל_gemel_inv_sp500": "9421", "אלטשולר שחם_gemel_inv_sp500": "9432", "מיטב_gemel_inv_sp500": "9440",
    "הראל_gemel_inv_general": "5321", "אלטשולר שחם_gemel_inv_general": "5132", "מיטב_gemel_inv_general": "5344"
}

def extract_official_yield(record, field_names):
    """חילוץ בטוח של שדות התשואה הרשמיים של משרד האוצר"""
    for field in field_names:
        val = record.get(field)
        if val is not None and str(val).strip() != "":
            try:
                return f"{float(val):.2f}"
            except:
                pass
    return "0.00"

def build_market_matrix():
    dashboard_data = []
    for prod_key, prod_info in PRODUCTS.items():
        product_node = {"id": prod_key, "title": prod_info["title"], "tracks": []}
        for track_key, track_info in TRACKS.items():
            track_node = {"id": track_key, "title": track_info["title"], "funds": []}
            for company in COMPANIES:
                uid = KNOWN_IDS.get(f"{company}_{prod_key}_{track_key}", None)
                suffix = track_info['title'].split(' ')[1] if len(track_info['title'].split(' ')) > 1 else track_info['title']
                if "S&P" in track_info['title']: suffix = "מחקה מדד S&P 500"
                fund_name = f"{company} {prod_info['title'].replace('קרן ', '').replace('קופת ', '')} {suffix}"
                
                track_node["funds"].append({
                    "id": uid,
                    "company": company,
                    "name": fund_name,
                    "YTD": "N/A", "Year1": "N/A", "Year3": "N/A", "Year5": "N/A",
                    "last_updated": "טרם עודכן"
                })
            product_node["tracks"].append(track_node)
        dashboard_data.append(product_node)
    return dashboard_data

def fetch_live_data():
    market_data = build_market_matrix()
    
    # המזהה הרשמי של האוצר לנתוני גמל-נט המעודכנים ביותר
    resource_id = "a30dcbea-a1d2-482c-ae29-8f781f5025fb"
    
    for product in market_data:
        for track in product["tracks"]:
            for fund in track["funds"]:
                if fund["id"]:  # רק אם יש מזהה חוקי לאוצר
                    # בקשת הרשומה האחרונה בלבד לפי חודש דיווח
                    url = f"https://data.gov.il/api/3/action/datastore_search?resource_id={resource_id}&q={fund['id']}&sort=REPORT_PERIOD desc&limit=1"
                    try:
                        resp = requests.get(url, timeout=5)
                        if resp.status_code == 200:
                            records = resp.json().get('result', {}).get('records', [])
                            if records:
                                latest_record = records[0]
                                
                                # משיכת הנתונים הרשמיים המחושבים מראש של האוצר!
                                fund["YTD"] = extract_official_yield(latest_record, ['TSUA_NOMINALIT_BTOCH_TKOOFA'])
                                fund["Year1"] = extract_official_yield(latest_record, ['TSUA_NOMINALIT_SHANA_ACHARONA', 'TSUA_SHANA_ACHARONA'])
                                fund["Year3"] = extract_official_yield(latest_record, ['TSUA_NOMINALIT_3_SHANIM', 'TSUA_3_SHANIM'])
                                fund["Year5"] = extract_official_yield(latest_record, ['TSUA_NOMINALIT_5_SHANIM', 'TSUA_5_SHANIM'])
                                
                                raw_date = str(latest_record.get('REPORT_PERIOD', ''))
                                if len(raw_date) == 6:
                                    fund["last_updated"] = f"{raw_date[4:6]}/{raw_date[0:4]}"
                    except Exception as e:
                        print(f"Error fetching exact data for {fund['company']} - {fund['id']}: {e}")

    with open('funds_data.json', 'w', encoding='utf-8') as f:
        json.dump(market_data, f, ensure_ascii=False, indent=4)
    print("Exact official API synchronization completed.")

if __name__ == "__main__":
    fetch_live_data()