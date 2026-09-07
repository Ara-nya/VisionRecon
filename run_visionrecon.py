import sys
import subprocess

def run_script(script_name, target):
    print(f"\n{'='*50}\n[*] EXECUTING: {script_name}\n{'='*50}")
    try:
        # Passes the target name as an argument to each script
        subprocess.run(["python", script_name, target], check=True)
    except subprocess.CalledProcessError:
        print(f"\n[!] FATAL ERROR: {script_name} failed. Halting pipeline.")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_visionrecon.py <target_instagram_username>")
        sys.exit(1)
        
    target_profile = sys.argv[1]
    
    print(f"[*] INITIALIZING VISIONRECON PIPELINE FOR: @{target_profile}")
    
    # 1. Download (Assuming you want 20 photos and 5 videos for a quick scan)
    # Note: instagram_downloader.py already uses argparse, so we pass flags
    try:
        subprocess.run(["python", "instagram_downloader.py", target_profile, "--photos", "20", "--videos", "5", "--sql"], check=True)
    except subprocess.CalledProcessError:
        print("\n[!] FATAL ERROR: Downloader failed (likely an Instagram block). Halting pipeline.")
        sys.exit(1)
    
    # 2. Run the Analysis Pipeline
    run_script("yolo_video_extractor.py", target_profile)
    run_script("run_ocr_extractor.py", target_profile)
    run_script("vlm_analyzer.py", target_profile)
    run_script("osint_synthesizer.py", target_profile)
    
    print(f"\n[*] PIPELINE COMPLETE. Check the {target_profile} folder for the Dossier.")

if __name__ == "__main__":
    main()