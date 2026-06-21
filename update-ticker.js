const fs = require('fs');

async function fetchFinancialMetrics() {
    const symbols = ['^GSPC', '^NDX', '^DJI', '^RUT', 'TA35.TA', 'TA125.TA', 'TA90.TA'];
    const processedData = {};
    let successCount = 0;

    console.log('Initiating Highly-Resilient Connection to Yahoo Chart API...');

    for (const symbol of symbols) {
        try {
            const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=2d`;
            
            const response = await fetch(url, {
                headers: { 
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) throw new Error(`HTTP Status ${response.status}`);

            const data = await response.json();
            const result = data.chart.result[0];
            const meta = result.meta;

            // אלגוריתם חילוץ חסין תקלות: אם השדה הראשי ריק, שולפים את המחיר האחרון ממערך הסגירות
            let currentPrice = meta.regularMarketPrice;
            if (!currentPrice && result.indicators && result.indicators.quote && result.indicators.quote[0].close) {
                const closes = result.indicators.quote[0].close.filter(c => c !== null);
                if (closes.length > 0) {
                    currentPrice = closes[closes.length - 1];
                }
            }

            const prevClose = meta.previousClose || meta.chartPreviousClose;
            
            if (!currentPrice || !prevClose) {
                throw new Error('Incomplete data vectors returned from endpoint');
            }

            const changePercent = ((currentPrice - prevClose) / prevClose) * 100;

            processedData[symbol] = {
                price: currentPrice,
                change: changePercent
            };
            
            successCount++;
            console.log(`[V] Data successfully resolved for ${symbol}: ${currentPrice}`);
            
            await new Promise(resolve => setTimeout(resolve, 300));

        } catch (error) {
            console.warn(`[X] Bypassing symbol ${symbol} due to fetch block:`, error.message);
        }
    }

    if (successCount === 0) {
        console.error('Critical Failure: All finance endpoints rejected connection.');
        process.exit(1);
    }

    fs.writeFileSync('market_data.json', JSON.stringify(processedData, null, 2));
    console.log(`Pipeline finished. Saved ${successCount} active symbols.`);
}

fetchFinancialMetrics();
