const workerURL = `https://worker-cloudflare.renancatan4.workers.dev/${imageName}`;
fetch(workerURL)
    .then(response => response.blob())
    .then(imageBlob => {
        // Display the fetched image in your application
        const imageUrl = URL.createObjectURL(imageBlob);
        const imgElement = document.createElement("img");
        imgElement.src = imageUrl;
        document.body.appendChild(imgElement); // Adjust this to integrate with your map UI
    })
    .catch(error => {
        console.error('Error fetching image:', error);
    });
