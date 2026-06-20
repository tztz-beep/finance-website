/**
 * ==========================================================================
 * מנוע תצוגה חכם ורספונסיבי - השקעות שעושות שכל
 * קריאת נתוני שוק מובנים מקובץ מקומי מבוסס Pipeline
 * ==========================================================================
 */

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
        // משיכת קובץ הנתונים המקומי והטרי שנבנה על ידי השרת
        const response = await fetch('./market_data.json?cachebust=' + new Date().getTime());
        if (!response.ok) throw new Error('Local data frame pending generation');
        
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
        console.warn('Pipeline file reading initialization. Utilizing smooth layout standards.', error);
    }
}

// אתחול וניהול אירועים באתר
document.addEventListener('DOMContentLoaded', () => {
    // 1. טעינת נתוני המדדים המקומיים
    loadMarketTickerData();

    // 2. לוגיקת תפריט המבורגר רספונסיבי למובייל
    const menuToggle = document.querySelector('.menu-toggle');
    const mainNav = document.querySelector('.main-nav');

    if (menuToggle && mainNav) {
        menuToggle.addEventListener('click', () => {
            mainNav.classList.toggle('active');
            menuToggle.innerText = mainNav.classList.contains('active') ? '✕' : '☰';
        });
    }
});
