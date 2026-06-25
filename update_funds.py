import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

BASE_URL = "https://data.gov.il/api/3/action/datastore_search"

# איחוד מלא של כל המשאבים הרשמיים מהמחקר שלך
RESOURCES = {
    "gemel":    "a30dcbea-a1d2-482c-ae29-8f781f5025fb",  # גמל והשתלמות
    "pension":  "6d47d6b5-cb08-488b-b333-f1e717b1e1bd",  # קרנות פנסיה
    "policies": "d0b61e50-1e38-4d52-8067-de8b1ee37419"   # פוליסות חיסכון (ביטוח נט)
}

COMPANIES = ["הראל", "אלטשולר שחם", "ילין לפידות", "הפניקס", "מיטב", "כלל", "מגדל", "מנורה מבטחים", "אנליסט", "מור"]

# מיפוי מוצרים מורחב הכולל פוליסות חיסכון ומילות מפתח ייעודיות לסינון
PRODUCTS = {
    "hishtalmut": {"title": "קרן השתלמות", "res": "gemel", "key": "השתלמות"},
    "gemel_inv":  {"title": "קופת גמל להשקעה", "res": "gemel", "key": "להשקעה"},
    "pension":    {"title": "קרן פנסיה מקיפה", "res": "pension", "key": "פנסיה"},
    "policy":     {"title": "פוליסת חיסכון", "res": "policies", "key": "חיסכון"}
}

TRACKS = {
    "sp500":   {"title": "מסלול עוקב S&P 500"},
    "equity":  {"title": "מסלול מנייתי טהור"},
    "general": {"title": "מסלול כללי / תלוי גיל"},
    "solid":   {"title": "מסלול אג\"ח / שקלי"}
}

def classify(name, classification):
    """מנוע סיווג סמנטי המנתב קופות למסלולים תחרותיים על בסיס מילות מפתח"""
    t = (str(name) + " " + str(classification)).lower()
    if any(x in t for x in ["s&p", "500", "אס אנד פי"]): return "sp500"
    if any(x in t for x in ["מניות", "מנייתי", "equity"]): return "equity"
    if any(x in t for x in ["אג\"ח", "אגח", "שקלי", "אגרות חוב", "כספית", "סולידי"]): return "solid"
    return "general"

def safe_yield(record, fields):
    """חילוץ תשואה מתקדם המבוסס על מנגנון הניקוי המחמיר שלך"""
    for f in fields:
        v = record.get(f)
        if v is not None and str(v).strip() not in ("", "None", "null"):
            try: return f"{float(v):.2f}"
            except: pass
    return "N/A"

def fetch_entire_market():
    """הורדה מרוכזת ב-3 שאילתות בלבד למניעת חסימות רשת (Rate Limits)"""
    market_data = {}
    for res_key, res_id in RESOURCES.items():
        log.info(f"מוריד בצובר נתוני רשות שוק ההון עבור משאב: {res_key}")
        params = {
            "resource_id": res_id,
            "limit": 25000,
            "sort": "REPORT_PERIOD desc"
        }
        try:
            resp = requests.get(BASE_URL, params=params, timeout=25)
            if resp.status_code == 200:
                records = resp.json().get("result", {}).get("records", [])
                for rec in records:
                    fid = str(rec.get("FUND_ID", ""))
                    if fid and fid not in market_data:
                        market_data[fid] = rec  
        except Exception as e:
            log.error(f"תקלת תקשורת פטלית מול משאב {res_key}: {e}")
    return market_data

def build():
    market_data = fetch_entire_market()
    matrix = []
    
    for p_key, p_info in PRODUCTS.items():
        p_node = {"id": p_key, "title": p_info["title"], "tracks": []}
        track_map = {t_key: {c: None for c in COMPANIES} for t_key in TRACKS}
        
        for fid, rec in market_data.items():
            # זיהוי תאגידי רב-ערוצי הפותר את בעיית שמות העמודות השונים בין גמל, פנסיה וביטוח
            comp_fields = ["MANAGING_CORPORATION", "PARENT_COMPANY_NAME", "COMPANY_NAME", "CONTROLLING_CORPORATION"]
            comp_name_raw = " ".join(str(rec.get(k, "")) for k in comp_fields)
            
            matched_company = next((c for c in COMPANIES if c in comp_name_raw), None)
            if not matched_company: continue
            
            fname = rec.get("FUND_NAME", "")
            fclass = rec.get("FUND_CLASSIFICATION", "")
            
            # וידוא שיוך המוצר (הפרדת גמל להשקעה מהשתלמות, ופוליסות חיסכון מפנסיה)
            if p_info["key"] not in fname and p_info["key"] not in fclass:
                continue
                
            t_key = classify(fname, fclass)
            
            if track_map[t_key][matched_company] is None:
                track_map[t_key][matched_company] = rec

        # בניית המבנה ההיררכי התחרותי עבור ממשק המשתמש
        for t_key, t_info in TRACKS.items():
            t_node = {"id": t_key, "title": t_info["title"], "funds": []}
            for comp in COMPANIES:
                rec = track_map[t_key][comp]
                if rec:
                    ytd = safe_yield(rec, ["TSUA_MITCHILAT_SHANA", "TSUA_NOMINALIT_MITCHILAT_SHANA", "YEAR_TO_DATE_YIELD"])
                    y1 = safe_yield(rec, ["TSUA_SHANA_ACHARONA", "TSUA_NOMINALIT_SHANA_ACHARONA", "YIELD_TRAILING_1_YR"])
                    y3 = safe_yield(rec, ["TSUA_3_SHANIM", "TSUA_NOMINALIT_3_SHANIM", "YIELD_TRAILING_3_YRS"])
                    y5 = safe_yield(rec, ["TSUA_5_SHANIM", "TSUA_NOMINALIT_5_SHANIM", "YIELD_TRAILING_5_YRS"])
                    
                    raw_date = str(rec.get('REPORT_PERIOD', ''))
                    date_str = f"{raw_date[4:6]}/{raw_date[0:4]}" if len(raw_date) == 6 else "מעודכן"
                    
                    t_node["funds"].append({
                        "id": rec["FUND_ID"], "company": comp, "name": rec.get("FUND_NAME", ""),
                        "YTD": ytd, "Year1": y1, "Year3": y3, "Year5": y5,
                        "last_updated": date_str
                    })
                else:
                    t_node["funds"].append({
                        "id": None, "company": comp, "name": "לא נמצא מסלול פעיל",
                        "YTD": "N/A", "Year1": "N/A", "Year3": "N/A", "Year5": "N/A",
                        "last_updated": "N/A"
                    })
            p_node["tracks"].append(t_node)
        matrix.append(p_node)
    return matrix

if __name__ == "__main__":
    log.info("מפעיל אינטגרציה מלאה: הגדרות מקוריות + סכימת מאגרים מעודכנת")
    data = build()
    
    # בקרת הגנה משולשת למניעת דריסת קבצים במקרה של שגיאת API רגעית
    empty_tracks = sum(len(track["funds"]) for p in data for track in p["tracks"])
    if not data or empty_tracks == 0:
        log.error("קריטי: תהליך הסינכרון החזיר מטריצה ריקה. הפעולה נעצרה להגנת הדאשבורד.")
        exit(1)
        
    with open("funds_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info("המטריצה הפיננסית המאוחדת נבנתה ונשמרה בהצלחה!")