const express = require('express');
const path = require('path');

const app = express();
const port = 3000;

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

app.listen(port, () => {
    console.log(`App listening on http://localhost:${port}`);
});