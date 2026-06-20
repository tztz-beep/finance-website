const fs = require('fs');

async function fetchFinancialMetrics() {
    const symbols = ['^GSPC', '^NDX', '^DJI', '^RUT', 'TA35.TA', 'TA125.TA', 'TA90.TA'];
    const targetUrl = `https://query1.finance.yahoo.com/v7/finance/quote?symbols=${symbols.join(',')}`;
    
    // ניתוב הבקשה דרך צומת גישה אנונימי כדי למנוע חסימת IP של חוות השרתים של GitHub
    const proxyUrl = `https://api.allorigins.win/get?url=${encodeURIComponent(targetUrl)}`;

    try {
        const response = await fetch(proxyUrl);
        if (!response.ok) throw new Error(`HTTP network anomaly! status: ${response.status}`);
        
        const wrapperData = await response.json();
        const data = JSON.parse(wrapperData.contents); // פענוח עטיפת הפרוקסי
        const quotes = data.quoteResponse.result;

        const processedData = {};
        quotes.forEach(quote => {
            processedData[quote.symbol] = {
                price: quote.regularMarketPrice,
                change: quote.regularMarketChangePercent
            };
        });

        // כתיבה פיזית של הקובץ על גבי השרת
        fs.writeFileSync('market_data.json', JSON.stringify(processedData, null, 2));
        console.log('Market data pipeline executed and filed successfully.');
    } catch (error) {
        console.error('Critical failure in core data pipeline fetch:', error);
        process.exit(1);
    }
}

fetchFinancialMetrics();
