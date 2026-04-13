addEventListener('fetch', event => {
    event.respondWith(handleRequest(event.request))
  })


async function handleRequest(request) {
    const url = new URL(request.url)
    const pathname = url.pathname
  
    const basePath = 'https://34b20cfe4942c861ec708ab9d5f8c6b9.r2.cloudflarestorage.com/travels'
    const objectPath = `${basePath}${pathname}`
  
    const response = await fetch(objectPath, {
      headers: {
            'Authorization': `Bearer ${r2ApiToken}`,
        },
    })
    const contentType = getContentType(pathname)
  
    return new Response(response.body, {
      headers: { 'Content-Type': contentType }
    })
  }

function getContentType(pathname) {
if (pathname.endsWith('.jpg') || pathname.endsWith('.jpeg')) {
    return 'image/jpeg'
} else if (pathname.endsWith('.png')) {
    return 'image/png'
} else if (pathname.endsWith('.gif')) {
    return 'image/gif'
} else {
    return 'application/octet-stream'
}
}