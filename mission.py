# mission.py

from flask import Flask, render_template, Response, jsonify, request
import atexit
from drone import Tello

app = Flask(__name__)
tello = Tello()

atexit.register(tello.cleanup)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video')
def video_feed():
    return Response(tello.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/command/<action>')
def handle_command(action):
    global tello

    if action == 'takeoff':
        if tello.current_mode != "Manual":
            return jsonify({"error": "Le drone n'est pas en mode manuel"}), 400
        tello.current_mode = "Auto - Take Off"
        return jsonify({"message": "Drone en décollage"})

    elif action == 'land':
        if tello.current_mode != "Auto - Take Off":
            return jsonify({"error": "Le drone n'est pas en vol"}), 400
        tello.current_mode = "Auto - Landing"
        return jsonify({"message": "Drone en atterrissage"})

    elif action == 'start_tracking':
        tello.tracking_enabled = True
        tello.current_mode = "Tracking Enabled"
        return jsonify({"message": "Tracking started"})

    elif action == 'stop_tracking':
        tello.tracking_enabled = False
        tello.current_mode = "Tracking Disabled"
        return jsonify({"message": "Tracking stopped"})

    elif action == 'change_color':
        colors = list(tello.COLOR_PALETTE.keys())
        tello.current_color = colors[(colors.index(tello.current_color) + 1) % len(colors)]
        tello.color_lower, tello.color_upper = tello.COLOR_PALETTE[tello.current_color]
        tello.current_mode = f"Tracking {tello.current_color}"
        return jsonify({"message": f"Color changed to: {tello.current_color}"})

    return jsonify({"error": "Commande inconnue"}), 400

@app.route('/set_color/<color>')
def set_color(color):
    global tello

    if color in tello.COLOR_PALETTE:
        tello.current_color = color
        tello.color_lower, tello.color_upper = tello.COLOR_PALETTE[color]
        return jsonify({"message": f"Color set to: {color}"})
    else:
        return jsonify({"error": "Couleur invalide"}), 400

@app.route('/get_status')
def get_status():
    global tello
    return jsonify({"mode": tello.current_mode})

@app.route('/get_velocities')
def get_velocities():
    global tello
    return jsonify(tello.velocities)

if __name__ == '__main__':
    app.run(debug=True)
