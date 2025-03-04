from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from ultralytics import YOLO
import os
import base64
import cv2
import numpy as np
import pyrebase
import torch
import psutil

app = Flask(__name__)
CORS(app)

firebaseConfig = {
  'apiKey': "AIzaSyBTptL4v2ONEmn5CCNGSY3FeefTofz3wp4",
  'authDomain': "deteccao-de-plantas.firebaseapp.com",
  'projectId': "deteccao-de-plantas",
  'storageBucket': "deteccao-de-plantas.firebasestorage.app",
  'databaseURL': "https://deteccao-de-plantas-default-rtdb.firebaseio.com",
  'messagingSenderId': "144203838962",
  'appId': "1:144203838962:web:a62e7f8f2c6adc77f3276b"
}
firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()


# Carrega os pesos manualmente com weights_only=False
checkpoint = torch.load("best.pt", weights_only=False, map_location='cpu')
model = YOLO("best.pt")  # O YOLO ainda precisa do caminho, mas agora ele deve aceitar o carregamento prévio

@app.route("/")
def inicio():
    return render_template("front.html")

@app.route("/camera")
def camera():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process_image():
    data = request.json
    image_data = data["image"]

    image_data = image_data.split(",")[1]
    image_bytes = base64.b64decode(image_data)
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    results = model(image)
    annotated_frame = results[0].plot()

    if len(results) > 0 and len(results[0].boxes.cls) > 0:
        detected_plant = results[0].names[results[0].boxes.cls[0].item()]
    else:
        detected_plant = "Nenhuma planta detectada"

    _, buffer = cv2.imencode(".jpg", annotated_frame)
    processed_image_data = base64.b64encode(buffer).decode("utf-8")

    return jsonify({
        "processed_image": f"data:image/jpeg;base64,{processed_image_data}",
        "plant_name": detected_plant
    })

@app.route("/info/<plant_name>")
def show_plant_info(plant_name):
    try:
        doc_ref = db.child("plantas").child(plant_name)
        doc = doc_ref.get()

        if doc.val() is None:
            return "Planta não encontrada.", 404
        info = doc.val()
        print(doc.val())
        return render_template('info.html', plant=info)

    except Exception as e:
        return f"Erro ao acessar o banco de dados: {e}", 500

@app.route('/monitor')
def monitor():
    # Uso de CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # Uso de memória
    memory = psutil.virtual_memory()
    ram_percent = memory.percent
    ram_used = memory.used / (1024 * 1024 * 1024)  # Convertendo para GB
    ram_total = memory.total / (1024 * 1024 * 1024)  # Convertendo para GB
    
    # Uso específico do processo Python
    process = psutil.Process()
    python_cpu = process.cpu_percent(interval=1)
    python_memory = process.memory_info().rss / (1024 * 1024)  # MB
    
    return jsonify({
        'sistema': {
            'cpu_total': f"{cpu_percent}%",
            'ram_total': f"{ram_percent}%",
            'ram_usado': f"{ram_used:.2f}GB",
            'ram_total_gb': f"{ram_total:.2f}GB"
        },
        'processo_python': {
            'cpu': f"{python_cpu}%",
            'memoria': f"{python_memory:.2f}MB"
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
#ssl_context=('cert.pem', 'key.pem')