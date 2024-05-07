addEventListener('fetch', event => {
    event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
    // Parse the URL to extract the object key from the request path
    const url = new URL(request.url);
    const objectKey = url.pathname.slice(1); // Extract the path after the leading "/"
    const bucketName = 'travels'; // Change to your bucket name
    const baseURL = `https://34b20cfe4942c861ec708ab9d5f8c6b9.r2.cloudflarestorage.com/${bucketName}/${objectKey}`;

    // Fetch the object from R2
    const response = await fetch(baseURL, {
        headers: {
            'Authorization': `Bearer ${R2_API_TOKEN}`, // Replace with your Wrangler secret
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
