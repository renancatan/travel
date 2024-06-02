function travelSheetData(rows) {
    if (rows.length) {
        const data = rows.map(row => {
            let coordinates = [];
            if (row[16] && row[17]) {
                const lat = parseFloat(row[16].replace(',', '.').replace("'", ""));
                const lon = parseFloat(row[17].replace(',', '.').replace("'", ""));
                console.log(lat, lon);  // Log coordinates for debugging
                if (!isNaN(lat) && !isNaN(lon)) {
                    coordinates = [lat, lon];
                }
            }

            return {
                coordinates: coordinates,
                city: row[5] || 'unknown',  // 'location_name' corresponds to 'city'
                region: null,  // No region in the new structure
                categories: row[2] ? row[2].split(',') : [],  // 'category' corresponds to 'categories'
                country: 'unknown',  // No country in the new structure
                province: 'unknown',  // No province in the new structure
                images: [],  // No images in the new structure
                prices: row[15] ? row[15].replace(',', '.') : null,  // 'amount' corresponds to 'prices'
                additionalInfo: row[4] || null,  // 'description' corresponds to 'additionalInfo'
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
