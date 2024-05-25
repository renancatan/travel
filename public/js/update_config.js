const fs = require('fs');
const path = require('path');
const metadata = require('./metadata.json');

function updateConfigWithImages(basePath, metadata) {
    const config = {
        locations: {}
    };

    metadata.forEach(location => {
        const countryData = config.locations[location.country] = config.locations[location.country] || { name: location.country, regions: {}, provinces: {} };
        const regionData = countryData.regions[location.region] = countryData.regions[location.region] || { name: location.region, provinces: {} };
        const provinceData = regionData.provinces[location.province] = regionData.provinces[location.province] || { name: location.province, cities: {} };
        const cityData = provinceData.cities[location.city] = provinceData.cities[location.city] || { name: location.city, coordinates: location.coordinates, images: [], categories: location.categories, subLocations: {} };

        const locationPath = path.join(basePath, location.country, location.region || '', location.province, location.city);
        if (fs.existsSync(locationPath) && fs.lstatSync(locationPath).isDirectory()) {
            const files = fs.readdirSync(locationPath);
            files.forEach(file => {
                const filePath = path.join(locationPath, file);
                if (!fs.lstatSync(filePath).isDirectory()) {
                    cityData.images.push(file);
                }
            });

            location.categories.forEach(category => {
                const categoryPath = path.join(locationPath, category);
                if (fs.existsSync(categoryPath) && fs.lstatSync(categoryPath).isDirectory()) {
                    const categoryFiles = fs.readdirSync(categoryPath);
                    categoryFiles.forEach(file => {
                        const filePath = path.join(categoryPath, file);
                        if (!fs.lstatSync(filePath).isDirectory()) {
                            cityData.images.push(file);
                        }
                    });

                    if (location.subLocations) {
                        location.subLocations.forEach(subLocation => {
                            const subLocationPath = path.join(categoryPath, subLocation.name);
                            if (fs.existsSync(subLocationPath) && fs.lstatSync(subLocationPath).isDirectory()) {
                                const subLocationFiles = fs.readdirSync(subLocationPath);
                                subLocationFiles.forEach(file => {
                                    const filePath = path.join(subLocationPath, file);
                                    if (!fs.lstatSync(filePath).isDirectory()) {
                                        cityData.subLocations[subLocation.name] = cityData.subLocations[subLocation.name] || { name: subLocation.name, coordinates: subLocation.coordinates, images: [] };
                                        cityData.subLocations[subLocation.name].images.push(file);
                                    }
                                });
                            }
                        });
                    }
                }
            });
        }
    });

    return config;
}

function saveConfig(filePath, config) {
    const configContent = `export const locations = ${JSON.stringify(config, null, 2)};`;
    fs.writeFileSync(filePath, configContent, 'utf8');
}

function main() {
    const basePath = path.join(__dirname, '../../uploads');
    const updatedConfig = updateConfigWithImages(basePath, metadata);

    const outputPath = path.join(__dirname, 'config.js');
    console.log("Output path config.js for update_config: ", outputPath);
    saveConfig(outputPath, updatedConfig);

    console.log('Config updated successfully!');
}

main();
