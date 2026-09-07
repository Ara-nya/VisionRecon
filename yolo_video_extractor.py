"""
Step 1: YOLO Video Object Detector & Cropper for OSINT
=====================================================
- Automatically discovers all .mp4 files recursively
- Extracts 1 frame per second from downloaded videos
- Runs YOLO detection for OSINT-critical objects
- Crops and saves detected objects for downstream OCR / analysis
- Logs all detections into your SQLite database
"""

import os
import sys
import cv2
import sqlite3
from ultralytics import YOLO

# ================= USER SETTINGS =================
if len(sys.argv) < 2:
    print("Usage: python script_name.py <target_profile>")
    sys.exit(1)

TARGET_PROFILE = sys.argv[1]
MODEL_WEIGHTS = "yolo26m.pt"   # You can also use 'yolov8n.pt' or 'yolo11m.pt'
FPS_SAMPLE_RATE = 1            # 1 frame per second

# Target classes: 0: person, 2: car, 3: motorcycle, 5: bus, 7: truck, 9: traffic light, 11: stop sign, 67: cell phone
TARGET_CLASSES = [0, 2, 3, 5, 7, 9, 11, 67]
# =================================================


def init_db(db_path: str):
    """Adds video_detections table to SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS video_detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shortcode TEXT,
            timestamp_sec REAL,
            class_name TEXT,
            confidence REAL,
            bbox_coords TEXT,
            crop_path TEXT
        )
    """)
    conn.commit()
    conn.close()


def find_all_mp4_files(search_root: str):
    """Recursively finds all .mp4 files regardless of folder naming."""
    mp4_files = []
    for root, _, files in os.walk(search_root):
        # Skip the Crops or YOLO_Processed folders to avoid processing intermediate outputs
        if "Crops" in root or "YOLO_Processed" in root:
            continue
        for file in files:
            if file.lower().endswith(".mp4"):
                mp4_files.append(os.path.join(root, file))
    return mp4_files


def process_video(video_path: str, model: YOLO, db_path: str, base_output_dir: str):
    video_filename = os.path.basename(video_path)
    shortcode_identifier = os.path.splitext(video_filename)[0]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[!] Could not open video: {video_path}")
        return

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval = max(1, int(round(video_fps / FPS_SAMPLE_RATE)))

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    frame_count = 0
    saved_detections = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            timestamp_sec = round(frame_count / video_fps, 2)

            # Run YOLO inference
            results = model.predict(frame, classes=TARGET_CLASSES, verbose=False)[0]

            for box in results.boxes:
                cls_id = int(box.cls[0])
                class_name = model.names[cls_id]
                conf = float(box.conf[0])

                if conf < 0.40:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                h, w, _ = frame.shape
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)

                crop_path = "None"

                # Crop vehicles and electronics for OCR / OSINT inspection
                if class_name in ["car", "truck", "bus", "motorcycle", "cell phone"]:
                    crop = frame[y1:y2, x1:x2]
                    if crop.size > 0:
                        crop_folder = os.path.join(base_output_dir, "Crops", class_name)
                        os.makedirs(crop_folder, exist_ok=True)
                        crop_filename = f"{shortcode_identifier}_t{timestamp_sec}s_conf{int(conf*100)}.jpg"
                        crop_path = os.path.join(crop_folder, crop_filename)
                        cv2.imwrite(crop_path, crop)

                bbox_str = f"{x1},{y1},{x2},{y2}"
                cursor.execute("""
                    INSERT INTO video_detections 
                    (shortcode, timestamp_sec, class_name, confidence, bbox_coords, crop_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (shortcode_identifier, timestamp_sec, class_name, conf, bbox_str, crop_path))
                
                saved_detections += 1

        frame_count += 1

    conn.commit()
    conn.close()
    cap.release()
    print(f"[*] Processed {video_filename} -> Found & logged {saved_detections} key objects.")


def main():
    # Recursively find all MP4 files in the current workspace
    video_files = find_all_mp4_files(TARGET_PROFILE)

    if not video_files:
        print("[!] No .mp4 files found anywhere in the current directory.")
        return

    print(f"[*] Successfully discovered {len(video_files)} video(s).")
    
    # Save database to the primary profile directory
    base_dir = TARGET_PROFILE
    os.makedirs(base_dir, exist_ok=True)
    db_path = os.path.join(base_dir, f"{TARGET_PROFILE}_data.db")

    init_db(db_path)

    print(f"[*] Loading YOLO model: {MODEL_WEIGHTS}...")
    model = YOLO(MODEL_WEIGHTS)

    for idx, video_path in enumerate(video_files, 1):
        print(f"\n[{idx}/{len(video_files)}] Scanning: {os.path.basename(video_path)}")
        process_video(video_path, model, db_path, base_dir)

    print(f"\n[*] Complete! Detections saved in database '{db_path}' and object crops stored in '{base_dir}/Crops/'.")


if __name__ == "__main__":
    main()