const express = require('express');
const path = require('path');
const NodeCache = require('node-cache');
const getSheetData = require('./public/js/google/services/sheetsService.js');
const travelSheetData = require('./public/js/google/travelSheet.js');
const mergeData = require('./public/js/mergeData/travelSheetData.js');
const fs = require('fs');
require('dotenv').config();

const app = express();
const port = 3000;
const cache = new NodeCache({ stdTTL: 300 });

app.use((req, res, next) => {
    console.log(`Received request for: ${req.url}`);
    next();
});

app.use(express.static(path.join(__dirname, 'public')));

app.get('/metadata.json', (req, res) => {
    res.sendFile(path.join(__dirname, 'public/js/metadata.json'));
});

app.get('/data', async (req, res) => {
    try {
        const cachedData = cache.get('sheetData');
        if (cachedData) {
            return res.json(cachedData);
        }

        const metadataPath = path.join(__dirname, 'public/js/metadata.json');
        const primaryData = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));

        let secondaryData = [];
        try {
            const sheetData = await getSheetData(process.env.SPREADSHEET_ID, `${process.env.SPREADSHEET_NAME}!A2:Z`);
            secondaryData = travelSheetData(sheetData);
        } catch (sheetError) {
            console.error('Failed to fetch or process data from Google Sheets:', sheetError);
        }

        const mergedData = mergeData(primaryData, secondaryData);
        cache.set('sheetData', mergedData);
        res.json(mergedData);
    } catch (error) {
        console.error('Failed to fetch data:', error);
        res.status(500).send('Failed to fetch data');
    }
});

app.listen(port, () => {
    console.log(`App listening on http://localhost:${port}`);
});
