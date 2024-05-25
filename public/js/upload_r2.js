const AWS = require('aws-sdk');
const fs = require('fs');
const path = require('path');
require('dotenv').config({path: '.env'});

const r2AccessKey = process.env.R2_ACCESS_KEY;
const r2SecretKey = process.env.R2_SECRET_KEY;
const bucketName = 'travels';
console.log('R2_ACCESS_KEY:', process.env.R2_ACCESS_KEY);
console.log('R2_SECRET_KEY:', process.env.R2_SECRET_KEY);

const s3 = new AWS.S3({
  accessKeyId: r2AccessKey,
  secretAccessKey: r2SecretKey,
  endpoint: 'https://34b20cfe4942c861ec708ab9d5f8c6b9.r2.cloudflarestorage.com',
  region: 'auto',
  signatureVersion: 'v4',
});

const place = "ph/mindanao/davao_del_sur/davao/"
const specificRegion = "bars/bar_name/"
const general = "general/"
const remotePrefix = `${place}${general}`;
const localImageDir = path.join(__dirname, `../../uploads/${remotePrefix}`);

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
