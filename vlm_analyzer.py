import os
import sys
import base64
import requests
import sqlite3

# ================= USER SETTINGS =================
if len(sys.argv) < 2:
    print("Usage: python script_name.py <target_profile>")
    sys.exit(1)

TARGET_PROFILE = sys.argv[1]
API_URL = "http://localhost:1234/v1/chat/completions" 
MODEL_NAME = "qwen3-vl-4b"
# =================================================

def init_vlm_table(db_path: str):
    """Creates a table to store our AI intelligence reports."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vlm_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT,
            class_type TEXT,
            analysis_text TEXT
        )
    """)
    conn.commit()
    conn.close()

def encode_image(image_path: str) -> str:
    """Encodes an image to Base64 to send to LM Studio."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_image(image_path: str, prompt: str) -> str:
    """Sends the image and prompt to the local Qwen-VL model."""
    base64_image = encode_image(image_path)
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        "temperature": 0.1, # Kept very low to reduce AI hallucinations
        "max_tokens": 300
    }
    
    try:
        response = requests.post(API_URL, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status() 
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error: {e}"

def main():
    base_dir = TARGET_PROFILE
    # Ensure the base directory exists for the database
    os.makedirs(base_dir, exist_ok=True)
    db_path = os.path.join(base_dir, f"{TARGET_PROFILE}_data.db")

    init_vlm_table(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    osint_prompt = (
        "Act as an expert OSINT analyst and image forensics investigator. "
        "Examine this image methodically and extract all actionable intelligence. "
        "Structure your report using the exact categories below:\n\n"
        
        "1. ENVIRONMENT & SETTING: Is it strictly indoors, outdoors, or a transitional space? "
        "Describe the lighting (natural vs artificial), architecture, ground surface (e.g., concrete, asphalt, dirt), "
        "and any geographical clues like road markings, flora, or building styles.\n\n"
        
        "2. VEHICLE INTELLIGENCE: Identify the exact vehicle make, model, body type, and approximate generation. "
        "Note any distinct features, colors, modifications, or damage. Extract any visible license plate text, "
        "stickers, or badges, and state the likely regional format if recognizable.\n\n"
        
        "3. HUMAN ACTIVITY: Describe the people present. Note their specific actions, posture, clothing styles, "
        "uniforms, and any identifiable brands or accessories.\n\n"
        
        "4. TEXT & HIDDEN CLUES: Identify any background signage, storefront names, or readable text. "
        "Analyze reflections in car windows, paint, or mirrors for off-camera context.\n\n"
        
        "CRITICAL RULE: Do not guess or hallucinate data. If a detail is blurry, obscured, or not present, "
        "you must explicitly state 'Not visible' or 'Unknown'."
    )

    print(f"[*] Starting batch OSINT analysis using LM Studio ({MODEL_NAME})...")
    
    processed_count = 0

    # Walk through the current directory (".") to catch all weirdly named folders
    for root, _, files in os.walk("."):
        # Only process folders that belong to our target profile
        if TARGET_PROFILE not in root:
            continue
            
        # Skip the Crops folder (we already did those) and YOLO processed videos
        if "Crops" in root or "YOLO_Processed" in root:
            continue
            
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                full_path = os.path.join(root, file)
                class_type = "Full_Photo" 
                
                print(f"  -> Analyzing {file}...")
                analysis_result = analyze_image(full_path, osint_prompt)
                
                # Save to database
                cursor.execute("""
                    INSERT INTO vlm_analysis (source_file, class_type, analysis_text)
                    VALUES (?, ?, ?)
                """, (file, class_type, analysis_result))
                
                processed_count += 1

    conn.commit()
    conn.close()
    
    print(f"\n[*] Complete! Generated and saved {processed_count} intelligence reports to '{db_path}'.")


if __name__ == "__main__":
    main()