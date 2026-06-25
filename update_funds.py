import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

RESOURCES = {
    "gemel":    "a30dcbea-a1d2-482c-ae29-8f781f5025fb",
    "pension":  "6d47d6b5-cb08-488b-b333-f1e717b1e1bd",
    "policies": "d0b61e50-1e38-4d52-8067-de8b1ee37419"
}

COMPANIES = ["הראל", "אלטשולר שחם", "ילין לפידות", "הפניקס", "מיטב", "כלל", "מגדל", "מנורה מבטחים", "אנליסט", "מור"]

PRODUCTS = {
    "hishtalmut": {"title": "קרן השתלמות", "keyword": "השתלמות"},
    "gemel_inv":  {"title": "קופת גמל להשקעה", "keyword": "להשקעה"},
    "pension":    {"title": "קרן פנסיה מקיפה", "keyword": "פנסיה"},
    "policy":     {"title": "פוליסת חיסכון", "keyword": "חיסכון"}
}

TRACKS = {
    "sp500":   {"title": "מסלול עוקב S&P 500"},
    "equity":  {"title": "מסלול מנייתי טהור"},
    "general": {"title": "מסלול כללי / תלוי גיל"},
    "solid":   {"title": "מסלול אג\"ח / שקלי"}
}

def classify_track(fund_name, classification):
    text = (str(fund_name) + " " + str(classification)).lower()
    if any(k in text for k in ["s&p", "500", "אס אנד פי"]): return "sp500"
    if any(k in text for k in ["מניות", "מנייתי", "equity"]): return "equity"
    if any(k in text for k in ["אג\"ח", "אגח", "שקלי", "אגרות חוב", "כספית", "ממשלתי", "סולידי"]): return "solid"
    return "general"

def extract_clean_value(record, fields):
    for f in fields:
        v = record.get(f)
        if v is not None and str(v).strip() not in ("", "None"):
            try: return f"{float(v):.2f}"
            except: pass
    return "N/A"

def fetch_all_latest_data():
    latest_records = {}
    for res_key, res_id in RESOURCES.items():
        url = "https://data.gov.il/api/3/action/datastore_search"
        # שימוש בפרמטרים מובנים כדי למנוע קריסת URL עקב רווחים (כמו שהיה מקודם)
        params = {
            "resource_id": res_id,
            "limit": 8000,
            "sort": "REPORT_PERIOD desc"
        }
        try:
            resp = requests.get(url, params=params, timeout=20)
            if resp.status_code == 200:
                records = resp.json().get("result", {}).get("records", [])
                for rec in records:
                    fid = str(rec.get("FUND_ID", ""))
                    if fid and fid not in latest_records:
                        latest_records[fid] = rec 
        except Exception as e:
            log.error(f"Failed to fetch {res_key}: {e}")
    return latest_records

def build_dataset():
    latest_records = fetch_all_latest_data()
    matrix = []

    for prod_key, prod_info in PRODUCTS.items():
        product_node = {"id": prod_key, "title": prod_info["title"], "tracks": []}
        track_matches = {t_id: {c: None for c in COMPANIES} for t_id in TRACKS}
        
        for fid, rec in latest_records.items():
            c_name = rec.get("COMPANY_NAME", "")
            matched_company = next((c for c in COMPANIES if c in c_name), None)
            if not matched_company: continue
            
            fname = rec.get("FUND_NAME", "")
            fclass = rec.get("FUND_CLASSIFICATION", "")
            
            if prod_info["keyword"] not in fname and prod_info["keyword"] not in fclass:
                continue
            
            t_id = classify_track(fname, fclass)
            if track_matches[t_id][matched_company] is None:
                track_matches[t_id][matched_company] = rec

        for track_key, track_info in TRACKS.items():
            track_node = {"id": track_key, "title": track_info["title"], "funds": []}
            for company in COMPANIES:
                rec = track_matches[track_key][company]
                if rec:
                    ytd = extract_clean_value(rec, ["TSUA_MITCHILAT_SHANA", "TSUA_NOMINALIT_MITCHILAT_SHANA"])
                    y1 = extract_clean_value(rec, ["TSUA_SHANA_ACHARONA", "TSUA_NOMINALIT_SHANA_ACHARONA"])
                    y3 = extract_clean_value(rec, ["TSUA_3_SHANIM", "TSUA_NOMINALIT_3_SHANIM"])
                    y5 = extract_clean_value(rec, ["TSUA_5_SHANIM", "TSUA_NOMINALIT_5_SHANIM"])
                    
                    raw_date = str(rec.get('REPORT_PERIOD', ''))
                    updated_str = f"{raw_date[4:6]}/{raw_date[0:4]}" if len(raw_date) == 6 else "מעודכן"
                    
                    track_node["funds"].append({
                        "id": rec["FUND_ID"], "company": company, "name": rec["FUND_NAME"],
                        "YTD": ytd, "Year1": y1, "Year3": y3, "Year5": y5,
                        "last_updated": updated_str
                    })
                else:
                    track_node["funds"].append({
                        "id": None, "company": company, "name": f"לא נמצא מסלול פעיל",
                        "YTD": "N/A", "Year1": "N/A", "Year3": "N/A", "Year5": "N/A",
                        "last_updated": "N/A"
                    })
            product_node["tracks"].append(track_node)
        matrix.append(product_node)
    return matrix

if __name__ == "__main__":
    log.info("Starting Ultra-Fast Bulk Sync...")
    data = build_dataset()
    
    # מנגנון הגנה קריטי: אם לא נמשכו נתונים (תקלת תקשורת), הריצה נעצרת כדי לא למחוק את האתר!
    empty_check = sum(len(track["funds"]) for prod in data for track in prod["tracks"])
    if not data or empty_check == 0:
        log.error("Fatal Error: No data fetched from Gov API. Aborting save to protect current DB.")
        exit(1)
        
    with open("funds_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info("Market matrix successfully generated!")