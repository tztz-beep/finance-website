/**
 * ==========================================================================
 * הליבה האפליקטיבית - השקעות שעושות שכל (גרסה 16.0)
 * מנוע CMS פנימי עם הפניה לעמוד קריאה מקומי
 * ==========================================================================
 */

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

// 2. מנוע התוכן הדינמי (Headless CMS)
async function fetchAndRouteContent() {
    const githubUsername = 'tztz-beep'; 
    const repoName = 'finance-website';
    
    const apiUrl = `https://api.github.com/repos/${githubUsername}/${repoName}/issues?state=open`;

    try {
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error('CMS fetching failed. Check if repo is public.');
        
        const issues = await response.json();
        const articles = issues.filter(issue => !issue.pull_request);

        articles.forEach(article => {
            const title = article.title;
            const snippet = (article.body && article.body.length > 120) 
                            ? article.body.substring(0, 120) + '...' 
                            : (article.body || 'לחץ לקריאת הסקירה המלאה');
            
            // השינוי הקריטי: הפניה פנימית לאתר שלנו עם מספר המאמר
            const link = `article.html?id=${article.number}`; 
            const labels = article.labels.map(label => label.name.toLowerCase());

            const articleCard = `
                <div class="injected-article">
                    <h5>${title}</h5>
                    <p>${snippet}</p>
                    <a href="${link}">לקריאת הסקירה ←</a>
                </div>
            `;

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

// 3. אתחול
document.addEventListener('DOMContentLoaded', () => {
    loadMarketTickerData();
    setInterval(loadMarketTickerData, 300000);
    
    fetchAndRouteContent();

    const menuToggle = document.querySelector('.menu-toggle');
    const mainNav = document.querySelector('.main-nav');
    if (menuToggle && mainNav) {
        menuToggle.addEventListener('click', () => {
            mainNav.classList.toggle('active');
            menuToggle.innerText = mainNav.classList.contains('active') ? '✕' : '☰';
        });
    }
});
