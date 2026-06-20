const fs = require('fs');

async function fetchFinancialMetrics() {
    const symbols = ['^GSPC', '^NDX', '^DJI', '^RUT', 'TA35.TA', 'TA125.TA', 'TA90.TA'];
    const url = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${symbols.join(',')}`;

    try {
        // פנייה ישירה משרת לשרת - ללא חסימות דפדפן
        const response = await fetch(url, {
            headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' }
        });
        
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const data = await response.json();
        const quotes = data.quoteResponse.result;

        const processedData = {};
        quotes.forEach(quote => {
            processedData[quote.symbol] = {
                price: quote.regularMarketPrice,
                change: quote.regularMarketChangePercent
            };
        });

        // כתיבת הנתונים המעודכנים לקובץ מקומי באתר
        fs.writeFileSync('market_data.json', JSON.stringify(processedData, null, 2));
        console.log('Market data system updated successfully.');
    } catch (error) {
        console.error('Critical failure in data pipeline fetch:', error);
        process.exit(1);
    }
}

fetchFinancialMetrics();
