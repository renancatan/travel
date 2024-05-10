const workerURL = `https://worker-cloudflare.renancatan4.workers.dev/${imageName}`;
console.log(`Fetching image from ${workerURL}`);
fetch(workerURL)
    .then(response => {
        if (!response.ok) {
            throw new Error(`Failed to fetch image: ${response.status}`);
        }
        return response.blob();
    })
    .then(imageBlob => {
        const imageUrl = URL.createObjectURL(imageBlob);
        const imgElement = document.createElement("img");
        imgElement.src = imageUrl;
        document.body.appendChild(imgElement);
    })
    .catch(error => {
        console.error('Error fetching image:', error);
    });
