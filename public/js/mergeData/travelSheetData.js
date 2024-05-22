function mergeData(primaryData, secondaryData) {
    const primaryMap = new Map();
    primaryData.forEach(item => primaryMap.set(item.city, item));

    secondaryData.forEach(item => {
        if (primaryMap.has(item.city)) {
            const primaryItem = primaryMap.get(item.city);
            primaryItem.categories = [...new Set([...primaryItem.categories, ...item.categories])];
            primaryItem.images = [...new Set([...primaryItem.images, ...item.images])];
            primaryItem.region = primaryItem.region || item.region;
            primaryItem.country = primaryItem.country || item.country;
            primaryItem.province = primaryItem.province || item.province;
            primaryItem.coordinates = primaryItem.coordinates.length ? primaryItem.coordinates : item.coordinates;
        } else {
            primaryMap.set(item.city, item);
        }
    });

    return Array.from(primaryMap.values());
}

module.exports = mergeData;
