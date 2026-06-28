import requests
import json
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

BASE_URL = "https://data.gov.il/api/3/action/datastore_search"

# שני המאגרים הרשמיים והחזקים ביותר משרד האוצר
RESOURCES = {
    "gemel": "a30dcbea-a1d2-482c-ae29-8f781f5025fb",    # גמל והשתלמות
    "pension": "6d47d6b5-cb08-488b-b333-f1e717b1e1bd"   # קרנות פנסיה
}

COMPANY_MAP = {
    "הראל": "הראל", "אלטשולר": "אלטשולר שחם", "ילין": "ילין לפידות",
    "הפניקס": "הפניקס", "מיטב": "מיטב", "כלל": "כלל", "מגדל": "מגדל",
    "מנורה": "מנורה מבטחים", "אנליסט": "אנליסט", "מור": "מור"
}

PRODUCTS = {
    "hishtalmut": {"title": "קרן השתלמות", "res": "gemel", "key": "השתלמות"},
    "gemel_inv":  {"title": "קופת גמל להשקעה", "res": "gemel", "key": "להשקעה"},
    "pension":    {"title": "קרן פנסיה מקיפה", "res": "pension", "key": ""}
}

TRACKS = {
    "sp500":   {"title": "מסלול עוקב S&P 500"},
    "equity":  {"title": "מסלול מנייתי טהור"},
    "general": {"title": "מסלול כללי / תלוי גיל"},
    "solid":   {"title": "מסלול אג\"ח / שקלי"}
}

def classify(name, classification):
    """מנוע סיווג נקי המסנן רעשים ומקטלג רק מסלולים תחרותיים ומשותפים"""
    t = (str(name) + " " + str(classification)).lower().replace(" ", "")
    
    # סינון קפדני של מסלולים לא רלוונטיים כדי שלא ישתרבבו לטבלה
    if any(x in t for x in ["ילד", "ילדים", "פיצויים", "מטרה", "בטוחה", "מרכזית"]):
        return None
        
    if any(x in t for x in ["s&p", "500", "p500", "sp500", "אסאנדפי"]): return "sp500"
    if any(x in t for x in ["מניות", "מנייתי", "equity"]): return "equity"
    if any(x in t for x in ["אג\"ח", "אגח", "שקלי", "אגרותחוב", "כספית", "סולידי", "ממשלתי"]): return "solid"
    return "general"

def safe_yield(record, fields):
    for f in fields:
        v = record.get(f)
        if v is not None and str(v).strip() not in ("", "None", "null", "NaN", "nan"):
            try: return f"{float(v):.2f}"
            except: pass
    return "N/A"

def fetch_market_clean():
    """מוריד את נתוני החודש האחרון בלבד בצורה קלה ומהירה למניעת חסימות שרת"""
    market_data = {}
    for res_key, res_id in RESOURCES.items():
        log.info(f"שואב מנה עדכנית ממאגר: {res_key}")
        params = {
            "resource_id": res_id,
            "limit": 5000, # כמות אופטימלית שתופסת בדיוק את הדיווחים האחרונים של כל החברות
            "sort": "REPORT_PERIOD desc"
        }
        try:
            resp = requests.get(BASE_URL, params=params, timeout=20)
            if resp.status_code == 200:
                records = resp.json().get("result", {}).get("records", [])
                for rec in records:
                    fid = str(rec.get("FUND_ID", ""))
                    if fid and fid not in market_data:
                        rec["_res_key"] = res_key
                        market_data[fid] = rec
        except Exception as e:
            log.error(f"שגיאה בשאיבת משאב {res_key}: {e}")
    return market_data

def build():
    market_data = fetch_market_clean()
    matrix = []
    
    for p_key, p_info in PRODUCTS.items():
        p_node = {"id": p_key, "title": p_info["title"], "tracks": []}
        track_map = {t_key: {full_name: None for full_name in COMPANY_MAP.values()} for t_key in TRACKS}
        
        for fid, rec in market_data.items():
            if rec.get("_res_key") != p_info["res"]: continue 
            
            # סריקה רב-ערוצית של שם התאגיד המנהל
            comp_fields = ["MANAGING_CORPORATION", "PARENT_COMPANY_NAME", "COMPANY_NAME"]
            comp_name_raw = " ".join(str(rec.get(k, "")) for k in comp_fields)
            
            matched_root = next((root for root in COMPANY_MAP.keys() if root in comp_name_raw), None)
            if not matched_root: continue
            display_company = COMPANY_MAP[matched_root]
            
            fname = rec.get("FUND_NAME", "")
            fclass = rec.get("FUND_CLASSIFICATION", "")
            
            if p_info["key"] and p_info["key"] not in fname and p_info["key"] not in fclass: 
                continue
                
            t_key = classify(fname, fclass)
            if not t_key: continue # דילוג על מסלולי רעש (כמו חיסכון לכל ילד)
            
            if track_map[t_key][display_company] is None:
                track_map[t_key][display_company] = rec

        for t_key, t_info in TRACKS.items():
            t_node = {"id": t_key, "title": t_info["title"], "funds": []}
            for display_name in COMPANY_MAP.values():
                rec = track_map[t_key].get(display_name)
                if rec:
                    ytd = safe_yield(rec, ["TSUA_MITCHILAT_SHANA", "TSUA_NOMINALIT_MITCHILAT_SHANA", "YEAR_TO_DATE_YIELD"])
                    y3 = safe_yield(rec, ["TSUA_3_SHANIM", "TSUA_NOMINALIT_3_SHANIM", "YIELD_TRAILING_3_YRS"])
                    y5 = safe_yield(rec, ["TSUA_5_SHANIM", "TSUA_NOMINALIT_5_SHANIM", "YIELD_TRAILING_5_YRS"])
                    
                    raw_date = str(rec.get('REPORT_PERIOD', ''))
                    date_str = f"{raw_date[4:6]}/{raw_date[0:4]}" if len(raw_date) == 6 else "מעודכן"
                    
                    t_node["funds"].append({
                        "id": rec["FUND_ID"], "company": display_name, "name": rec.get("FUND_NAME", ""),
                        "YTD": ytd, 
                        "Year1": "N/A",  # ויתור מוחלט על השדה לבקשתך למניעת חורים
                        "Year3": y3, 
                        "Year5": y5,
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
    log.info("מריץ בניית מטריצה נקייה ומזוקקת מהיסוד...")
    data = build()
    
    # בקרת הגנה: מוודאים שנמצאו לפחות 10 קופות אמיתיות בשוק כדי לא לייצר קובץ ריק
    valid_count = sum(1 for p in data for t in p["tracks"] for f in t["funds"] if f["id"] is not None)
    if valid_count < 10:
        log.error("שגיאה: כמות נתונים נמוכה מדי מה-API. השמירה בוטלה להגנת האתר.")
        exit(1)
        
    with open("funds_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"הצלחה! המטריצה עודכנה בצורה נקייה עם {valid_count} מסלולים תחרותיים.")