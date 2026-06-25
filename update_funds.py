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

# מספרי קופות (תוכל להשלים כאן את מספרי האוצר של קרנות הפנסיה כשיהיו לך אותם)
KNOWN_IDS = {
    # --- קרנות השתלמות ---
    "הראל_hishtalmut_equity": "5122", "אלטשולר שחם_hishtalmut_equity": "1375", "ילין לפידות_hishtalmut_equity": "539", "הפניקס_hishtalmut_equity": "1414",
    "הראל_hishtalmut_sp500": "1421", "ילין לפידות_hishtalmut_sp500": "1430", "מיטב_hishtalmut_sp500": "1390",
    "הראל_hishtalmut_general": "312", "אלטשולר שחם_hishtalmut_general": "114", "ילין לפידות_hishtalmut_general": "538", "מיטב_hishtalmut_general": "151",
    
    # --- קופות גמל להשקעה ---
    "הראל_gemel_inv_equity": "5444", "אלטשולר שחם_gemel_inv_equity": "5133", "הפניקס_gemel_inv_equity": "9842", "ילין לפידות_gemel_inv_equity": "5149",
    "הראל_gemel_inv_sp500": "9421", "אלטשולר שחם_gemel_inv_sp500": "9432", "מיטב_gemel_inv_sp500": "9440",
    "הראל_gemel_inv_general": "5321", "אלטשולר שחם_gemel_inv_general": "5132", "מיטב_gemel_inv_general": "5344",
    
    # --- קרנות פנסיה (דוגמאות להשלמה עתידית) ---
    "מנורה מבטחים_pension_general": "",
    "הראל_pension_general": ""
}

# הפיצול הארכיטקטוני למאגרי מידע בהתאם למוצר (כפי שחשפת)
DATABASES = {
    "gemel": [
        "a30dcbea-a1d2-482c-ae29-8f781f5025fb", # גמל 2024-היום
        "2016d770-f094-4a2e-983e-797c26479720", # גמל 2023
        "91c849ed-ddc4-472b-bd09-0f5486cea35c"  # גמל 1999-2022
    ],
    "pension": [
        "6d47d6b5-cb08-488b-b333-f1e717b1e1bd", # פנסיה 2024-היום
        "4694d5a7-5284-4f3d-a2cb-5887f43fb55e", # פנסיה 2023
        "a66926f3-e396-4984-a4db-75486751c2f7"  # פנסיה 1999-2022
    ]
}

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
                    "last_updated": "טרם הוזן מזהה אוצר"
                })
            product_node["tracks"].append(track_node)
        dashboard_data.append(product_node)
    return dashboard_data

def fetch_live_data():
    market_data = build_market_matrix()
    current_year = datetime.now().year
    
    for product in market_data:
        # ניתוב השאילתות למאגרים הנכונים לפי סוג המוצר
        target_db_list = DATABASES["pension"] if product["id"] == "pension" else DATABASES["gemel"]
        
        for track in product["tracks"]:
            for fund in track["funds"]:
                fid = fund["id"]
                if not fid: 
                    continue # חוסך קריאות רשת מיותרות על קופות שטרם מיפינו
                
                all_records = []
                for rid in target_db_list:
                    url = f"https://data.gov.il/api/3/action/datastore_search?resource_id={rid}&q={fid}&limit=70"
                    try:
                        resp = requests.get(url, timeout=10)
                        if resp.status_code == 200:
                            records = resp.json().get('result', {}).get('records', [])
                            all_records.extend(records)
                    except Exception as e:
                        print(f"Error fetching {fid} from resource {rid}: {e}")
                
                if all_records:
                    try:
                        df = pd.DataFrame(all_records)
                        yield_col = 'TSUA_NOMINALIT_BTOCH_TKOOFA' 
                        
                        if yield_col in df.columns and 'REPORT_PERIOD' in df.columns:
                            df[yield_col] = pd.to_numeric(df[yield_col], errors='coerce').fillna(0)
                            df['REPORT_PERIOD'] = pd.to_datetime(df['REPORT_PERIOD'].astype(str), format='%Y%m', errors='coerce')
                            df = df.dropna(subset=['REPORT_PERIOD']).drop_duplicates(subset=['REPORT_PERIOD'])
                            df = df.sort_values(by='REPORT_PERIOD', ascending=False)
                            
                            if not df.empty:
                                ytd_df = df[df['REPORT_PERIOD'].dt.year == current_year]
                                calc_cum = lambda d, m: f"{((1 + d.head(m)[yield_col] / 100).prod() - 1) * 100:.2f}"
                                
                                fund["YTD"] = calc_cum(ytd_df, len(ytd_df))
                                fund["Year1"] = calc_cum(df, 12)
                                fund["Year3"] = calc_cum(df, 36)
                                fund["Year5"] = calc_cum(df, 60)
                                
                                raw_date = df['REPORT_PERIOD'].dt.strftime('%m/%Y').iloc[0]
                                fund["last_updated"] = f"אומת ב-{raw_date}"
                    except Exception as e:
                        print(f"Error processing math for fund {fid}: {e}")

    with open('funds_data.json', 'w', encoding='utf-8') as f:
        json.dump(market_data, f, ensure_ascii=False, indent=4)
    print("Dual-Database (Gemel & Pension) synchronization completed.")

if __name__ == "__main__":
    fetch_live_data()