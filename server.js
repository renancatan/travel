const express = require('express');
const path = require('path');

const app = express();
const port = 3000;

app.use((req, res, next) => {
    console.log(`Received request for: ${req.url}`);
    next();
});

// Serve static files from the 'public' directory
app.use(express.static(path.join(__dirname, 'public')));

// Serve metadata.json explicitly
app.get('/metadata.json', (req, res) => {
    res.sendFile(path.join(__dirname, 'public/js/metadata.json'));
});

app.listen(port, () => {
    console.log(`App listening on http://localhost:${port}`);
});
