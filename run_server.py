import subprocess
import time
import re
import sys

def main():
    print("1. Terminating existing Uvicorn and Cloudflare processes...")
    subprocess.run(["pkill", "-f", "uvicorn"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-f", "cloudflared"], stderr=subprocess.DEVNULL)
    time.sleep(1)

    print("2. Launching FastAPI server with Uvicorn (Port 8000)...")
    subprocess.Popen(
        ["uvicorn", "server:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
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
        print("🚀 Kronos Colab Server is live!")
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
