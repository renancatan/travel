const fs = require('fs');
const path = require('path');
const metadata = require('./metadata.json');

function updateMetadataWithImages(basePath, metadata) {
    metadata.forEach(location => {
        const locationPath = path.join(basePath, location.country, location.region || '', location.province, location.city);
        if (fs.existsSync(locationPath) && fs.lstatSync(locationPath).isDirectory()) {
            const images = [];
            const files = fs.readdirSync(locationPath);
            files.forEach(file => {
                const filePath = path.join(locationPath, file);
                if (!fs.lstatSync(filePath).isDirectory()) {
                    images.push(file);
                }
            });
            location.images = images;

            location.categories.forEach(category => {
                const categoryPath = path.join(locationPath, category);
                if (fs.existsSync(categoryPath) && fs.lstatSync(categoryPath).isDirectory()) {
                    const categoryFiles = fs.readdirSync(categoryPath);
                    categoryFiles.forEach(file => {
                        const filePath = path.join(categoryPath, file);
                        if (!fs.lstatSync(filePath).isDirectory()) {
                            location.images.push(file);
                        }
                    });

                    if (location.subLocations) {
                        location.subLocations.forEach(subLocation => {
                            const subLocationPath = path.join(categoryPath, subLocation.name);
                            if (fs.existsSync(subLocationPath) && fs.lstatSync(subLocationPath).isDirectory()) {
                                const subLocationFiles = fs.readdirSync(subLocationPath);
                                subLocation.images = [];
                                subLocationFiles.forEach(file => {
                                    const filePath = path.join(subLocationPath, file);
                                    if (!fs.lstatSync(filePath).isDirectory()) {
                                        subLocation.images.push(file);
                                    }
                                });
                            }
                        });
                    }
                } else {
                    console.log(`Category path does not exist or is not a directory: ${categoryPath}`);
                }
            });
        } else {
            console.log(`Path does not exist or is not a directory: ${locationPath}`);
        }
    });

    return metadata;
}

function saveMetadata(filePath, metadata) {
    fs.writeFileSync(filePath, JSON.stringify(metadata, null, 2), 'utf8');
}

function main() {
    const basePath = path.join(__dirname, '../../uploads');
    const updatedMetadata = updateMetadataWithImages(basePath, metadata);

    const outputPath = path.join(__dirname, 'metadata.json');
    saveMetadata(outputPath, updatedMetadata);

    console.log('Metadata updated successfully!');
}

main();
