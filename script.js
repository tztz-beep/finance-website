/**
 * ==========================================================================
 * הליבה האפליקטיבית - השקעות שעושות שכל (גרסה 19.0)
 * אינטגרציה מלאה מול Structured Headless CMS (Sanity.io)
 * ==========================================================================
 */

const SANITY_PROJECT_ID = 'nk1s624p'; 
const SANITY_DATASET = 'production';
const SANITY_VERSION = 'v2021-10-21';

// 1. מנוע המדדים המקומי (ללא שינוי)
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

// 2. מנוע התוכן המקצועי מבוסס Sanity API
async function fetchAndRouteSanityContent() {
    // השאילתה מושכת את כל התוכן מסוג 'טור מקצועי' שיצרנו, מסודר מהחדש לישן
    const groqQuery = '*[_type == "column"] | order(publishedAt desc)';
    const apiUrl = `https://${SANITY_PROJECT_ID}.api.sanity.io/${SANITY_VERSION}/data/query/${SANITY_DATASET}?query=${encodeURIComponent(groqQuery)}`;

    try {
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error('Sanity CDN connection failed');
        
        const jsonResult = await response.json();
        const columns = jsonResult.result;

        if (!columns || columns.length === 0) return;

        // איתור אזור הנחיתה תחת הקובייה של "ייעוץ וניהול השקעות"
        const targetContainer = document.getElementById('investments-content-area');
        if (!targetContainer) return;

        targetContainer.innerHTML = ''; // ניקוי העמודה לפני הזרקת התוכן החדש

        columns.forEach(column => {
            const title = column.title;
            const snippet = column.excerpt || '';
            const publishedDate = column.publishedAt ? new Date(column.publishedAt).toLocaleDateString('he-IL') : '';
            
            // הכנת הקישור לעמוד המאמר המלא (ישתמש ב-Slug שהגדרנו)
            const link = column.slug ? `article.html?slug=${column.slug.current}` : '#';

            // בניית הקובייה העיצובית בדיוק לפי העיצוב (CSS) שכבר הגדרת מראש
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
    }
}

// 3. הפעלת המערכות עם טעינת העמוד
document.addEventListener('DOMContentLoaded', () => {
    // הפעלת מדדי הבורסה
    loadMarketTickerData();
    setInterval(loadMarketTickerData, 300000);
    
    // הפעלת שאיבת הטורים המקצועיים מסניטי
    fetchAndRouteSanityContent();

    // הפעלת תפריט הניווט (מובייל)
    const menuToggle = document.querySelector('.menu-toggle');
    const mainNav = document.querySelector('.main-nav');
    if (menuToggle && mainNav) {
        menuToggle.addEventListener('click', () => {
            mainNav.classList.toggle('active');
            menuToggle.innerText = mainNav.classList.contains('active') ? '✕' : '☰';
        });
    }
});