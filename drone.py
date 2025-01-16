# drone.py

import cv2
import numpy as np
import datetime

# Palette de couleurs prédéfinies (HSV)
COLOR_PALETTE = {
    "blue": ((100, 150, 50), (140, 255, 255)),  # Bleu
    "red": ((0, 100, 100), (10, 255, 255)),    # Rouge
    "green": ((40, 100, 50), (80, 255, 255)),  # Vert
    "yellow": ((20, 100, 100), (40, 255, 255)),# Jaune
    "orange": ((10, 100, 100), (20, 255, 255)),# Orange
    "purple": ((130, 100, 50), (160, 255, 255))# Violet
}

class Tello:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Erreur : Impossible d'ouvrir la caméra")
            exit()
        self.tracking_enabled = False
        self.current_color = "blue"
        self.color_lower, self.color_upper = COLOR_PALETTE[self.current_color]
        self.velocities = {'for_back': 0, 'left_right': 0, 'up_down': 0, 'yaw': 0}
        self.current_mode = "Manual"
        self.video_writer = None
        self.min_contour_area = 500

    def cleanup(self):
        if self.cap.isOpened():
            self.cap.release()
        if self.video_writer:
            self.video_writer.release()

    def track_object(self, center_x, center_y, frame_width, frame_height):
        if center_x is None or center_y is None:
            self.velocities['left_right'] = 0
            self.velocities['up_down'] = 0
            return

        center_image_x = frame_width / 2
        center_image_y = frame_height / 2

        distance_x = center_x - center_image_x
        distance_y = center_y - center_image_y

        max_distance = max(frame_width, frame_height) / 2
        normalized_distance_x = distance_x / max_distance
        normalized_distance_y = distance_y / max_distance

        max_speed = 100
        self.velocities['left_right'] = int(-normalized_distance_x * max_speed)
        self.velocities['up_down'] = int(normalized_distance_y * max_speed)

        self.velocities['left_right'] = max(-max_speed, min(max_speed, self.velocities['left_right']))
        self.velocities['up_down'] = max(-max_speed, min(max_speed, self.velocities['up_down']))

        print(f"Vitesses actuelles : {self.velocities}")

    def generate_frames(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            frame_height, frame_width, _ = frame.shape

            if self.tracking_enabled:
                blurred = cv2.GaussianBlur(frame, (11, 11), 0)
                hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

                if self.current_color == "red":
                    lower1 = np.array(COLOR_PALETTE["red"][0])
                    upper1 = np.array(COLOR_PALETTE["red"][1])
                    lower2 = np.array((170, 100, 100))
                    upper2 = np.array((180, 255, 255))

                    mask1 = cv2.inRange(hsv, lower1, upper1)
                    mask2 = cv2.inRange(hsv, lower2, upper2)
                    mask = cv2.bitwise_or(mask1, mask2)
                else:
                    lower = np.array(COLOR_PALETTE[self.current_color][0])
                    upper = np.array(COLOR_PALETTE[self.current_color][1])
                    mask = cv2.inRange(hsv, lower, upper)

                contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                if contours:
                    largest = max(contours, key=cv2.contourArea)
                    if cv2.contourArea(largest) < self.min_contour_area:
                        self.track_object(None, None, frame_width, frame_height)
                    else:
                        x, y, w, h = cv2.boundingRect(largest)
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        center_x = x + w // 2
                        center_y = y + h // 2
                        cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)

                        self.track_object(center_x, center_y, frame_width, frame_height)
                else:
                    self.track_object(None, None, frame_width, frame_height)

            if self.video_writer:
                self.video_writer.write(frame)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

    def start_recording(self):
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.video_writer = cv2.VideoWriter(f"recording_{timestamp}.avi", fourcc, 20.0, (640, 480))

    def stop_recording(self):
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
