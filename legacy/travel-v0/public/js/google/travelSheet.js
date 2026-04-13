function travelSheetData(rows) {
    if (rows.length) {
        const data = rows.map(row => {
            let coordinates = [];
            if (row[16] && row[17]) {
                const lat = parseFloat(row[16].replace(',', '.').replace("'", ""));
                const lon = parseFloat(row[17].replace(',', '.').replace("'", ""));
                console.log(lat, lon);
                if (!isNaN(lat) && !isNaN(lon)) {
                    coordinates = [lat, lon];
                }
            }

            return {
                coordinates: coordinates,
                city: row[5] || 'unknown',
                region: null,
                categories: row[2] ? row[2].split(',') : [],
                country: 'unknown',
                province: 'unknown',
                images: [],
                prices: row[15] ? row[15].replace(',', '.') : null,
                additionalInfo: row[6] || null,
                score: row[13] || null
            };
        });
        return data;
    } else {    
        console.log('No data found.');
        return [];
    }
}

module.exports = travelSheetData;
