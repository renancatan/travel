const fs = require('fs');
const path = require('path');
const metadata = require('./metadata.json');

function generateConfig(basePath, metadata) {
    const locations = {};

    Object.keys(metadata.countries).forEach((country) => {
        console.log(`Processing country: ${country}`);
        const countryData = metadata.countries[country];
        locations[country] = {};

        if (countryData.regions && Object.keys(countryData.regions).length > 0) {
            console.log(`Country has regions: ${Object.keys(countryData.regions)}`);
            Object.keys(countryData.regions).forEach((region) => {
                console.log(`Processing region: ${region}`);
                const regionData = countryData.regions[region];
                locations[country][region] = {};

                Object.keys(regionData.provinces).forEach((province) => {
                    console.log(`Processing province: ${province}`);
                    const provinceData = regionData.provinces[province];
                    locations[country][region][province] = {};

                    if (provinceData.cities && Object.keys(provinceData.cities).length > 0) {
                        Object.keys(provinceData.cities).forEach((city) => {
                            console.log(`Processing city: ${city}`);
                            const cityData = provinceData.cities[city];
                            locations[country][region][province][city] = {
                                coordinates: cityData.coordinates || [],
                                images: []
                            };

                            const cityPath = path.join(basePath, country, region, province, city);
                            if (fs.existsSync(cityPath) && fs.lstatSync(cityPath).isDirectory()) {
                                const files = fs.readdirSync(cityPath);
                                files.forEach((file) => {
                                    const filePath = path.join(cityPath, file);
                                    if (!fs.lstatSync(filePath).isDirectory()) {
                                        locations[country][region][province][city].images.push(file);
                                    }
                                });
                            }

                            cityData.categories.forEach((category) => {
                                const categoryPath = path.join(cityPath, category);
                                console.log(`Checking path: ${categoryPath}`);

                                if (fs.existsSync(categoryPath) && fs.lstatSync(categoryPath).isDirectory()) {
                                    const files = fs.readdirSync(categoryPath);
                                    files.forEach((file) => {
                                        const filePath = path.join(categoryPath, file);
                                        if (!fs.lstatSync(filePath).isDirectory()) {
                                            locations[country][region][province][city].images.push(file);
                                        }
                                    });
                                } else {
                                    console.log(`Path does not exist or is not a directory: ${categoryPath}`);
                                }
                            });
                        });
                    }
                });
            });
        } else if (countryData.provinces && Object.keys(countryData.provinces).length > 0) {
            console.log(`Country has provinces: ${Object.keys(countryData.provinces)}`);
            Object.keys(countryData.provinces).forEach((province) => {
                console.log(`Processing province: ${province}`);
                const provinceData = countryData.provinces[province];
                locations[country][province] = {};

                if (provinceData.cities && Object.keys(provinceData.cities).length > 0) {
                    Object.keys(provinceData.cities).forEach((city) => {
                        console.log(`Processing city: ${city}`);
                        const cityData = provinceData.cities[city];
                        locations[country][province][city] = {
                            coordinates: cityData.coordinates || [],
                            images: []
                        };

                        const cityPath = path.join(basePath, country, province, city);
                        if (fs.existsSync(cityPath) && fs.lstatSync(cityPath).isDirectory()) {
                            const files = fs.readdirSync(cityPath);
                            files.forEach((file) => {
                                const filePath = path.join(cityPath, file);
                                if (!fs.lstatSync(filePath).isDirectory()) {
                                    locations[country][province][city].images.push(file);
                                }
                            });
                        }

                        cityData.categories.forEach((category) => {
                            const categoryPath = path.join(cityPath, category);
                            console.log(`Checking path: ${categoryPath}`);

                            if (fs.existsSync(categoryPath) && fs.lstatSync(categoryPath).isDirectory()) {
                                const files = fs.readdirSync(categoryPath);
                                files.forEach((file) => {
                                    const filePath = path.join(categoryPath, file);
                                    if (!fs.lstatSync(filePath).isDirectory()) {
                                        locations[country][province][city].images.push(file);
                                    }
                                });
                            } else {
                                console.log(`Path does not exist or is not a directory: ${categoryPath}`);
                            }
                        });
                    });
                }
            });
        } else {
            console.log(`No regions or provinces found for country: ${country}`);
        }
    });

    return locations;
}

function saveConfig(configPath, configContent) {
    fs.writeFileSync(configPath, configContent, 'utf8');
}

function main() {
    const basePath = path.join(__dirname, '../../uploads');
    const locations = generateConfig(basePath, metadata);

    const configPath = path.join(__dirname, 'config.js');
    const configContent = `export const locations = ${JSON.stringify(locations, null, 2)};\n`;

    console.log('Generated configuration:');
    console.log(configContent);

    saveConfig(configPath, configContent);
    console.log('Configuration updated successfully!');
}

main();
