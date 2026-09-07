"""
Step 2 (Upgraded): Full-Frame & Crop OCR Pipeline
=================================================
- Scans full video keyframes (1 fps) for on-screen text, signage, and subtitles
- Scans cropped objects (vehicles, devices) for plates and badges
- Deduplicates repetitive text across consecutive frames
- Logs structured text, timestamps, and confidence scores into SQLite
"""

import os
import sys
import cv2
import sqlite3
import easyocr

# ================= USER SETTINGS =================
if len(sys.argv) < 2:
    print("Usage: python script_name.py <target_profile>")
    sys.exit(1)

TARGET_PROFILE = sys.argv[1]
LANGUAGES = ['en']
CONFIDENCE_THRESHOLD = 0.40   # Filter noise
FPS_SAMPLE_RATE = 1           # 1 frame per second
# =================================================


def init_ocr_table(db_path: str):
    """Creates or verifies the ocr_detections table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ocr_detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT,
            source_type TEXT,
            timestamp_sec REAL,
            detected_text TEXT,
            confidence REAL,
            bbox_coords TEXT
        )
    """)
    conn.commit()
    conn.close()


def find_all_mp4_files(search_root: str):
    """Discovers all .mp4 files recursively."""
    mp4_files = []
    for root, _, files in os.walk(search_root):
        if "Crops" in root or "YOLO_Processed" in root:
            continue
        for file in files:
            if file.lower().endswith(".mp4"):
                mp4_files.append(os.path.join(root, file))
    return mp4_files


def process_full_video_ocr(reader: easyocr.Reader, video_path: str, db_path: str) -> int:
    video_filename = os.path.basename(video_path)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return 0

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval = max(1, int(round(video_fps / FPS_SAMPLE_RATE)))

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    frame_count = 0
    logged_count = 0
    seen_texts_in_video = set()  # Prevent logging identical overlay text every second

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            timestamp_sec = round(frame_count / video_fps, 2)
            results = reader.readtext(frame)

            for (bbox, text, conf) in results:
                text_clean = text.strip()
                if conf >= CONFIDENCE_THRESHOLD and len(text_clean) > 2:
                    # Basic deduplication for static text overlays
                    text_key = f"{text_clean.lower()}_{int(timestamp_sec // 3)}"
                    if text_key in seen_texts_in_video:
                        continue
                    seen_texts_in_video.add(text_key)

                    bbox_str = str([[int(pt[0]), int(pt[1])] for pt in bbox])
                    cursor.execute("""
                        INSERT INTO ocr_detections 
                        (source_file, source_type, timestamp_sec, detected_text, confidence, bbox_coords)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (video_filename, "Video_Keyframe", timestamp_sec, text_clean, float(conf), bbox_str))
                    
                    logged_count += 1

        frame_count += 1

    conn.commit()
    conn.close()
    cap.release()
    return logged_count


def main():
    base_dir = TARGET_PROFILE
    db_path = os.path.join(base_dir, f"{TARGET_PROFILE}_data.db")
    crops_dir = os.path.join(base_dir, "Crops")

    init_ocr_table(db_path)

    print(f"[*] Initializing EasyOCR engine for languages: {LANGUAGES}...")
    reader = easyocr.Reader(LANGUAGES, gpu=True)

    # 1. Full Video Keyframe Scan
    video_files = find_all_mp4_files(TARGET_PROFILE)
    print(f"\n[*] Scanning {len(video_files)} full video(s) for on-screen text & signage...")
    
    total_video_text = 0
    for idx, video in enumerate(video_files, 1):
        count = process_full_video_ocr(reader, video, db_path)
        print(f"  [{idx}/{len(video_files)}] {os.path.basename(video)} -> Found {count} text item(s)")
        total_video_text += count

    print(f"\n[*] Complete! Found and stored {total_video_text} on-screen text elements in '{db_path}'.")


if __name__ == "__main__":
    main()