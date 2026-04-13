// const express = require('express');
// const path = require('path');
// const getSheetData = require('./public/js/google/sheets.js');
// require('dotenv').config();

// const app = express();
// const port = 3000;

// app.use(express.static(path.join(__dirname, 'public')));

// app.get('/data', async (req, res) => {
//     try {
//         const data = await getSheetData();
//         res.json(data);
//     } catch (error) {
//         console.error('Failed to fetch data from Google Sheets:', error);
//         res.status(500).send('Failed to fetch data from Google Sheets');
//     }
// });

// app.listen(port, () => {
//     console.log(`App listening on http://localhost:${port}`);
// });

// bar: L.icon({ iconUrl: `${workerBaseURL + "/"}bar-icon2.png`, iconSize: [50, 50] }),
// iconUrl: `${workerBaseURL + "/" + "Drink-Beer-icon.png"}`, iconSize: [50, 50]


const num = "125,13"
console.log(num.replace(",", "."))

const t = "TRUE"
const x = t === ("VERDADEIRO" || "TRUE")
console.log(x)

require('dotenv').config();
console.log('R2_ACCESS_KEY:', process.env.R2_ACCESS_KEY);
console.log('R2_SECRET_KEY:', process.env.R2_SECRET_KEY);


fetch('/data')
  .then(response => {
    if (!response.ok) {
      throw new Error('Network response was not ok ' + response.statusText);
    }
    return response.json();
  })
  .then(mergedData => {
    console.log('Merged data:', JSON.stringify(mergedData, null, 2));
    allLocations = mergedData;
    populateFilters(mergedData, 'regionFilter', 'categoryFilter');
    updateMarkers(mergedData);
  })
  .catch(error => {
    console.error('Failed to fetch data:', error);
  });


  // setYoutubeUrl/modal


  // hash -> b3ea7a6 // 92db9d4 -> funciona modal e preco do gglSheets

  // hash -> 5835395 -> funciona modal e preco do gglSheets E YOUTUBE

  // hash -> 949eaf1 -> funciona modal e preco do gglSheets E YOUTUBE EE ICONES
  
  