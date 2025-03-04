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

@app.route("/search")
def search_plants():
    return render_template("search.html")

@app.route("/api/search", methods=["POST"])
def api_search_plants():
    try:
        data = request.json
        characteristics = data.get("characteristics", {})
        print("Características de busca:", characteristics)
        
        # Buscar no Firebase
        try:
            # Primeiro, vamos verificar se conseguimos acessar o banco
            all_plants = []
            plants = db.get()  # Buscar todos os dados para debug
            print("Estrutura do banco:", plants.val())
            
            # Agora buscar as plantas
            plants_ref = db.child("plantas")  # Mudando de "plants" para "plantas"
            plants_data = plants_ref.get()
            print("Dados das plantas:", plants_data)
            
            if plants_data:
                # Converter os dados para uma lista
                for plant in plants_data.each():
                    plant_data = plant.val()
                    if isinstance(plant_data, dict):  # Verificar se é um dicionário válido
                        all_plants.append(plant_data)
            
            print(f"Total de plantas carregadas: {len(all_plants)}")
            
            if not all_plants:
                print("Nenhuma planta encontrada no Firebase")
                return jsonify({"plants": [], "message": "Nenhuma planta encontrada no banco de dados"})
            
            matched_plants = []
            for plant_data in all_plants:
                print("Verificando planta:", plant_data.get('name', ''), "Família:", plant_data.get('familia', ''))
                matches_all = True
                
                # Verificar cada característica
                for key, value in characteristics.items():
                    if not value:  # Pular campos vazios
                        continue
                        
                    # Garantir que o campo existe e não é None
                    plant_value = plant_data.get(key)
                    if plant_value is None:
                        print(f"Campo {key} não encontrado na planta")
                        matches_all = False
                        break
                        
                    # Converter para minúsculas para comparação case-insensitive
                    plant_value = str(plant_value).lower().strip()
                    search_value = str(value).lower().strip()
                    
                    print(f"Comparando {key}: '{search_value}' com '{plant_value}'")
                    
                    # Para descrição, verificar se contém as palavras-chave
                    if key == 'descricao':
                        keywords = search_value.split()
                        if not any(keyword in plant_value for keyword in keywords):
                            print("Palavras-chave não encontradas na descrição")
                            matches_all = False
                            break
                    # Para outros campos, verificar se contém o valor (busca parcial)
                    elif search_value not in plant_value and plant_value not in search_value:
                        print(f"Valor não encontrado em {key}")
                        matches_all = False
                        break
                
                if matches_all:
                    print("Planta corresponde aos critérios!")
                    matched_plants.append(plant_data)
            
            print(f"Total de plantas encontradas: {len(matched_plants)}")
            return jsonify({
                "plants": matched_plants,
                "message": f"Encontradas {len(matched_plants)} plantas"
            })
            
        except Exception as e:
            print("Erro ao buscar plantas no Firebase:", str(e))
            return jsonify({
                "plants": [],
                "message": "Erro ao buscar plantas no banco de dados",
                "error": str(e)
            }), 500
            
    except Exception as e:
        print("Erro na rota de busca:", str(e))
        return jsonify({
            "plants": [],
            "message": "Erro ao processar a busca",
            "error": str(e)
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
#ssl_context=('cert.pem', 'key.pem')