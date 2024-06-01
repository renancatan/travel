const fs = require('fs');
const path = require('path');
const readline = require('readline');

const metadata = JSON.parse(fs.readFileSync(path.join(__dirname, 'metadata.json'), 'utf8'));

function renameFiles(basePath, metadata) {
    console.log(`Starting renaming process in base path: ${basePath}`);
    metadata.forEach(location => {
        const locationPath = path.join(basePath, location.country, location.region || '', location.province, location.city);
        console.log(`Processing location: ${location.city} at path: ${locationPath}`);
        
        if (fs.existsSync(locationPath) && fs.lstatSync(locationPath).isDirectory()) {
            console.log(`Found location directory: ${locationPath}`);
            renameFilesInDirectory(locationPath, location.city, 'general');

            location.categories.forEach(category => {
                const categoryPath = path.join(locationPath, category);
                console.log(`Processing category: ${category} at path: ${categoryPath}`);
                
                if (fs.existsSync(categoryPath) && fs.lstatSync(categoryPath).isDirectory()) {
                    console.log(`Found category directory: ${categoryPath}`);
                    renameFilesInDirectory(categoryPath, location.city, category);

                    // Check and rename files in sub-locations
                    if (location.name) {
                        const subLocPath = path.join(categoryPath, location.name.toLowerCase().replace(/ /g, '_'));
                        console.log(`Processing sub-location: ${location.name} at path: ${subLocPath}`);
                        
                        if (fs.existsSync(subLocPath) && fs.lstatSync(subLocPath).isDirectory()) {
                            console.log(`Found sub-location directory: ${subLocPath}`);
                            renameFilesInDirectory(subLocPath, location.city, category, location.name.toLowerCase().replace(/ /g, '_'));
                        } else {
                            console.log(`Sub-location path does not exist or is not a directory: ${subLocPath}`);
                        }
                    }
                } else {
                    console.log(`Category path does not exist or is not a directory: ${categoryPath}`);
                }
            });
        } else {
            console.log(`Location path does not exist or is not a directory: ${locationPath}`);
        }
    });
}

function renameFilesInDirectory(directoryPath, city, category, subLocation = null) {
    const files = fs.readdirSync(directoryPath);
    console.log(`Renaming files in directory: ${directoryPath}, found ${files.length} files.`);
    let counter = 1;

    files.forEach(file => {
        const filePath = path.join(directoryPath, file);
        if (!fs.lstatSync(filePath).isDirectory()) {
            const ext = path.extname(file);
            const newName = subLocation
                ? `${city}_${category}_${subLocation}_${counter}${ext}`
                : `${city}_${category}_${counter}${ext}`;
            const newPath = path.join(directoryPath, newName);

            console.log(`Renaming file: ${filePath} to ${newPath}`);
            fs.renameSync(filePath, newPath);
            counter++;
        } else {
            console.log(`Skipping directory: ${filePath}`);
        }
    });
}

function promptUser(question) {
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
    });

    return new Promise(resolve => {
        rl.question(question, answer => {
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
