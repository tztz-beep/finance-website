import requests
import json
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

# מקורות הנתונים הרשמיים שמיפית בהצלחה
RESOURCES = {
    "gemel":    "a30dcbea-a1d2-482c-ae29-8f781f5025fb",  # גמל, השתלמות, גמל להשקעה
    "pension":  "6d47d6b5-cb08-488b-b333-f1e717b1e1bd",  # קרנות פנסיה
    "policies": "d0b61e50-1e38-4d52-8067-de8b1ee37419",  # פוליסות חיסכון
}

BASE_URL = "https://data.gov.il/api/3/action/datastore_search"

COMPANIES = ["הראל", "אלטשולר שחם", "ילין לפידות", "הפניקס", "מיטב", "כלל", "מגדל", "מנורה מבטחים", "אנליסט", "מור"]

PRODUCTS = {
    "hishtalmut": {"title": "קרן השתלמות", "res_type": "gemel", "keyword": "השתלמות"},
    "gemel_inv":  {"title": "קופת גמל להשקעה", "res_type": "gemel", "keyword": "להשקעה"},
    "pension":    {"title": "קרן פנסיה מקיפה", "res_type": "pension", "keyword": "פנסיה"},
    "policy":     {"title": "פוליסת חיסכון", "res_type": "policies", "keyword": "חיסכון"}
}

TRACKS = {
    "sp500":   {"title": "מסלול עוקב S&P 500", "keywords": ["S&P", "500", "מחקה מדד", "אס אנד פי"]},
    "equity":  {"title": "מסלול מנייתי טהור", "keywords": ["מניות", "מנייתי", "equity"]},
    "general": {"title": "מסלול כללי / תלוי גיל", "keywords": ["כללי", "תלוי גיל", "לבני", "עד גיל", "קצב"]},
    "solid":   {"title": "מסלול אג\"ח / שקלי", "keywords": ["אג\"ח", "אגח", "שקלי", "אגרות חוב", "כספית", "ממשלתי"]}
}

DELAY_BETWEEN_REQUESTS = 0.2

def classify_track(fund_name, classification):
    """מנוע סיווג חכם - משייך קופה למסלול התחרותי המתאים לפי מילות מפתח"""
    text = (str(fund_name) + " " + str(classification)).lower()
    if any(k in text for k in ["s&p", "500", "אס אנד פי"]):
        return "sp500"
    if any(k in text for k in ["מניות", "מנייתי", "equity"]):
        return "equity"
    if any(k in text for k in ["אג\"ח", "אגח", "שקלי", "אגרות חוב", "כספית", "ממשלתי", "בונד", "סולידי"]):
        return "solid"
    return "general" # ברירת מחדל למסלולים מגוונים או תלויי גיל שלא סווגו ספציפית

def fetch_yield_data(resource_id, fund_id):
    """שליפת שורת התשואה האחרונה והרשמית עבור קופה ספציפית"""
    params = {
        "resource_id": resource_id,
        "filters": json.dumps({"FUND_ID": str(fund_id)}),
        "sort": "REPORT_PERIOD desc",
        "limit": 1
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=12)
        if resp.status_code == 200:
            records = resp.json().get("result", {}).get("records", [])
            if records:
                return records[0]
    except Exception as e:
        log.error(f"Error fetching yields for fund {fund_id}: {e}")
    return {}

def extract_clean_value(record, fields):
    for f in fields:
        v = record.get(f)
        if v is not None and str(v).strip() not in ("", "None"):
            try:
                return f"{float(v):.2f}"
            except:
                pass
    return "N/A"

