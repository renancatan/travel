const fs = require('fs');
const path = require('path');
const readline = require('readline');

const metadata = JSON.parse(fs.readFileSync(path.join(__dirname, 'metadata.json'), 'utf8'));

function renameFiles(basePath, metadata) {
    metadata.forEach(location => {
        const locationPath = path.join(basePath, location.country, location.region || '', location.province, location.city);
        if (fs.existsSync(locationPath) && fs.lstatSync(locationPath).isDirectory()) {
            renameFilesInDirectory(locationPath, location.city, 'general');

            location.categories.forEach(category => {
                const categoryPath = path.join(locationPath, category);
                if (fs.existsSync(categoryPath) && fs.lstatSync(categoryPath).isDirectory()) {
                    renameFilesInDirectory(categoryPath, location.city, category);
                } else {
                    console.log(`Path does not exist or is not a directory: ${categoryPath}`);
                }
            });
        } else {
            console.log(`Path does not exist or is not a directory: ${locationPath}`);
        }
    });
}

function renameFilesInDirectory(directoryPath, city, category) {
    const files = fs.readdirSync(directoryPath);
    let counter = 1;

    files.forEach(file => {
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
