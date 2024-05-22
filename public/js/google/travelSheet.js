function travelSheetData(rows) {
    if (rows.length) {
        const data = rows.map(row => ({
            coordinates: row[3] ? row[3].split(',').map(Number) : [],
            city: row[2],
            region: row[4] || null,
            categories: row[5] ? row[5].split(',') : [],
            country: row[0] || 'unknown',
            province: row[1] || 'unknown',
            images: row[6] ? row[6].split(',') : [],
            prices: row[7] || null,
            additionalInfo: row[8] || null
        }));
        return data;
    } else {    
        console.log('No data found.');
        return [];
    }
}

module.exports = travelSheetData;
