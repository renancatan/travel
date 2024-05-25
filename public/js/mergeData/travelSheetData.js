function mergeData(primaryData, secondaryData) {
    const primaryMap = new Map();
    primaryData.forEach(item => primaryMap.set(item.city + JSON.stringify(item.coordinates), item));

    secondaryData.forEach(item => {
        const key = item.city + JSON.stringify(item.coordinates);
        if (primaryMap.has(key)) {
            const primaryItem = primaryMap.get(key);
            primaryItem.categories = [...new Set([...primaryItem.categories, ...item.categories])];
            primaryItem.images = [...new Set([...primaryItem.images, ...item.images])];
            primaryItem.region = primaryItem.region || item.region;
            primaryItem.country = primaryItem.country || item.country;
            primaryItem.province = primaryItem.province || item.province;
            primaryItem.coordinates = primaryItem.coordinates.length ? primaryItem.coordinates : item.coordinates;
            primaryItem.prices = primaryItem.prices || item.prices;
            primaryItem.additionalInfo = primaryItem.additionalInfo || item.additionalInfo;
        } else {
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
