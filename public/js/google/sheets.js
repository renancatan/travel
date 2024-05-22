const fs = require('fs');
const { google } = require('googleapis');
require('dotenv').config();

const SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
];

const credentials = {
    "type": process.env.TYPE,
    "project_id": process.env.PROJECT_ID,
    "private_key_id": process.env.PRIVATE_KEY_ID,
    "private_key": process.env.PRIVATE_KEY.replace(/\\n/g, '\n'),
    "client_email": process.env.CLIENT_EMAIL,
    "client_id": process.env.CLIENT_ID,
    "auth_uri": process.env.AUTH_URI,
    "token_uri": process.env.TOKEN_URI,
    "auth_provider_x509_cert_url": process.env.AUTH_PROVIDER_X509_CERT_URL,
    "client_x509_cert_url": process.env.CLIENT_X509_CERT_URL
};

const auth = new google.auth.GoogleAuth({
    credentials,
    scopes: SCOPES,
});

async function getSheetData() {
    const client = await auth.getClient();
    const sheets = google.sheets({ version: 'v4', auth: client });
    const spreadsheetId = process.env.SPREADSHEET_ID;
    const range = `${process.env.SPREADSHEET}!A2:Z`;

    const res = await sheets.spreadsheets.values.get({
        spreadsheetId,
        range,
    });

    const rows = res.data.values;
    if (rows.length) {
        console.log('Data from Google Sheets:');
        rows.forEach((row) => {
            console.log(`${row[0]}, ${row[1]}`);
        });
        return rows;
    } else {
        console.log('No data found.');
        return [];
    }
}

module.exports = getSheetData;
