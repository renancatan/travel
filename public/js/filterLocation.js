export const filterCategory = function filterLocationsByCategory(locations, category) {
    const filteredLocations = {};

    Object.keys(locations).forEach((country) => {
        const countryData = locations[country];
        filteredLocations[country] = {};

        const processProvinces = (provinces, region = null) => {
            Object.keys(provinces).forEach((province) => {
                const provinceData = provinces[province];
                filteredLocations[country][region || province] = filteredLocations[country][region || province] || {};

                Object.keys(provinceData.cities).forEach((city) => {
                    const cityData = provinceData.cities[city];

                    if (cityData.categories.includes(category)) {
                        filteredLocations[country][region || province][city] = {
                            coordinates: cityData.coordinates,
                            images: cityData.images || [],
                            category: category
                        };
                    }
                });
            });
        };

        if (countryData.regions) {
            Object.keys(countryData.regions).forEach((region) => {
                const regionData = countryData.regions[region];
                filteredLocations[country][region] = {};

                processProvinces(regionData.provinces, region);
            });
        } else if (countryData.provinces) {
            processProvinces(countryData.provinces);
        }
    });

    return filteredLocations;
};