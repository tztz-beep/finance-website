import requests
import pandas as pd
import json
from datetime import datetime

# מילון הקופות שברצונך להציג באתר (ניתן להוסיף מספרי קופות ככל הנדרש)
FUNDS = {
    "5122": "הראל השתלמות מנייתי",
    "1375": "אלטשולר שחם גמל מנייתי",
    "1430": "ילין לפידות מסלול S&P 500"
}

# מזהה מאגר גמל-נט ב-Data.gov.il (יש לוודא את ה-ID העדכני באתר הממשלתי)
RESOURCE_ID = 'a3123861-12c6-43a2-92e1-48616149495e' 

def calculate_cumulative_yield(df, months):
    """פונקציה המחשבת ריבית דריבית מצטברת על חתך נתונים"""
    if len(df) == 0: 
        return "0.00"
    
    slice_df = df.head(months)
    # שימוש באגרגציה לחישוב המכפיל המצטבר
    cumulative = (1 + slice_df['MONTHLY_YIELD'] / 100).prod() - 1
    return f"{(cumulative * 100):.2f}"

def fetch_fund_data():
    results = []
    current_year = datetime.now().year
    
    for fund_id, fund_name in FUNDS.items():
        # שליפת 60 החודשים האחרונים עבור הקופה הספציפית
        url = f"https://data.gov.il/api/3/action/datastore_search?resource_id={RESOURCE_ID}&q={fund_id}&limit=60"
        
        try:
            response = requests.get(url)
            data = response.json()
            records = data.get('result', {}).get('records', [])
            
            if records:
                # טעינה למבנה נתונים וסידור כרונולוגי חכם
                df = pd.DataFrame(records)
                df['MONTHLY_YIELD'] = pd.to_numeric(df['MONTHLY_YIELD'], errors='coerce').fillna(0)
                df['REPORT_PERIOD'] = pd.to_datetime(df['REPORT_PERIOD'], format='%Y%m', errors='coerce')
                df = df.sort_values(by='REPORT_PERIOD', ascending=False)
                
                # חיתוך נתונים מתחילת השנה (YTD)
                ytd_df = df[df['REPORT_PERIOD'].dt.year == current_year]
                
                results.append({
                    "id": fund_id,
                    "name": fund_name,
                    "YTD": calculate_cumulative_yield(ytd_df, len(ytd_df)),
                    "Year1": calculate_cumulative_yield(df, 12),
                    "Year3": calculate_cumulative_yield(df, 36),
                    "Year5": calculate_cumulative_yield(df, 60),
                    "last_updated": df['REPORT_PERIOD'].dt.strftime('%m/%Y').iloc[0]
                })
        except Exception as e:
            print(f"Error fetching data for fund {fund_id}: {e}")
            
    # שמירת התוצאות לקובץ JSON קטנטן ומהיר שיישב בשרת שלנו
    with open('funds_data.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print("Financial data processed and saved successfully.")

if __name__ == "__main__":
    fetch_fund_data()