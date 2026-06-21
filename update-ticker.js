const fs = require('fs');

async function fetchFinancialMetrics() {
    const symbols = ['^GSPC', '^NDX', '^DJI', '^RUT', 'TA35.TA', 'TA125.TA', 'TA90.TA'];
    const processedData = {};
    let successCount = 0;

    console.log('Initiating Stealth Connection to Yahoo Chart API...');

    for (const symbol of symbols) {
        try {
            // גישה דרך ה-API של הגרפים - פתוח יותר ואינו חסום על ידי רובוטים בדרך כלל
            const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=2d`;
            
            const response = await fetch(url, {
                headers: { 
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) throw new Error(`HTTP Status ${response.status}`);

            const data = await response.json();
            const meta = data.chart.result[0].meta;

            // חילוץ המחיר העדכני ושער הסגירה הקודם
            const currentPrice = meta.regularMarketPrice;
            const prevClose = meta.previousClose || meta.chartPreviousClose;
            
            // חישוב מדויק של אחוז השינוי
            const changePercent = ((currentPrice - prevClose) / prevClose) * 100;

            processedData[symbol] = {
                price: currentPrice,
                change: changePercent
            };
            
            successCount++;
            console.log(`[V] Data securely fetched for ${symbol}`);
            
            // מנגנון המתנה קצר למניעת זיהוי של בקשות אוטומטיות מהירות מדי
            await new Promise(resolve => setTimeout(resolve, 500));

        } catch (error) {
            console.warn(`[X] Failed to fetch ${symbol}:`, error.message);
        }
    }

    if (successCount === 0) {
        console.error('Critical Failure: Could not fetch any data from the stealth endpoints.');
        process.exit(1);
    }

    // כתיבת הנתונים לקובץ באופן מסודר
    fs.writeFileSync('market_data.json', JSON.stringify(processedData, null, 2));
    console.log(`Success: market_data.json created with ${successCount} live metrics.`);
}

fetchFinancialMetrics();
