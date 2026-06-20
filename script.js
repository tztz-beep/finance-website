/**
 * ==========================================================================
 * מערכת הזרקת נתוני שוק בזמן אמת - השקעות שעושות שכל
 * מנוע אינטגרציה מול שרתי Yahoo Finance באמצעות פרוקסי CORS פתוח
 * ==========================================================================
 */

async function fetchLiveMarketData() {
    // רשימת הסימולים הרשמית של המדדים ב-Yahoo Finance
    const symbols = ['^GSPC', '^NDX', '^DJI', '^RUT', 'TA35.TA', 'TA125.TA', 'TA90.TA'];
    const symbolsString = symbols.join(',');
    
    // בניית הכתובת האנליטית ומעבר דרך פרוקסי AllOrigins לעקיפת חסימות דפדפן
    const yahooApiUrl = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${symbolsString}`;
    const proxyUrl = `https://api.allorigins.win/get?url=${encodeURIComponent(yahooApiUrl)}`;

    try {
        const response = await fetch(proxyUrl);
        if (!response.ok) throw new Error('Network response was not ok');
        
        const wrapperData = await response.json();
        // פענוח מחרוזת ה-JSON המוחזרת מתוך שרת הפרוקסי
        const marketJson = JSON.parse(wrapperData.contents);
        const quotes = marketJson.quoteResponse.result;

        // מפת סינכרון בין סימולי הבורסה לבין מחלקות ה-HTML באתר
        const symbolToClassMap = {
            '^GSPC': 'ticker-sp500',
            '^NDX': 'ticker-nasdaq',
            '^DJI': 'ticker-dow',
            '^RUT': 'ticker-russell',
            'TA35.TA': 'ticker-ta35',
            'TA125.TA': 'ticker-ta125',
            'TA90.TA': 'ticker-ta90'
        };

        // לולאת עיבוד והזרקה אקטיבית לכל מדד ומדד
        quotes.forEach(quote => {
            const symbol = quote.symbol;
            const targetClass = symbolToClassMap[symbol];

            if (targetClass) {
                const price = quote.regularMarketPrice;
                const changePercent = quote.regularMarketChangePercent;
                
                // קביעת כיווניות המגמה
                const isPositive = changePercent >= 0;
                const arrow = isPositive ? '▲' : '▼';
                const trendClass = isPositive ? 'positive' : 'negative';
                const oppositeClass = isPositive ? 'negative' : 'positive';

                // איתור כל האלמנטים המשוכפלים ברצועה (קבוצה 1 וקבוצה 2)
                const domElements = document.querySelectorAll(`.${targetClass}`);
                
                domElements.forEach(element => {
                    // עיצוב מספרים תקני בפורמט פיננסי קריא (עם פסיקים ואלפיות)
                    const formattedPrice = price.toLocaleString('en-US', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    });
                    const formattedPercent = (isPositive ? '+' : '') + changePercent.toFixed(2);

                    // הזרקת המבנה החדש והעדכני
                    element.innerText = `${arrow} ${formattedPrice} (${formattedPercent}%)`;
                    
                    // עדכון דינמי של פלטת הצבעים בהתאם למגמה
                    element.classList.remove(oppositeClass);
                    element.classList.add(trendClass);
                });
            }
        });

    } catch (error) {
        console.error('Failure in fetching live market metrics:', error);
        // במקרה של כשל רשת, נשאיר חיווי סולידי למשתמש
        symbols.forEach(sym => {
            const targetClass = symbolToClassMap[sym];
            if (targetClass) {
                document.querySelectorAll(`.${targetClass}`).forEach(el => {
                    if(el.innerText === 'טוען...') el.innerText = 'לא זמין';
                });
            }
        });
    }
}

// הפעלת המנוע מיד עם טעינת המבנה הסמנטי של העמוד (DOM)
document.addEventListener('DOMContentLoaded', () => {
    fetchLiveMarketData();
    
    // ביצוע רענון נתונים אוטומטי (Polling) מדי 5 דקות (300,000 מילישניות)
    setInterval(fetchLiveMarketData, 300000);
});
