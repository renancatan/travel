const express = require('express');
const path = require('path');
const NodeCache = require('node-cache');
const fetch = require('node-fetch');
const getSheetData = require('./public/js/google/services/sheetsService.js');
const travelSheetData = require('./public/js/google/travelSheet.js');
const mergeData = require('./public/js/mergeData/travelSheetData.js');
const fs = require('fs');
require('dotenv').config();

const app = express();
const port = 3000;
const cache = new NodeCache({ stdTTL: 300 });

const WORKER_URL = 'https://worker-travel-data.renancatan4.workers.dev/data';

app.use((req, res, next) => {
    console.log(`Server: Received request for: ${req.url}`);
    next();
});

app.use(express.static(path.join(__dirname, 'public')));

app.get('/metadata.json', (req, res) => {
    console.log('Server: Sending metadata.json');
    res.sendFile(path.join(__dirname, 'public/js/metadata.json'));
});

app.get('/data', async (req, res) => {
    try {
        const cachedData = cache.get('sheetData');
        if (cachedData) {
            // needs '/data' in map.js and accessing localhost... /data
            console.log("Saved json file")
            fs.writeFileSync('data.json', JSON.stringify(cachedData, null, 2));
            return res.json(cachedData);
        }

        const metadataPath = path.join(__dirname, 'public/js/metadata.json');
        const primaryData = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
        console.log('Server: Primary data loaded');

        let secondaryData = [];
        try {
            const sheetData = await getSheetData(process.env.SPREADSHEET_ID, `${process.env.SPREADSHEET_NAME}!A2:Z`);
            secondaryData = travelSheetData(sheetData);
            console.log('Server: Secondary data fetched from Google Sheets');
        } catch (sheetError) {
            console.error('Server: Failed to fetch or process data from Google Sheets:', sheetError);
        }

        const mergedData = mergeData(primaryData, secondaryData);
        cache.set('sheetData', mergedData);
        console.log('Server: Returning merged data');
        res.json(mergedData);
    } catch (error) {
        console.error('Server: Failed to fetch data:', error);
        res.status(500).send('Failed to fetch data');
    }
});

app.listen(port, () => {
    console.log(`Server: Proxy server listening at http://localhost:${port}`);
});
