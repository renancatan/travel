function mergeData(primaryData, secondaryData) {
    const formatCoordinates = (coordinates) => coordinates.map(coord => coord.toFixed(4)).join(',');

    const primaryMap = new Map();
    primaryData.forEach(item => {
        const key = formatCoordinates(item.coordinates);
        primaryMap.set(key, item);
    });

    secondaryData.forEach(item => {
        const key = formatCoordinates(item.coordinates);
        console.log(`Secondary item key: ${key}, Secondary item: ${JSON.stringify(item, null, 2)}`);

        if (primaryMap.has(key)) {
            const primaryItem = primaryMap.get(key);
            console.log(`Matching primary item: ${JSON.stringify(primaryItem, null, 2)}`);

            primaryItem.categories = [...new Set([...primaryItem.categories, ...item.categories])];
            primaryItem.images = [...new Set([...primaryItem.images, ...item.images])];
            primaryItem.region = primaryItem.region || item.region;
            primaryItem.country = primaryItem.country || item.country;
            primaryItem.province = primaryItem.province || item.province;
            primaryItem.coordinates = primaryItem.coordinates.length ? primaryItem.coordinates : item.coordinates;
            primaryItem.prices = primaryItem.prices || item.prices;
            primaryItem.additionalInfo = primaryItem.additionalInfo || item.additionalInfo;
        } else {
            console.log(`No match found for secondary item: ${JSON.stringify(item, null, 2)}`);
            primaryMap.set(key, item);
        }
    });

    // Filter out any invalid images
    primaryMap.forEach(item => {
        item.images = item.images.filter(image => /\.(jpg|jpeg|png|gif)$/.test(image));
    });

    return Array.from(primaryMap.values());
}

module.exports = mergeData;
