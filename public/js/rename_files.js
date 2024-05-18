const fs = require('fs');
const path = require('path');
const readline = require('readline');

const metadata = JSON.parse(fs.readFileSync(path.join(__dirname, 'metadata.json'), 'utf8'));

function renameFiles(basePath, metadata) {
    Object.keys(metadata.countries).forEach((country) => {
        console.log(`Processing country: ${country}`);
        const countryData = metadata.countries[country];

        // Handle regions if present
        if (countryData.regions && Object.keys(countryData.regions).length > 0) {
            console.log(`Country has regions: ${Object.keys(countryData.regions)}`);
            Object.keys(countryData.regions).forEach((region) => {
                console.log(`Processing region: ${region}`);
                const regionData = countryData.regions[region];

                Object.keys(regionData.provinces).forEach((province) => {
                    console.log(`Processing province: ${province}`);
                    const provinceData = regionData.provinces[province];

                    if (provinceData.cities && Object.keys(provinceData.cities).length > 0) {
                        Object.keys(provinceData.cities).forEach((city) => {
                            console.log(`Processing city: ${city}`);
                            const cityData = provinceData.cities[city];

                            const cityPath = path.join(basePath, country, region, province, city);
                            if (fs.existsSync(cityPath) && fs.lstatSync(cityPath).isDirectory()) {
                                renameFilesInDirectory(cityPath, city, 'general');
                            } else {
                                console.log(`Path does not exist or is not a directory: ${cityPath}`);
                            }

                            cityData.categories.forEach((category) => {
                                const categoryPath = path.join(cityPath, category);
                                console.log(`Checking path: ${categoryPath}`);

                                if (fs.existsSync(categoryPath) && fs.lstatSync(categoryPath).isDirectory()) {
                                    renameFilesInDirectory(categoryPath, city, category);
                                } else {
                                    console.log(`Path does not exist or is not a directory: ${categoryPath}`);
                                }
                            });
                        });
                    }
                });
            });
        } else if (countryData.provinces && Object.keys(countryData.provinces).length > 0) {
            // Handle provinces if present
            console.log(`Country has provinces: ${Object.keys(countryData.provinces)}`);
            Object.keys(countryData.provinces).forEach((province) => {
                console.log(`Processing province: ${province}`);
                const provinceData = countryData.provinces[province];

                if (provinceData.cities && Object.keys(provinceData.cities).length > 0) {
                    Object.keys(provinceData.cities).forEach((city) => {
                        console.log(`Processing city: ${city}`);
                        const cityData = provinceData.cities[city];

                        const cityPath = path.join(basePath, country, province, city);
                        if (fs.existsSync(cityPath) && fs.lstatSync(cityPath).isDirectory()) {
                            renameFilesInDirectory(cityPath, city, 'general');
                        } else {
                            console.log(`Path does not exist or is not a directory: ${cityPath}`);
                        }

                        cityData.categories.forEach((category) => {
                            const categoryPath = path.join(cityPath, category);
                            console.log(`Checking path: ${categoryPath}`);

                            if (fs.existsSync(categoryPath) && fs.lstatSync(categoryPath).isDirectory()) {
                                renameFilesInDirectory(categoryPath, city, category);
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
}

function renameFilesInDirectory(directoryPath, city, category) {
    const files = fs.readdirSync(directoryPath);
    let counter = 1;

    files.forEach((file) => {
        const filePath = path.join(directoryPath, file);
        if (!fs.lstatSync(filePath).isDirectory()) {
            const ext = path.extname(file);
            const newName = `${city}_${category}_${counter}${ext}`;
            const newPath = path.join(directoryPath, newName);

            console.log(`Renaming file: ${filePath} to ${newPath}`);
            fs.renameSync(filePath, newPath);
            counter++;
        }
    });
}

// Prompt user for confirmation
function promptUser(question) {
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
    });

    return new Promise((resolve) => {
        rl.question(question, (answer) => {
            rl.close();
            resolve(answer.toLowerCase() === 'yes' || answer.toLowerCase() === 'y');
        });
    });
}

async function main() {
    const basePath = path.join(__dirname, '../../uploads');
    const confirm = await promptUser('Do you want to proceed with renaming files? (yes/no): ');

    if (confirm) {
        renameFiles(basePath, metadata);
        console.log('Files renamed successfully!');
    } else {
        console.log('Operation canceled.');
    }
}

main();
