import json
import logging
import sys
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger(__name__)

BASE_URL = "https://data.gov.il/api/3/action/datastore_search"

RESOURCES = {
    "gemel": "a30dcbea-a1d2-482c-ae29-8f781f5025fb",
    "pension": "6d47d6b5-cb08-488b-b333-f1e717b1e1bd",
    "policies": "d0b61e50-1e38-4d52-8067-de8b1ee37419"
}

COMPANY_MAP = {
    "הראל": "הראל", "אלטשולר": "אלטשולר שחם", "ילין": "ילין לפידות",
    "הפניקס": "הפניקס", "מיטב": "מיטב", "כלל": "כלל", "מגדל": "מגדל",
    "מנורה": "מנורה מבטחים", "אנליסט": "אנליסט", "מור": "מור"
}

PRODUCTS = {
    "hishtalmut": {"title": "קרן השתלמות", "res": "gemel", "key": "השתלמות"},
    "gemel_inv":  {"title": "קופת גמל להשקעה", "res": "gemel", "key": "להשקעה"},
    "pension":    {"title": "קרן פנסיה מקיפה", "res": "pension", "key": ""},
    "policy":     {"title": "פוליסת חיסכון", "res": "policies", "key": "חיסכון"}
}

TRACKS = {
    "sp500":   {"title": "מסלול עוקב S&P 500"},
    "equity":  {"title": "מסלול מנייתי טהור"},
    "general": {"title": "מסלול כללי / תלוי גיל"},
    "solid":   {"title": "מסלול אג\"ח / שקלי"}
}

def extract_yield(rec, keywords):
    for k, v in rec.items():
        if any(key in str(k).upper() for key in keywords):
            if v is not None and str(v).strip() not in ("", "None", "null", "NaN", "nan", "-"):
                try: return f"{float(v):.2f}"
                except: pass
    return "N/A"

def classify(name, classification):
    """מנוע סיווג כירורגי שמונע זליגת קופות מעורבות למסלולים טהורים"""
    t = (str(name) + " " + str(classification)).lower().replace(" ", "").replace(";", "").replace("-", "")
    
    # 1. חסימת מילות רעש
    if any(x in t for x in ["ילד", "פיצויים", "מטרה", "בטוחה", "מרכזית", "אישי", "מבטיחת", "הלכה", "שריעה"]): 
        return None

    # 2. S&P 500
    if any(x in t for x in ["s&p", "500", "p500", "sp500", "אסאנדפי", "s1p"]): 
        return "sp500"

    # 3. מנייתי טהור (חובה: מניות. אסור: אג"ח, אשראי, "עד X%")
    if any(x in t for x in ["מניות", "מנייתי", "equity", "אקוויטי"]):
        if any(x in t for x in ["אגח", "אשראי", "עד25", "עד10", "עד15", "עד20", "שקלי"]):
            pass # נפסל ממנייתי טהור
        else:
            return "equity"

    # 4. אג"ח / סולידי טהור (חובה: אג"ח/שקלי. אסור: מניות)
    if any(x in t for x in ["אגח", "שקלי", "אגרותחוב", "כספית", "סולידי", "ממשלתי"]):
        if any(x in t for x in ["מניות", "מנייתי", "equity"]):
            pass # נפסל מסולידי
        else:
            return "solid"

    # 5. ברירת מחדל
    return "general"

