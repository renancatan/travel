const express = require('express');
const path = require('path');

const app = express();
const port = 3000;

app.use((req, res, next) => {
    console.log(`Received request for: ${req.url}`);
    next();
});

app.use(express.static(path.join(__dirname, 'public')));

app.listen(port, () => {
    console.log(`App listening on http://localhost:${port}`);
});
