/**
 * ==========================================================================
 * הליבה האפליקטיבית - השקעות שעושות שכל (גרסה 21.0)
 * מנוע ניתוב ושאילתות דינמי מול Sanity CMS לפי קטגוריות עמודים
 * ==========================================================================
 */

const SANITY_PROJECT_ID = 'nk1s624p'; 
const SANITY_DATASET = 'production';
const SANITY_VERSION = 'v2021-10-21';

// 1. מנוע המדדים המקומי
async function loadMarketTickerData() {
    const symbolToClassMap = {
        '^GSPC': 'ticker-sp500',
        '^NDX': 'ticker-nasdaq',
        '^DJI': 'ticker-dow',
        '^RUT': 'ticker-russell',
        'TA35.TA': 'ticker-ta35',
        'TA125.TA': 'ticker-ta125',
        'TA90.TA': 'ticker-ta90'
    };

    try {
        const response = await fetch('./market_data.json?cachebust=' + new Date().getTime());
        if (!response.ok) throw new Error('Data frame pending');
        
        const data = await response.json();

        Object.keys(data).forEach(symbol => {
            const targetClass = symbolToClassMap[symbol];
            if (targetClass) {
                const price = data[symbol].price;
                const changePercent = data[symbol].change;

                const isPositive = changePercent >= 0;
                const arrow = isPositive ? '▲' : '▼';
                const trendClass = isPositive ? 'positive' : 'negative';
                const oppositeClass = isPositive ? 'negative' : 'positive';

                const domElements = document.querySelectorAll(`.${targetClass}`);
                domElements.forEach(element => {
                    const formattedPrice = price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                    const formattedPercent = (isPositive ? '+' : '') + changePercent.toFixed(2);
                    
                    element.innerText = `${arrow} ${formattedPrice} (${formattedPercent}%)`;
                    element.classList.remove(oppositeClass);
                    element.classList.add(trendClass);
                });
            }
        });
    } catch (error) {
        console.warn('Ticker Engine:', error.message);
    }
}

// 2. מנוע ניתוב ושאילתות דינמי מבוסס הקשר עמוד
async function fetchAndRouteSanityContent() {
    // מפת ניתוב אסטרטגית: מקשרת בין מזהה המיכל הפיזי (ID) לערך ה-category הלוגי ב-Sanity
    const routeMap = {
        'investments-content-area': 'investments',
        'pension-content-area': 'pension',
        'tax-content-area': 'tax',
        'funds-content-area': 'funds'
    };

    let activeContainerId = null;
    let activeCategory = null;

    // סריקה אנליטית לזיהוי המיכל הנוכחי שקיים בדף הספציפי שנטען בדפדפן
    for (const containerId in routeMap) {
        if (document.getElementById(containerId)) {
            activeContainerId = containerId;
            activeCategory = routeMap[containerId];
            break;
        }
    }

    // במידה והמשתמש נמצא בעמוד שלא אמור להציג רשימת סקירות (כמו עמוד הבית), המנוע יעצור בעדינות
    if (!activeContainerId) return;

    const targetContainer = document.getElementById(activeContainerId);

    // בניית שאילתת GROQ מותאמת קטגוריה: שליפת מאמרים רלוונטיים בלבד, מסודרים כרונולוגית מהחדש לישן
    const groqQuery = `*[_type == "column" && category == "${activeCategory}"] | order(publishedAt desc)`;
    const apiUrl = `https://${SANITY_PROJECT_ID}.api.sanity.io/${SANITY_VERSION}/data/query/${SANITY_DATASET}?query=${encodeURIComponent(groqQuery)}`;

    try {
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error('Sanity CDN connection failed');
        
        const jsonResult = await response.json();
        const columns = jsonResult.result;

        // טיפול במצב שבו טרם הוזנו מאמרים תחת הקטגוריה הספציפית הזו
        if (!columns || columns.length === 0) {
            targetContainer.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 40px; font-size: 15px;">טרם פורסמו סקירות מקצועיות בקטגוריה זו. מוזמנים להתעדכן בקרוב.</p>';
            return;
        }

        targetContainer.innerHTML = ''; // ניקוי חיווי הטעינה הראשוני (Loading state)

        // רינדור דינמי של כרטיסיות המאמרים שנמצאו
        columns.forEach(column => {
            const title = column.title;
            const snippet = column.excerpt || '';
            const publishedDate = column.publishedAt ? new Date(column.publishedAt).toLocaleDateString('he-IL') : '';
            const link = column.slug ? `article.html?slug=${column.slug.current}` : '#';

            const articleCard = `
                <div class="injected-article">
                    <h5>${title}</h5>
                    ${publishedDate ? `<p style="font-size: 11px; margin-bottom: 4px; color: #7f8c8d;">פורסם ב: ${publishedDate}</p>` : ''}
                    <p>${snippet}</p>
                    <a href="${link}">לקריאת הטור המלא ←</a>
                </div>
            `;

            targetContainer.innerHTML += articleCard;
        });

    } catch (error) {
        console.warn('Sanity CMS Engine:', error.message);
        targetContainer.innerHTML = '<p style="color: var(--accent-error); text-align: center; padding: 20px;">תקלת תקשורת זמנית מול שרתי התוכן.</p>';
    }
}

// 3. אתחול והפעלת המערכות עם טעינת ה-DOM
document.addEventListener('DOMContentLoaded', () => {
    // הפעלת עדכוני מדדי הבורסה באוויר
    loadMarketTickerData();
    setInterval(loadMarketTickerData, 300000); // רענון מובנה כל 5 דקות
    
    // הפעלת מנוע שאיבת הנתונים הממודר
    fetchAndRouteSanityContent();

    // הפעלת מנגנון תפריט הניווט הרספונסיבי למובייל
    const menuToggle = document.querySelector('.menu-toggle');
    const mainNav = document.querySelector('.main-nav');
    if (menuToggle && mainNav) {
        menuToggle.addEventListener('click', () => {
            mainNav.classList.toggle('active');
            menuToggle.innerText = mainNav.classList.contains('active') ? '✕' : '☰';
        });
    }
});