def build_dataset():
    matrix = []
    
    for prod_key, prod_info in PRODUCTS.items():
        log.info(f"📦 מייצר מטריצה עבור מוצר: {prod_info['title']}")
        product_node = {"id": prod_key, "title": prod_info["title"], "tracks": []}
        res_id = RESOURCES[prod_info["res_type"]]
        
        # מבנה זמני לאיסוף הקופות הטובות ביותר לכל חברה בכל מסלול
        track_matches = {t_id: {c: None for c in COMPANIES} for t_id in TRACKS}
        
        for company in COMPANIES:
            params = {
                "resource_id": res_id,
                "filters": json.dumps({"COMPANY_NAME": company}),
                "sort": "REPORT_PERIOD desc",
                "limit": 150,
                "fields": "FUND_ID,FUND_NAME,FUND_CLASSIFICATION,COMPANY_NAME,REPORT_PERIOD",
                "distinct": "true"
            }
            try:
                resp = requests.get(BASE_URL, params=params, timeout=15)
                if resp.status_code == 200:
                    records = resp.json().get("result", {}).get("records", [])
                    for rec in records:
                        fid = rec.get("FUND_ID")
                        fname = rec.get("FUND_NAME", "")
                        fclass = rec.get("FUND_CLASSIFICATION", "")
                        
                        # סינון תת-מוצרים בתוך מאגר הגמל המאוחד
                        if prod_info["res_type"] == "gemel":
                            if prod_info["keyword"] not in fname and prod_info["keyword"] not in fclass:
                                continue
                        
                        t_id = classify_track(fname, fclass)
                        
                        # שמירת המסלול העדכני ביותר שנמצא לחברה זו
                        current_best = track_matches[t_id][company]
                        if current_best is None or int(rec.get("REPORT_PERIOD", 0)) > int(current_best.get("REPORT_PERIOD", 0)):
                            track_matches[t_id][company] = rec
            except Exception as e:
                log.error(f"Discovery fail for {company}: {e}")
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        # כעת בונים את מבנה הטבלאות התחרותיות המבוקש עבור ה-HTML
        for track_key, track_info in TRACKS.items():
            track_node = {"id": track_key, "title": track_info["title"], "funds": []}
            log.info(f"  ⚡ מאכלס מסלול תחרותי: {track_info['title']}")
            
            for company in COMPANIES:
                matched_fund = track_matches[track_key][company]
                if matched_fund:
                    fid = matched_fund.get("FUND_ID")
                    fname = matched_fund.get("FUND_NAME")
                    
                    # שליפת התשואות הרשמיות מהאוצר עבור הקופה הזו
                    time.sleep(DELAY_BETWEEN_REQUESTS)
                    yield_rec = fetch_yield_data(res_id, fid)
                    
                    ytd = extract_clean_value(yield_rec, ["TSUA_MITCHILAT_SHANA", "TSUA_NOMINALIT_MITCHILAT_SHANA"])
                    y1 = extract_clean_value(yield_rec, ["TSUA_SHANA_ACHARONA", "TSUA_NOMINALIT_SHANA_ACHARONA"])
                    y3 = extract_clean_value(yield_rec, ["TSUA_3_SHANIM", "TSUA_NOMINALIT_3_SHANIM"])
                    y5 = extract_clean_value(yield_rec, ["TSUA_5_SHANIM", "TSUA_NOMINALIT_5_SHANIM"])
                    
                    raw_date = str(yield_rec.get('REPORT_PERIOD', ''))
                    updated_str = f"{raw_date[4:6]}/{raw_date[0:4]}" if len(raw_date) == 6 else "מעודכן"
                    
                    track_node["funds"].append({
                        "id": fid, "company": company, "name": fname,
                        "YTD": ytd, "Year1": y1, "Year3": y3, "Year5": y5,
                        "last_updated": updated_str
                    })
                else:
                    # יצירת שורת גיבוי שומרת-מבנה עבור חברות שאין להן מסלול כזה
                    track_node["funds"].append({
                        "id": None, "company": company, "name": f"לא נמצא מסלול {track_info['title']} פעיל",
                        "YTD": "N/A", "Year1": "N/A", "Year3": "N/A", "Year5": "N/A",
                        "last_updated": "N/A"
                    })
            product_node["tracks"].append(track_node)
        matrix.append(product_node)
        
    return matrix

if __name__ == "__main__":
    log.info("🚀 מתחיל הרצה משולבת: גילוי דינמי + בניית מטריצה תחרותית")
    data = build_dataset()
    
    with open("funds_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info("✅ קובץ הנתונים התחרותי נשמר בהצלחה בתשתית האתר.")