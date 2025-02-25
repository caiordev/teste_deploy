const video = document.querySelector("video");
const captureBtn = document.getElementById("capture-btn");
const processingScreen = document.getElementById("processing-screen");
const capturedImage = document.getElementById("captured-image");
const detectionBox = document.querySelector(".detection-box");
const feedbackModal = new bootstrap.Modal(document.getElementById('feedbackModal'));

let currentStream = null;

// Função para iniciar a câmera
async function startCamera(facingMode = 'environment') {
    try {
        if (currentStream) {
            currentStream.getTracks().forEach(track => track.stop());
        }

        const constraints = {
            video: {
                facingMode: facingMode,
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        };

        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        currentStream = stream;
        video.srcObject = stream;
        await video.play();
    } catch (error) {
        console.error("Erro ao acessar a câmera:", error);
        alert("Erro ao acessar a câmera. Por favor, certifique-se de que seu navegador tem permissão para usar a câmera.");
    }
}

// Função para mostrar a tela de processamento
function showProcessingScreen(imageData) {
    capturedImage.src = imageData;
    processingScreen.classList.add('show');
    
    // Simular o aparecimento da caixa de detecção após um breve delay
    setTimeout(() => {
        const imageWidth = capturedImage.offsetWidth;
        const imageHeight = capturedImage.offsetHeight;
        
        // Posicionar a caixa de detecção no centro da imagem
        detectionBox.style.width = `${imageWidth * 0.8}px`;
        detectionBox.style.height = `${imageHeight * 0.8}px`;
        detectionBox.style.left = `${imageWidth * 0.1}px`;
        detectionBox.style.top = `${imageHeight * 0.1}px`;
        detectionBox.classList.add('show');
    }, 500);
}

// Função para esconder a tela de processamento
function hideProcessingScreen() {
    processingScreen.classList.remove('show');
    detectionBox.classList.remove('show');
}

// Iniciar com a câmera traseira por padrão
startCamera();

captureBtn.addEventListener("click", async () => {
    const canvas = document.createElement("canvas");
    canvas.height = video.videoHeight;
    canvas.width = video.videoWidth;

    const context = canvas.getContext("2d");
    context.drawImage(video, 0, 0);

    const imageData = canvas.toDataURL("image/jpeg");
    showProcessingScreen(imageData);

    try {
        const response = await fetch("/process", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ image: imageData }),
        });

        if (!response.ok) {
            throw new Error("Erro ao processar a imagem no backend");
        }

        const data = await response.json();
        const detectedPlantName = data.plant_name;

        if (detectedPlantName === "Nenhuma planta detectada") {
            hideProcessingScreen();
            feedbackModal.show();
        } else {
            // Aguardar um momento para mostrar a animação da caixa de detecção
            setTimeout(() => {
                window.location.href = `/info/${detectedPlantName}`;
            }, 1500);
        }
    } catch (error) {
        console.error("Erro:", error);
        hideProcessingScreen();
        alert("Erro ao processar a imagem. Por favor, tente novamente.");
    }
});