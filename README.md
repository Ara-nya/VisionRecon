# VisionRecon 👁️‍🗨️
**Automated OSINT Image & Video Intelligence Pipeline**

VisionRecon is an advanced, fully offline Open-Source Intelligence (OSINT) pipeline that extracts, analyzes, and synthesizes data from public social media profiles. 

By combining object detection, optical character recognition (OCR), and local Vision-Language Models (VLMs), this tool autonomously analyzes media to generate structured intelligence dossiers detailing environmental context, vehicle identification, human activity, and hidden text.

## ⚠️ Ethical Use & Disclaimer
This tool was developed strictly for **educational purposes, personal digital footprint auditing, and authorized threat-intelligence research.** 

As cybersecurity professionals, we must respect privacy. Do not use this tool to stalk, harass, or perform unauthorized reconnaissance on private individuals. The developer assumes no liability for the misuse of this software.

## 🚀 Key Features

*   **Automated Media Ingestion:** Downloads target profile media while respecting rate limits.
*   **Object Detection (YOLO26):** Scans video keyframes to isolate critical OSINT targets (vehicles, electronics, people).
*   **Text Extraction (EasyOCR):** Extracts license plates, street signs, and on-screen captions from frames.
*   **Forensic Context Analysis:** Uses **Qwen3-VL (4B)** via LM Studio to perform deep environmental analysis on extracted media.
*   **Dossier Generation:** Synthesizes SQL database records into a final, human-readable intelligence report.
*   **100% Offline AI:** All computer vision and language model inferences are executed locally, ensuring total data privacy and zero API costs.

## 🛠️ Technology Stack

*   **Core Logic:** Python 3
*   **Computer Vision:** Ultralytics YOLO26, OpenCV
*   **OCR Engine:** EasyOCR, PyTorch (CUDA-enabled)
*   **Local LLM Integration:** LM Studio, Qwen3-VL-4B-Instruct (GGUF)
*   **Data Storage:** SQLite3

## 💻 Hardware Requirements

To run the local VLM pipeline smoothly, the following hardware is recommended:
*   **GPU:** NVIDIA GPU with at least 6GB VRAM (e.g., RTX 4050 or higher).
*   **RAM:** 16GB DDR5 recommended.
*   **Storage:** ~5GB of free space for YOLO weights, EasyOCR models, and the Qwen3 GGUF file.

## ⚙️ Installation

1. **Clone the Repository:**
   ```bash
   git clone [https://github.com/Ara-nys/VisionRecon.git](https://github.com/Ara-nya/VisionRecon.git)
   cd VisionRecon


Install Dependencies:
Ensure you have CUDA installed for your GPU, then run:

Bash
pip install instaloader ultralytics opencv-python easyocr requests
pip install torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/cu118](https://download.pytorch.org/whl/cu118)
Setup LM Studio:

Download and install LM Studio.

Search for and download the Qwen3 VL 4B Instruct Q4_K_M GGUF model.

Start the Local Server in LM Studio on port 1234 with GPU Offload set to Max.

🕵️‍♂️ Usage
You can run the entire pipeline autonomously using the master wrapper script:

Bash
python run_visionrecon.py <target_instagram_username>
Manual Execution
If you prefer to run the modules step-by-step for debugging:

Download Media: python instagram_downloader.py <target> --sql

Extract Keyframes (YOLO): python yolo_video_extractor.py <target>

Extract Text (OCR): python run_ocr_extractor.py <target>

Run VLM Analysis: python vlm_analyzer.py <target>

Synthesize Dossier: python osint_synthesizer.py <target>