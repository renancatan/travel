async function handleRequest(request, env) {
    const url = new URL(request.url);
    const objectKey = url.pathname.slice(1); // Extracts the path after the leading "/"
    const acc_id_cloudflare = "34b20cfe4942c861ec708ab9d5f8c6b9"
    const bucketName = 'travels'; // Adjust to match your bucket name
    const baseURL = `https://${acc_id_cloudflare}.r2.cloudflarestorage.com/${bucketName}/${objectKey}`;

    // Reference the R2 API Token from the `env` object
    const r2ApiToken = env.R2_API_TOKEN;

    // Fetch the object from R2 with authorization
    const response = await fetch(baseURL, {
        headers: {
            'Authorization': `Bearer ${r2ApiToken}`,
        },
    });

    if (response.ok) {
        return new Response(response.body, {
            headers: { 'content-type': response.headers.get('content-type') }
        });
    } else {
        return new Response(`Object not found: ${objectKey}`, { status: 404 });
    }
}

export default {
    async fetch(request, env) {
        const bucket = env.MY_BUCKET; // Reference the binding from wrangler.toml
        const url = new URL(request.url);
        const objectKey = url.pathname.slice(1); // Remove leading "/"

        // Fetch the object from the R2 bucket
        const object = await bucket.get(objectKey);

        if (!object) {
            return new Response(`Object not found: ${objectKey}`, { status: 404 });
        }

        return new Response(object.body, {
            headers: { 'content-type': object.httpMetadata.contentType || 'application/octet-stream' }
        });
    }
}
