const express = require('express');
const path = require('path');
const getSheetData = require('./public/js/google/sheets.js');

const app = express();
const port = 3000;

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
        const data = await getSheetData();
        res.json(data);
    } catch (error) {
        console.error('Failed to fetch data from Google Sheets:', error);
        res.status(500).send('Failed to fetch data from Google Sheets');
    }
});

app.listen(port, () => {
    console.log(`App listening on http://localhost:${port}`);
});
