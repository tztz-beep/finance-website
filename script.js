/**
 * ==========================================================================
 * הליבה האפליקטיבית - השקעות שעושות שכל (גרסה 19.0)
 * אינטגרציה מלאה מול Structured Headless CMS (Sanity.io)
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

// 2. מנוע התוכן המקצועי מבוסס Sanity API
async function fetchAndRouteSanityContent() {
    // שאילתת GROQ המושכת את כל המאמרים מסוג post
    const groqQuery = '*[_type == "post"] | order(_createdAt desc)';
    const apiUrl = `https://${SANITY_PROJECT_ID}.api.sanity.io/${SANITY_VERSION}/data/query/${SANITY_DATASET}?query=${encodeURIComponent(groqQuery)}`;

    try {
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error('Sanity CDN connection failed');
        
        const jsonResult = await response.json();
        const articles = jsonResult.result;

        if (!articles || articles.length === 0) return;

        articles.forEach(article => {
            const title = article.title;
            const snippet = article.excerpt || 'לחץ לקריאת הסקירה הפיננסית המלאה...';
            // חילוץ הקטגוריה אם קיימת
            const category = article.category ? article.category.toLowerCase() : '';
            
            // ניתוב לעמוד הקריאה הפנימי באמצעות ה-Slug הייחודי
            const link = article.slug ? `article.html?slug=${article.slug.current}` : '#';

            const articleCard = `
                <div class="injected-article">
                    <h5>${title}</h5>
                    <p>${snippet}</p>
                    <a href="${link}">לקריאת הסקירה ←</a>
                </div>
            `;

            if (category === 'investments') {
                const target = document.getElementById('investments-content-area');
                if (target) target.innerHTML += articleCard;
            } 
            else if (category === 'tax') {
                const target = document.getElementById('tax-content-area');
                if (target) target.innerHTML += articleCard;
            }
            else if (category === 'pension') {
                const target = document.getElementById('pension-content-area');
                if (target) target.innerHTML += articleCard;
            }
            else if (category === 'funds') {
                const target = document.getElementById('funds-content-area');
                if (target) target.innerHTML += articleCard;
            }
        });

    } catch (error) {
        console.warn('Sanity CMS Engine:', error.message);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadMarketTickerData();
    setInterval(loadMarketTickerData, 300000);
    
    fetchAndRouteSanityContent();

    const menuToggle = document.querySelector('.menu-toggle');
    const mainNav = document.querySelector('.main-nav');
    if (menuToggle && mainNav) {
        menuToggle.addEventListener('click', () => {
            mainNav.classList.toggle('active');
            menuToggle.innerText = mainNav.classList.contains('active') ? '✕' : '☰';
        });
    }
});
