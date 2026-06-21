/**
 * ==========================================================================
 * הליבה האפליקטיבית - השקעות שעושות שכל
 * כולל: הזרקת מדדים חיים ומנוע CMS מבוסס תשתית GitHub
 * ==========================================================================
 */

// 1. מנוע המדדים המקומי (מתוך market_data.json)
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

// 2. מנוע התוכן הדינמי (Headless CMS)
async function fetchAndRouteContent() {
    const githubUsername = 'tztz-beep'; 
    const repoName = 'finance-website';
    
    // קריאה ישירה לממשק התקלות/מאמרים של גיטהאב (ללא צורך בהרשאות)
    const apiUrl = `https://api.github.com/repos/${githubUsername}/${repoName}/issues?state=open`;

    try {
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error('CMS fetching failed. Check if repo is public.');
        
        const issues = await response.json();
        const articles = issues.filter(issue => !issue.pull_request);

        articles.forEach(article => {
            const title = article.title;
            // משיכת 120 התווים הראשונים ויצירת תקציר אלגנטי
            const snippet = (article.body && article.body.length > 120) 
                            ? article.body.substring(0, 120) + '...' 
                            : (article.body || 'לחץ לקריאת הסקירה המלאה');
            
            const link = article.html_url; 
            const labels = article.labels.map(label => label.name.toLowerCase());

            // תבנית העיצוב (Template) לכל מאמר שיוזרק
            const articleCard = `
                <div class="injected-article">
                    <h5>${title}</h5>
                    <p>${snippet}</p>
                    <a href="${link}" target="_blank" rel="noopener noreferrer">לקריאת הסקירה ←</a>
                </div>
            `;

            // נתב התוכן (Router) - מחפש תוויות תואמות ומזריק לקוביות
            if (labels.includes('investments')) {
                const target = document.getElementById('investments-content-area');
                if (target) target.innerHTML += articleCard;
            } 
            else if (labels.includes('tax')) {
                const target = document.getElementById('tax-content-area');
                if (target) target.innerHTML += articleCard;
            }
            else if (labels.includes('pension')) {
                const target = document.getElementById('pension-content-area');
                if (target) target.innerHTML += articleCard;
            }
            else if (labels.includes('funds')) {
                const target = document.getElementById('funds-content-area');
                if (target) target.innerHTML += articleCard;
            }
        });

    } catch (error) {
        console.warn('CMS Engine:', error.message);
    }
}

// 3. אתחול מערכות הפלטפורמה בעת טעינת העמוד
document.addEventListener('DOMContentLoaded', () => {
    // אתחול מדדים
    loadMarketTickerData();
    setInterval(loadMarketTickerData, 300000);
    
    // אתחול מערכת התוכן
    fetchAndRouteContent();

    // אתחול תפריט מובייל
    const menuToggle = document.querySelector('.menu-toggle');
    const mainNav = document.querySelector('.main-nav');
    if (menuToggle && mainNav) {
        menuToggle.addEventListener('click', () => {
            mainNav.classList.toggle('active');
            menuToggle.innerText = mainNav.classList.contains('active') ? '✕' : '☰';
        });
    }
});
