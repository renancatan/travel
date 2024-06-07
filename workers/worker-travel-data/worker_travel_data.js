addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const url = new URL(request.url);
  console.log('Worker: Received request for', url.pathname);

  if (url.pathname === '/data') {
    console.log('Worker: Handling /data request');
    const apiUrl = 'https://2e05-177-220-182-212.ngrok-free.app/data'; // Your ngrok URL

    try {
      const response = await fetch(apiUrl);
      console.log('Worker: Response from local server received', response.status);

      if (!response.ok) {
        console.error(`Worker: Failed to fetch data from the API, status: ${response.status}`);
        return new Response('Failed to fetch data from the API', { status: 500 });
      }

      const data = await response.json();
      console.log('Worker: Data successfully fetched from local server', data);
      const headers = new Headers({
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*', // Allow all origins for CORS
        'Access-Control-Allow-Methods': 'GET', // Allow only GET requests
        'Access-Control-Allow-Headers': 'Content-Type', // Allow only Content-Type header
      });
      return new Response(JSON.stringify(data), { headers });
    } catch (error) {
      console.error('Worker: Error fetching data from local server:', error);
      return new Response('Failed to fetch data from the API', { status: 500 });
    }
  }

  console.log('Worker: Default response');
  return new Response('Hello World!', { status: 200 });
}
