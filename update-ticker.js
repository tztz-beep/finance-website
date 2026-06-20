const fs = require('fs');
// ייבוא המנוע הייעודי
const yahooFinance = require('yahoo-finance2').default;

async function fetchFinancialMetrics() {
    const symbols = ['^GSPC', '^NDX', '^DJI', '^RUT', 'TA35.TA', 'TA125.TA', 'TA90.TA'];

    try {
        console.log('Initiating intelligent connection via yahoo-finance2 engine...');
        
        // משיכת הנתונים - המנוע מנהל את ה-Cookies וה-Crumbs אוטומטית
        const quotes = await yahooFinance.quote(symbols);

        if (!quotes || quotes.length === 0) {
            throw new Error('API returned empty dataset.');
        }

        const processedData = {};
        quotes.forEach(quote => {
            processedData[quote.symbol] = {
                price: quote.regularMarketPrice,
                change: quote.regularMarketChangePercent
            };
        });

        // כתיבת הנתונים לקובץ
        fs.writeFileSync('market_data.json', JSON.stringify(processedData, null, 2));
        console.log('Success: market_data.json created with live metrics.');

    } catch (error) {
        console.error('Critical Error in API Engine:', error.message);
        process.exit(1);
    }
}

fetchFinancialMetrics();