def fetch_all():
    session = requests.Session()
    retry = Retry(total=5, backoff_factor=1, status_forcelist=[403, 429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    
    market_data = []
    for res_key, res_id in RESOURCES.items():
        log.info(f"שואב נתונים ממאגר: {res_key}")
        params = {"resource_id": res_id, "limit": 15000, "sort": "REPORT_PERIOD desc"}
        try:
            resp = session.get(BASE_URL, params=params, timeout=30)
            if resp.status_code == 200:
                records = resp.json().get("result", {}).get("records", [])
                for r in records:
                    r["_res_key"] = res_key
                    market_data.append(r)
        except Exception as e:
            log.error(f"שגיאה במאגר {res_key}: {e}")
        time.sleep(1)
    return market_data

def score(rec):
    s = 0
    if extract_yield(rec, ["5_SHANIM", "5_YRS"]) != "N/A": s += 100
    if extract_yield(rec, ["3_SHANIM", "3_YRS"]) != "N/A": s += 10
    if extract_yield(rec, ["SHANA_ACHARONA", "1_YR", "12_MONTHS", "12_HODASHIM"]) != "N/A": s += 1
    return s

def build():
    market_data = fetch_all()
    matrix = []
    
    for p_key, p_info in PRODUCTS.items():
        p_node = {"id": p_key, "title": p_info["title"], "tracks": []}
        track_map = {t_key: {c: None for c in COMPANY_MAP.values()} for t_key in TRACKS}
        
        for rec in market_data:
            if rec.get("_res_key") != p_info["res"]: continue
            
            # התיקון הקריטי: מחפשים את החברה רק בעמודות של שמות התאגיד המנהל!
            comp_fields = ["MANAGING_CORPORATION", "PARENT_COMPANY_NAME", "COMPANY_NAME"]
            comp_name_raw = " ".join(str(rec.get(k, "")) for k in comp_fields)
            matched_root = next((root for root in COMPANY_MAP if root in comp_name_raw), None)
            if not matched_root: continue
            display_company = COMPANY_MAP[matched_root]
            
            fname = str(rec.get("FUND_NAME", ""))
            fclass = str(rec.get("FUND_CLASSIFICATION", ""))
            
            if p_info["key"] and p_info["key"] not in fname and p_info["key"] not in fclass: continue
                
            t_key = classify(fname, fclass)
            if not t_key: continue
            
            current = track_map[t_key][display_company]
            if current is None or score(rec) > score(current):
                track_map[t_key][display_company] = rec

        for t_key, t_info in TRACKS.items():
            t_node = {"id": t_key, "title": t_info["title"], "funds": []}
            for display_name in COMPANY_MAP.values():
                rec = track_map[t_key][display_name]
                if rec:
                    ytd = extract_yield(rec, ["MITCHILAT", "YTD", "YEAR_TO_DATE"])
                    y1 = extract_yield(rec, ["SHANA_ACHARONA", "1_YR", "12_MONTHS", "12_HODASHIM"])
                    y3 = extract_yield(rec, ["3_SHANIM", "3_YRS"])
                    y5 = extract_yield(rec, ["5_SHANIM", "5_YRS"])
                    
                    raw_date = str(rec.get('REPORT_PERIOD', ''))
                    date_str = f"{raw_date[4:6]}/{raw_date[0:4]}" if len(raw_date) == 6 else "מעודכן"
                    
                    t_node["funds"].append({
                        "id": rec.get("FUND_ID", ""), "company": display_name, "name": rec.get("FUND_NAME", ""),
                        "YTD": ytd, "Year1": y1, "Year3": y3, "Year5": y5, "last_updated": date_str
                    })
                else:
                    t_node["funds"].append({
                        "id": None, "company": display_name, "name": "לא נמצא מסלול פעיל",
                        "YTD": "N/A", "Year1": "N/A", "Year3": "N/A", "Year5": "N/A", "last_updated": "N/A"
                    })
            p_node["tracks"].append(t_node)
        matrix.append(p_node)
    return matrix

if __name__ == "__main__":
    log.info("מתחיל ריצה עם סינון מתקדם וכירורגי...")
    data = build()
    valid_count = sum(1 for p in data for t in p["tracks"] for f in t["funds"] if f["id"])
    
    if valid_count < 10:
        log.error("שגיאה: התקבלו פחות מ-10 קופות. עוצר שמירה להגנת המערכת.")
        sys.exit(1)
        
    with open("funds_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    log.info(f"נשמרו {valid_count} מסלולים תקינים אל funds_data.json.")