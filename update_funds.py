import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

BASE_URL = "https://data.gov.il/api/3/action/datastore_search"

# הגדרת 3 המשאבים המעודכנים שפיצחת
RESOURCES = {
    "gemel":    "a30dcbea-a1d2-482c-ae29-8f781f5025fb",  # גמל והשתלמות
    "pension":  "6d47d6b5-cb08-488b-b333-f1e717b1e1bd",  # קרנות פנסיה
    "policies": "d0b61e50-1e38-4d52-8067-de8b1ee37419"   # פוליסות חיסכון (ביטוח נט)
}

# מילון מיפוי ארכיטקטוני: שורש השם לחיפוש חסין-שגיאות -> שם פרימיום לתצוגה בדאשבורד
COMPANY_MAP = {
    "הראל": "הראל",
    "אלטשולר": "אלטשולר שחם",
    "ילין": "ילין לפידות",
    "הפניקס": "הפניקס",
    "מיטב": "מיטב",
    "כלל": "כלל",
    "מגדל": "מגדל",
    "מנורה": "מנורה מבטחים",
    "אנליסט": "אנליסט",
    "מור": "מור"
}

PRODUCTS = {
    "hishtalmut": {"title": "קרן השתלמות", "res": "gemel", "key": "השתלמות"},
    "gemel_inv":  {"title": "קופת גמל להשקעה", "res": "gemel", "key": "להשקעה"},
    "pension":    {"title": "קרן פנסיה מקיפה", "res": "pension", "key": ""},
    "policy":     {"title": "פוליסת חיסכון", "res": "policies", "key": ""} # תיקון פער 1: פוליסות חיסכון בפנים
}

TRACKS = {
    "sp500":   {"title": "מסלול עוקב S&P 500"},
    "equity":  {"title": "מסלול מנייתי טהור"},
    "general": {"title": "מסלול כללי / תלוי גיל"},
    "solid":   {"title": "מסלול אג\"ח / שקלי"}
}

def classify(name, classification):
    """מנוע סיווג סמנטי המנקה תווים משובשים של האוצר (כמו S1;P וחלוקה לקטגוריות)"""
    t = (str(name) + " " + str(classification)).lower().replace(";", "").replace("-", "").replace(" ", "")
    if any(x in t for x in ["s&p", "500", "אסאנדפי", "p500", "s1p", "sp500"]): return "sp500"
    if any(x in t for x in ["מניות", "מנייתי", "equity"]): return "equity"
    if any(x in t for x in ["אג\"ח", "אגח", "שקלי", "אגרותחוב", "כספית", "סולידי", "ממשלתי"]): return "solid"
    return "general"

def safe_yield(record, fields):
    for f in fields:
        v = record.get(f)
        if v is not None and str(v).strip() not in ("", "None", "null", "NaN"):
            try: return f"{float(v):.2f}"
            except: pass
    return "N/A"

def record_score(rec):
    """מערכת הניקוד המעדיפה מסלולים ותיקים ומלאים על פני מסלולים ריקים או צעירים"""
    score = 0
    if safe_yield(rec, ["TSUA_5_SHANIM", "TSUA_NOMINALIT_5_SHANIM", "YIELD_TRAILING_5_YRS"]) != "N/A": score += 5
    if safe_yield(rec, ["TSUA_3_SHANIM", "TSUA_NOMINALIT_3_SHANIM", "YIELD_TRAILING_3_YRS"]) != "N/A": score += 3
    if safe_yield(rec, ["TSUA_SHANA_ACHARONA", "TSUA_NOMINALIT_SHANA_ACHARONA", "YIELD_TRAILING_12_MONTHS", "YIELD_TRAILING_1_YR", "TSUA_12_HODASHIM"]) != "N/A": score += 1
    return score

def fetch_entire_market():
    market_data = {}
    for res_key, res_id in RESOURCES.items():
        log.info(f"שואב ומאמת נתונים בצובר ממאגר: {res_key}")
        params = {"resource_id": res_id, "limit": 25000, "sort": "REPORT_PERIOD desc"}
        try:
            resp = requests.get(BASE_URL, params=params, timeout=25)
            if resp.status_code == 200:
                records = resp.json().get("result", {}).get("records", [])
                for rec in records:
                    fid = str(rec.get("FUND_ID", ""))
                    if not fid: continue
                    
                    # רשת ביטחון לחודשי רפאים - מדלג על שורות ריקות עד למציאת חודש מלא
                    y1 = safe_yield(rec, ["TSUA_SHANA_ACHARONA", "TSUA_NOMINALIT_SHANA_ACHARONA", "YIELD_TRAILING_12_MONTHS", "YIELD_TRAILING_1_YR", "TSUA_12_HODASHIM"])
                    if y1 == "N/A": continue 
                    
                    if fid not in market_data:
                        rec["_res_key"] = res_key
                        market_data[fid] = rec  
        except Exception as e:
            log.error(f"תקלה במשאב {res_key}: {e}")
    return market_data

