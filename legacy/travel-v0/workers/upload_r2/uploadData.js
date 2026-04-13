const AWS = require('aws-sdk');
const fs = require('fs');
require('dotenv').config({path: ".env"});


const r2AccessKey = process.env.R2_ACCESS_KEY;
const r2SecretKey = process.env.R2_SECRET_KEY;
const bucketName = 'data';

console.log('R2_ACCESS_KEY:', process.env.R2_ACCESS_KEY);
console.log('R2_SECRET_KEY:', process.env.R2_SECRET_KEY);

// Configure the AWS SDK with Cloudflare R2 credentials
const s3 = new AWS.S3({
    accessKeyId: r2AccessKey,
    secretAccessKey: r2SecretKey,
    endpoint: 'https://34b20cfe4942c861ec708ab9d5f8c6b9.r2.cloudflarestorage.com',
    region: 'auto',
    signatureVersion: 'v4',
  });

// Upload file to R2
const uploadFile = async (bucketName, key, filePath) => {
  try {
    const fileContent = fs.readFileSync(filePath);

    const params = {
      Bucket: bucketName,
      Key: key,
      Body: fileContent,
      ContentType: 'application/json',
    };

    const data = await s3.upload(params).promise();
    console.log(`File uploaded successfully. ${data.Location}`);
  } catch (error) {
    console.error('Error uploading file:', error);
  }
};

// Usage
const key = 'metadata/data.json';
const filePath = './data.json';

uploadFile(bucketName, key, filePath);
