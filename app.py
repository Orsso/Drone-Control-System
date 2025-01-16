from flask import Flask, render_template, Response, jsonify, request
import cv2
import numpy as np
import threading
import datetime
import atexit

app = Flask(__name__)

# Palette de couleurs prédéfinies (HSV)
COLOR_PALETTE = {
    "blue": ((100, 150, 50), (140, 255, 255)),  # Bleu
    "red": ((0, 100, 100), (10, 255, 255)),    # Rouge
    "green": ((40, 100, 50), (80, 255, 255)),  # Vert
    "yellow": ((20, 100, 100), (40, 255, 255)),# Jaune
    "orange": ((10, 100, 100), (20, 255, 255)),# Orange
    "purple": ((130, 100, 50), (160, 255, 255))# Violet
}

# Initialisation de la caméra
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Erreur : Impossible d'ouvrir la caméra")
    exit()

# Variables globales
tracking_enabled = False
current_color = "blue"
color_lower, color_upper = COLOR_PALETTE[current_color]
velocities = {'for_back': 0, 'left_right': 0, 'up_down': 0, 'yaw': 0}
current_mode = "Manual"
video_writer = None

# Seuil minimal pour la taille des contours (en pixels)
min_contour_area = 500

# Fonction pour libérer les ressources
def cleanup():
    if cap.isOpened():
        cap.release()
    if video_writer:
        video_writer.release()

atexit.register(cleanup)

def track_object(center_x, center_y, frame_width, frame_height):
    global velocities

    # Si l'objet n'est pas détecté, le drone reste immobile
    if center_x is None or center_y is None:
        velocities['left_right'] = 0
        velocities['up_down'] = 0
        return

    # Centre de l'image
    center_image_x = frame_width / 2
    center_image_y = frame_height / 2

    # Calculer la distance entre l'objet et le centre de l'image
    distance_x = center_x - center_image_x
    distance_y = center_y - center_image_y

    # Normaliser la distance (pour une plage de 0 à 1)
    max_distance = max(frame_width, frame_height) / 2
    normalized_distance_x = distance_x / max_distance
    normalized_distance_y = distance_y / max_distance

    # Ajuster les vitesses en fonction de la distance
    max_speed = 100  # Vitesse maximale
    velocities['left_right'] = int(-normalized_distance_x * max_speed)  # Inverser pour le suivi
    velocities['up_down'] = int(normalized_distance_y * max_speed)  # Inverser pour le suivi

    # Limiter les vitesses pour éviter des valeurs trop élevées
    velocities['left_right'] = max(-max_speed, min(max_speed, velocities['left_right']))
    velocities['up_down'] = max(-max_speed, min(max_speed, velocities['up_down']))

    print(f"Vitesses actuelles : {velocities}")

def generate_frames():
    global tracking_enabled, color_lower, color_upper, video_writer, min_contour_area

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_height, frame_width, _ = frame.shape  # Obtenir les dimensions de l'image

        if tracking_enabled:
            # Détection de couleur
            blurred = cv2.GaussianBlur(frame, (11, 11), 0)
            hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

            if current_color == "red":
                # Traitement spécial pour le rouge (deux plages)
                lower1 = np.array(COLOR_PALETTE["red"][0])
                upper1 = np.array(COLOR_PALETTE["red"][1])
                lower2 = np.array((170, 100, 100))
                upper2 = np.array((180, 255, 255))

                mask1 = cv2.inRange(hsv, lower1, upper1)
                mask2 = cv2.inRange(hsv, lower2, upper2)
                mask = cv2.bitwise_or(mask1, mask2)
            else:
                lower = np.array(COLOR_PALETTE[current_color][0])
                upper = np.array(COLOR_PALETTE[current_color][1])
                mask = cv2.inRange(hsv, lower, upper)

            contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                largest = max(contours, key=cv2.contourArea)
                if cv2.contourArea(largest) < min_contour_area:
                    # Si le contour est trop petit, ignorer et immobiliser le drone
                    track_object(None, None, frame_width, frame_height)
                else:
                    # Suivre l'objet détecté
                    x, y, w, h = cv2.boundingRect(largest)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    center_x = x + w // 2
                    center_y = y + h // 2
                    cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)

                    # Suivi automatique avec ajustement de la vitesse
                    track_object(center_x, center_y, frame_width, frame_height)
            else:
                # Aucun objet détecté, le drone reste immobile
                track_object(None, None, frame_width, frame_height)

        if video_writer:
            video_writer.write(frame)

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

def start_recording():
    global video_writer
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    video_writer = cv2.VideoWriter(f"recording_{timestamp}.avi", fourcc, 20.0, (640, 480))

def stop_recording():
    global video_writer
    if video_writer:
        video_writer.release()
        video_writer = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/command/<action>')
def handle_command(action):
    global tracking_enabled, current_color, color_lower, color_upper, current_mode

    if action == 'takeoff':
        if current_mode != "Manual":
            return jsonify({"error": "Le drone n'est pas en mode manuel"}), 400
        current_mode = "Auto - Take Off"
        return jsonify({"message": "Drone en décollage"})

    elif action == 'land':
        if current_mode != "Auto - Take Off":
            return jsonify({"error": "Le drone n'est pas en vol"}), 400
        current_mode = "Auto - Landing"
        return jsonify({"message": "Drone en atterrissage"})

    elif action == 'start_tracking':
        tracking_enabled = True
        current_mode = "Tracking Enabled"
        return jsonify({"message": "Tracking started"})

    elif action == 'stop_tracking':
        tracking_enabled = False
        current_mode = "Tracking Disabled"
        return jsonify({"message": "Tracking stopped"})

    elif action == 'change_color':
        colors = list(COLOR_PALETTE.keys())
        current_color = colors[(colors.index(current_color) + 1) % len(colors)]
        color_lower, color_upper = COLOR_PALETTE[current_color]
        current_mode = f"Tracking {current_color}"
        return jsonify({"message": f"Color changed to: {current_color}"})

    return jsonify({"error": "Commande inconnue"}), 400

@app.route('/set_color/<color>')
def set_color(color):
    global current_color, color_lower, color_upper

    if color in COLOR_PALETTE:
        current_color = color
        color_lower, color_upper = COLOR_PALETTE[color]
        return jsonify({"message": f"Color set to: {color}"})
    else:
        return jsonify({"error": "Couleur invalide"}), 400

@app.route('/get_status')
def get_status():
    global current_mode
    return jsonify({"mode": current_mode})

@app.route('/get_velocities')
def get_velocities():
    global velocities
    return jsonify(velocities)

if __name__ == '__main__':
    app.run(debug=True)