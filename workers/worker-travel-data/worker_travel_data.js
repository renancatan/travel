addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const url = new URL(request.url);

  if (url.pathname === '/data') {
    const key = 'metadata/data.json'; // Path to the file in the R2 bucket

    try {
      const object = await MY_BUCKET.get(key);
      if (object === null) {
        return new Response('Object Not Found', { status: 404 });
      }

      const headers = new Headers();
      object.writeHttpMetadata(headers);
      headers.set('etag', object.httpEtag);

      return new Response(object.body, {
        headers: {
          ...headers,
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    } catch (error) {
      console.error('Error fetching data from bucket:', error);
      return new Response('Failed to fetch data from the bucket', { status: 500 });
    }
  }

  return new Response('Hello World!', { status: 200 });
}
