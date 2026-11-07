import argparse
import os
import subprocess
import time
import re
import sys

def main():
    parser = argparse.ArgumentParser(description="Kronos Colab Server Launcher")
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("KRONOS_MODEL_SIZE", "base"),
        choices=["mini", "small", "base", "large"],
        help="Kronos model size (mini, small, base, large). Default: base"
    )
    args = parser.parse_args()
    model_size = args.model.lower()

    print("1. Terminating existing Uvicorn and Cloudflare processes...")
    subprocess.run(["pkill", "-f", "uvicorn"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-f", "cloudflared"], stderr=subprocess.DEVNULL)
    time.sleep(1)

    print(f"2. Launching FastAPI server with Uvicorn (Model: {model_size.upper()}, Port 8000)...")
    env = os.environ.copy()
    env["KRONOS_MODEL_SIZE"] = model_size

    subprocess.Popen(
        ["uvicorn", "server:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env
    )
    time.sleep(8)  # 모델 로드 대기

    print("3. Establishing Cloudflare Quick Tunnel...")
    tunnel_proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://127.0.0.1:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    public_url = None
    start_time = time.time()
    while time.time() - start_time < 30:
        line = tunnel_proc.stdout.readline()
        match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
        if match:
            public_url = match.group(0)
            break
        time.sleep(0.2)

    if public_url:
        print("\n" + "=" * 65)
        print(f"🚀 Kronos Colab Server is live! (Model: {model_size.upper()})")
        print(f"📡 API Endpoint : {public_url}")
        print(f"📖 Swagger Docs : {public_url}/docs")
        print(f"🩺 Health Check : {public_url}/health")
        print("=" * 65 + "\n")
    else:
        print("❌ Failed to obtain Cloudflare Tunnel URL. Check logs.")
        sys.exit(1)

    try:
        tunnel_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        tunnel_proc.terminate()

if __name__ == "__main__":
    main()
