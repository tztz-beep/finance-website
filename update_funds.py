import requests
import json
from datetime import datetime

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

KNOWN_IDS = {
    "הראל_hishtalmut_equity": "5122", "אלטשולר שחם_hishtalmut_equity": "1375", "ילין לפידות_hishtalmut_equity": "539", "הפניקס_hishtalmut_equity": "1414",
    "הראל_hishtalmut_sp500": "1421", "ילין לפידות_hishtalmut_sp500": "1430", "מיטב_hishtalmut_sp500": "1390",
    "הראל_hishtalmut_general": "312", "אלטשולר שחם_hishtalmut_general": "114", "ילין לפידות_hishtalmut_general": "538", "מיטב_hishtalmut_general": "151",
    "הראל_gemel_inv_equity": "5444", "אלטשולר שחם_gemel_inv_equity": "5133", "הפניקס_gemel_inv_equity": "9842", "ילין לפידות_gemel_inv_equity": "5149",
    "הראל_gemel_inv_sp500": "9421", "אלטשולר שחם_gemel_inv_sp500": "9432", "מיטב_gemel_inv_sp500": "9440",
    "הראל_gemel_inv_general": "5321", "אלטשולר שחם_gemel_inv_general": "5132", "מיטב_gemel_inv_general": "5344"
}

# מספיק לנו לפנות רק למאגרים העדכניים של 2024 - הם מכילים את העמודות המצטברות לאחור!
DATABASES = {
    "gemel": "a30dcbea-a1d2-482c-ae29-8f781f5025fb",
    "pension": "6d47d6b5-cb08-488b-b333-f1e717b1e1bd"
}

def extract_official_yield(record, field_names):
    """שולף את הנתון הרשמי ישירות מעמודות משרד האוצר ללא חישובים"""
    for field in field_names:
        val = record.get(field)
        if val is not None and str(val).strip() != "":
            try:
                return f"{float(val):.2f}"
            except:
                pass
    return "N/A"

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
                    "id": uid, "company": company, "name": fund_name,
                    "YTD": "N/A", "Year1": "N/A", "Year3": "N/A", "Year5": "N/A",
                    "last_updated": "טרם הוגדר מזהה" if not uid else "ממתין לנתון"
                })
            product_node["tracks"].append(track_node)
        dashboard_data.append(product_node)
    return dashboard_data

def fetch_live_data():
    market_data = build_market_matrix()
    
    for product in market_data:
        resource_id = DATABASES["pension"] if product["id"] == "pension" else DATABASES["gemel"]
        
        for track in product["tracks"]:
            for fund in track["funds"]:
                fid = fund["id"]
                if not fid: continue
                
                # משיכת השורה האחרונה בלבד!
                url = f"https://data.gov.il/api/3/action/datastore_search?resource_id={resource_id}&q={fid}&sort=REPORT_PERIOD desc&limit=1"
                try:
                    resp = requests.get(url, timeout=10)
                    if resp.status_code == 200:
                        records = resp.json().get('result', {}).get('records', [])
                        if records:
                            latest_record = records[0]
                            
                            # שאיבת נתוני האמת הרשמיים
                            fund["YTD"] = extract_official_yield(latest_record, ['TSUA_MITCHILAT_SHANA', 'TSUA_NOMINALIT_MITCHILAT_SHANA'])
                            fund["Year1"] = extract_official_yield(latest_record, ['TSUA_SHANA_ACHARONA', 'TSUA_NOMINALIT_SHANA_ACHARONA'])
                            fund["Year3"] = extract_official_yield(latest_record, ['TSUA_3_SHANIM', 'TSUA_NOMINALIT_3_SHANIM'])
                            fund["Year5"] = extract_official_yield(latest_record, ['TSUA_5_SHANIM', 'TSUA_NOMINALIT_5_SHANIM'])
                            
                            raw_date = str(latest_record.get('REPORT_PERIOD', ''))
                            if len(raw_date) == 6:
                                fund["last_updated"] = f"{raw_date[4:6]}/{raw_date[0:4]}"
                except Exception as e:
                    print(f"Error fetching exact data for {fund['company']} - {fid}: {e}")

    with open('funds_data.json', 'w', encoding='utf-8') as f:
        json.dump(market_data, f, ensure_ascii=False, indent=4)
    print("Official pre-calculated synchronization completed.")

if __name__ == "__main__":
    fetch_live_data()