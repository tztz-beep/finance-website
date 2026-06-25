import requests
import json
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

BASE_URL = "https://data.gov.il/api/3/action/datastore_search"

# מאגרי המידע המעודכנים (כפי שהוכחת שצריך)
RESOURCES = {
    "gemel": "a30dcbea-a1d2-482c-ae29-8f781f5025fb",
    "pension": "6d47d6b5-cb08-488b-b333-f1e717b1e1bd"
}

COMPANIES = ["הראל", "אלטשולר שחם", "ילין לפידות", "הפניקס", "מיטב", "כלל", "מגדל", "מנורה מבטחים", "אנליסט", "מור"]

PRODUCTS = {
    "hishtalmut": {"title": "קרן השתלמות", "res": "gemel", "key": "השתלמות"},
    "gemel_inv":  {"title": "קופת גמל להשקעה", "res": "gemel", "key": "להשקעה"},
    "pension":    {"title": "קרן פנסיה מקיפה", "res": "pension", "key": "פנסיה"}
}

TRACKS = {
    "sp500":   {"title": "מסלול עוקב S&P 500"},
    "equity":  {"title": "מסלול מנייתי טהור"},
    "general": {"title": "מסלול כללי / תלוי גיל"},
    "solid":   {"title": "מסלול אג\"ח / שקלי"}
}

def classify(name, classification):
    """מנוע סיווג טקסטואלי שמנתב כל קופה למסלול התחרותי הנכון"""
    t = (str(name) + " " + str(classification)).lower()
    if any(x in t for x in ["s&p", "500", "אס אנד פי"]): return "sp500"
    if any(x in t for x in ["מניות", "מנייתי", "equity"]): return "equity"
    if any(x in t for x in ["אג\"ח", "אגח", "שקלי", "אגרות חוב", "כספית", "סולידי"]): return "solid"
    return "general"

def safe_yield(record, fields):
    """חילוץ תשואה בטוח שמתעלם מערכים ריקים ומחזיר N/A במקרה חסר"""
    for f in fields:
        v = record.get(f)
        if v is not None and str(v).strip() not in ("", "None"):
            try: return f"{float(v):.2f}"
            except: pass
    return "N/A"

def build():
    matrix = []
    
    for p_key, p_info in PRODUCTS.items():
        log.info(f"מתחיל סריקה עבור: {p_info['title']}")
        p_node = {"id": p_key, "title": p_info["title"], "tracks": []}
        res_id = RESOURCES[p_info["res"]]
        
        # בניית שלד זמני לאיסוף הקופות הטובות ביותר
        track_map = {t_key: {c: None for c in COMPANIES} for t_key in TRACKS}
        
        # שלב 1: גילוי דינמי ומדויק של מספרי הקופות (מבוסס על הקוד המקורי שלך)
        for comp in COMPANIES:
            params = {
                "resource_id": res_id,
                "filters": json.dumps({"COMPANY_NAME": comp}),
                "limit": 300,
                "sort": "REPORT_PERIOD desc",
                "fields": "FUND_ID,FUND_NAME,FUND_CLASSIFICATION,REPORT_PERIOD"
            }
            try:
                resp = requests.get(BASE_URL, params=params, timeout=15)
                if resp.status_code == 200:
                    records = resp.json().get("result", {}).get("records", [])
                    for rec in records:
                        fname = rec.get("FUND_NAME", "")
                        fclass = rec.get("FUND_CLASSIFICATION", "")
                        if p_info["key"] not in fname and p_info["key"] not in fclass:
                            continue
                        t_key = classify(fname, fclass)
                        # שמירת הקופה הראשונה (העדכנית ביותר) שנמצאה עבור החברה והמסלול
                        if track_map[t_key][comp] is None:
                            track_map[t_key][comp] = str(rec.get("FUND_ID"))
            except Exception as e:
                log.error(f"Error fetching funds for {comp}: {e}")
            time.sleep(0.3) # השהייה קריטית למניעת חסימת IP
            
        # שלב 2: שאיבת התשואות הרשמיות עבור כל קופה שנמצאה
        for t_key, t_info in TRACKS.items():
            t_node = {"id": t_key, "title": t_info["title"], "funds": []}
            for comp in COMPANIES:
                fid = track_map[t_key][comp]
                if fid:
                    params = {
                        "resource_id": res_id,
                        "filters": json.dumps({"FUND_ID": fid}),
                        "sort": "REPORT_PERIOD desc",
                        "limit": 1
                    }
                    try:
                        resp = requests.get(BASE_URL, params=params, timeout=10)
                        if resp.status_code == 200:
                            records = resp.json().get("result", {}).get("records", [])
                            if records:
                                rec = records[0]
                                ytd = safe_yield(rec, ["TSUA_MITCHILAT_SHANA", "TSUA_NOMINALIT_MITCHILAT_SHANA"])
                                y1 = safe_yield(rec, ["TSUA_SHANA_ACHARONA", "TSUA_NOMINALIT_SHANA_ACHARONA"])
                                y3 = safe_yield(rec, ["TSUA_3_SHANIM", "TSUA_NOMINALIT_3_SHANIM"])
                                y5 = safe_yield(rec, ["TSUA_5_SHANIM", "TSUA_NOMINALIT_5_SHANIM"])
                                raw_date = str(rec.get('REPORT_PERIOD', ''))
                                date_str = f"{raw_date[4:6]}/{raw_date[0:4]}" if len(raw_date)==6 else "מעודכן"
                                
                                t_node["funds"].append({
                                    "id": fid, "company": comp, "name": rec.get("FUND_NAME", ""),
                                    "YTD": ytd, "Year1": y1, "Year3": y3, "Year5": y5,
                                    "last_updated": date_str
                                })
                                time.sleep(0.3)
                                continue
                    except Exception as e:
                        log.error(f"Error fetching yields for {fid}: {e}")
                        
                # אם חברה לא משווקת את המסלול או שהייתה שגיאה, מוסיפים נתון חסר נקי
                t_node["funds"].append({
                    "id": None, "company": comp, "name": "לא נמצא מסלול פעיל",
                    "YTD": "N/A", "Year1": "N/A", "Year3": "N/A", "Year5": "N/A",
                    "last_updated": "N/A"
                })
            p_node["tracks"].append(t_node)
        matrix.append(p_node)
    return matrix

if __name__ == "__main__":
    data = build()
    # מנגנון אל-כשל למניעת כתיבת קובץ ריק בעת נפילת תקשורת
    if not data or not data[0]["tracks"][0]["funds"]:
        log.error("Fatal Error: Matrix is empty.")
        exit(1)
    with open("funds_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info("Market matrix successfully generated!")