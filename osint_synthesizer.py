import os
import sys
import sqlite3
from collections import Counter


# ================= USER SETTINGS =================
if len(sys.argv) < 2:
    print("Usage: python script_name.py <target_profile>")
    sys.exit(1)

TARGET_PROFILE = sys.argv[1]
# =================================================

def main():
    base_dir = TARGET_PROFILE
    db_path = os.path.join(base_dir, f"{TARGET_PROFILE}_data.db")
    
    if not os.path.exists(db_path):
        print(f"[!] Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"\n[{TARGET_PROFILE.upper()}] - AUTOMATED OSINT DOSSIER GENERATION")
    print("="*60)

    # 1. ENVIRONMENT ANALYSIS (Parsing VLM Text)
    cursor.execute("SELECT analysis_text FROM vlm_analysis")
    reports = [row[0].lower() for row in cursor.fetchall() if row[0]]
    
    indoors = sum(1 for r in reports if "indoors" in r or "indoor" in r)
    outdoors = sum(1 for r in reports if "outdoors" in r or "outdoor" in r)
    
    print("\n[1] ENVIRONMENT PROFILE:")
    print(f"  -> Indoor Scenes Detected: {indoors}")
    print(f"  -> Outdoor Scenes Detected: {outdoors}")
    if indoors > outdoors:
        print("  -> Conclusion: Content is predominantly filmed in controlled, indoor environments (e.g., studios, garages, gyms).")
    else:
        print("  -> Conclusion: Content is predominantly filmed outdoors.")

    # 2. VEHICLE INTELLIGENCE (Cross-referencing VLM and OCR)
    car_brands = ["suzuki", "hyundai", "honda", "mahindra", "tata", "toyota", "bmw", "mercedes", "audi", "kia"]
    brand_counts = Counter()
    
    for report in reports:
        for brand in car_brands:
            if brand in report:
                brand_counts[brand] += 1

    print("\n[2] VEHICLE INTELLIGENCE:")
    if brand_counts:
        for brand, count in brand_counts.most_common(3):
            print(f"  -> High probability vehicle match: {brand.capitalize()} (Mentioned {count} times)")
    else:
        print("  -> No distinct vehicle brands definitively identified in text.")

    # 3. YOLOV26 OBJECT FREQUENCY (What is actually on screen?)
    try:
        cursor.execute("SELECT class_name, COUNT(*) FROM video_detections GROUP BY class_name ORDER BY COUNT(*) DESC LIMIT 5")
        yolo_objects = cursor.fetchall()
        print("\n[3] MOST FREQUENT ON-SCREEN OBJECTS (YOLO):")
        for obj, count in yolo_objects:
            print(f"  -> {obj.capitalize()}: {count} detections")
    except sqlite3.OperationalError:
        print("\n[3] YOLO OBJECTS: Table not found or empty.")

    # 4. HIGH-CONFIDENCE OCR TEXT (Plates, signs, captions)
    try:
        # Filter for text longer than 4 chars to remove noise, high confidence
        cursor.execute("""
            SELECT detected_text, COUNT(*) FROM ocr_detections 
            WHERE length(detected_text) > 4 AND confidence > 0.5 
            GROUP BY detected_text ORDER BY COUNT(*) DESC LIMIT 10
        """)
        ocr_texts = cursor.fetchall()
        print("\n[4] REPEATED TEXT & SIGNAGE (EasyOCR):")
        for text, count in ocr_texts:
            print(f"  -> '{text}' (Seen {count} times)")
    except sqlite3.OperationalError:
        print("\n[4] OCR TEXT: Table not found or empty.")

    # 5. CONTENT CATEGORIZATION
    print("\n[5] CONTENT GENRE CONCLUSION:")
    dance_keywords = sum(1 for r in reports if "dancing" in r or "posing" in r or "choreography" in r)
    travel_keywords = sum(1 for r in reports if "travel" in r or "mountain" in r or "beach" in r)
    
    if dance_keywords > travel_keywords:
        print(f"  -> AI Assessment: Target primarily produces Lifestyle / Dance / Choreography content (Action keywords detected {dance_keywords} times).")
    else:
        print(f"  -> AI Assessment: Target primarily produces Travel / Vlogging content.")
        
    print("="*60)
    
    # Save to file
    dossier_path = os.path.join(base_dir, f"{TARGET_PROFILE}_Target_Dossier.txt")
    with open(dossier_path, "w", encoding="utf-8") as f:
        f.write(f"OSINT TARGET DOSSIER: {TARGET_PROFILE}\n")
        f.write(f"Total Intelligence Reports Processed: {len(reports)}\n")
        f.write(f"Indoor Environments: {indoors} | Outdoor Environments: {outdoors}\n")
        f.write("View terminal output for full breakdown.")
        
    print(f"\n[*] Summary dossier saved to {dossier_path}")

    conn.close()

if __name__ == "__main__":
    main()