const AWS = require('aws-sdk');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

const r2AccessKey = '';
const r2SecretKey = '';
const bucketName = 'travels';

const s3 = new AWS.S3({
  accessKeyId: r2AccessKey,
  secretAccessKey: r2SecretKey,
  endpoint: 'https://34b20cfe4942c861ec708ab9d5f8c6b9.r2.cloudflarestorage.com',
  region: 'auto',
  signatureVersion: 'v4',
});

// Define the directory structure
const localImageDir = path.join(__dirname, '../../uploads/br/sp/eldorado/caves');
const remotePrefix = 'br/sp/eldorado/caves/';

// Upload images
fs.readdir(localImageDir, (err, files) => {
  if (err) {
    console.error('Error reading directory:', err);
    return;
  }

  files.forEach((imageFile) => {
    if (imageFile.endsWith('.jpg') || imageFile.endsWith('.jpeg') || imageFile.endsWith('.png')) {
      const localPath = path.join(localImageDir, imageFile);
      const remotePath = `${remotePrefix}${imageFile}`;

      const fileContent = fs.readFileSync(localPath);

      const params = {
        Bucket: bucketName,
        Key: remotePath,
        Body: fileContent,
      };

      s3.upload(params, (err, data) => {
        if (err) {
          console.error(`Error uploading ${imageFile}:`, err);
        } else {
          console.log(`Successfully uploaded ${imageFile} to ${data.Location}`);
        }
      });
    }
  });
});