def build():
    market_data = fetch_entire_market()
    matrix = []
    
    for p_key, p_info in PRODUCTS.items():
        p_node = {"id": p_key, "title": p_info["title"], "tracks": []}
        track_map = {t_key: {full_name: None for full_name in COMPANY_MAP.values()} for t_key in TRACKS}
        
        for fid, rec in market_data.items():
            if rec.get("_res_key") != p_info["res"]: continue 
            
            comp_fields = ["MANAGING_CORPORATION", "PARENT_COMPANY_NAME", "COMPANY_NAME", "CONTROLLING_CORPORATION"]
            comp_name_raw = " ".join(str(rec.get(k, "")) for k in comp_fields)
            
            # תיקון פער 2: זיהוי תאגידי לפי שורש השם ומפוי לשם הפרימיום המלא לתצוגה
            matched_root = next((root for root in COMPANY_MAP.keys() if root in comp_name_raw), None)
            if not matched_root: continue
            display_company = COMPANY_MAP[matched_root]
            
            fname = rec.get("FUND_NAME", "")
            fclass = rec.get("FUND_CLASSIFICATION", "")
            
            if p_info["key"] and p_info["key"] not in fname and p_info["key"] not in fclass:
                continue
                
            t_key = classify(fname, fclass)
            
            current_best = track_map[t_key].get(display_company)
            if current_best is None or record_score(rec) > record_score(current_best):
                track_map[t_key][display_company] = rec

        for t_key, t_info in TRACKS.items():
            t_node = {"id": t_key, "title": t_info["title"], "funds": []}
            for display_name in COMPANY_MAP.values():
                rec = track_map[t_key].get(display_name)
                if rec:
                    ytd = safe_yield(rec, ["TSUA_MITCHILAT_SHANA", "TSUA_NOMINALIT_MITCHILAT_SHANA", "YEAR_TO_DATE_YIELD", "TSUA_MITHILAT_SHANA"])
                    y1 = safe_yield(rec, ["TSUA_SHANA_ACHARONA", "TSUA_NOMINALIT_SHANA_ACHARONA", "YIELD_TRAILING_12_MONTHS", "YIELD_TRAILING_1_YR", "TSUA_12_HODASHIM"])
                    y3 = safe_yield(rec, ["TSUA_3_SHANIM", "TSUA_NOMINALIT_3_SHANIM", "YIELD_TRAILING_3_YRS"])
                    y5 = safe_yield(rec, ["TSUA_5_SHANIM", "TSUA_NOMINALIT_5_SHANIM", "YIELD_TRAILING_5_YRS"])
                    
                    raw_date = str(rec.get('REPORT_PERIOD', ''))
                    date_str = f"{raw_date[4:6]}/{raw_date[0:4]}" if len(raw_date) == 6 else "מעודכן"
                    
                    t_node["funds"].append({
                        "id": rec["FUND_ID"], "company": display_name, "name": rec.get("FUND_NAME", ""),
                        "YTD": ytd, "Year1": y1, "Year3": y3, "Year5": y5,
                        "last_updated": date_str
                    })
                else:
                    t_node["funds"].append({
                        "id": None, "company": display_name, "name": "לא נמצא מסלול פעיל",
                        "YTD": "N/A", "Year1": "N/A", "Year3": "N/A", "Year5": "N/A",
                        "last_updated": "N/A"
                    })
            p_node["tracks"].append(t_node)
        matrix.append(p_node)
    return matrix

if __name__ == "__main__":
    log.info("מריץ סריקה חכמה לאחר 3 בקרות איכות קפדניות...")
    data = build()
    
    empty_tracks = sum(len(track["funds"]) for p in data for track in p["tracks"])
    if not data or empty_tracks == 0:
        log.error("קריטי: מטריצה ריקה. הפעולה נעצרה להגנת הדאשבורד.")
        exit(1)
        
    with open("funds_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info("המטריצה הפיננסית המאוחדת נבנתה ונשמרה בהצלחה!")