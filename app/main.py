from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import subprocess
import socket
import os
import psutil

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), -1

def check_service(service_name):
    # Теперь systemctl будет работать напрямую, так как мы вне контейнера
    cmd = f"systemctl is-active {service_name}"
    output, code = run_command(cmd)
    status = "active" if output == "active" else "inactive"
    color = "#00c853" if status == "active" else "#ff1744"  # Ярко-зелёный и ярко-красный
    icon = "🟢" if status == "active" else "🔴"
    return {"name": service_name, "status": status, "color": color, "icon": icon}

def get_docker_containers():
    output, code = run_command("docker ps --format '{{.Names}}\t{{.Status}}\t{{.Image}}'")
    if code != 0:
        return []
    lines = output.splitlines()
    containers = []
    for line in lines:
        parts = line.split('\t')
        if len(parts) == 3:
            name, status, image = parts
            containers.append({"name": name, "state": status, "image": image})
    return containers

def get_system_resources():
    # CPU
    cpu_percent = psutil.getloadavg()[0] / os.cpu_count() * 100
    # RAM
    memory = psutil.virtual_memory()
    ram_percent = memory.percent
    ram_used_gb = round(memory.used / 1024**3, 2)
    ram_total_gb = round(memory.total / 1024**3, 2)
    return {
        "cpu_load": round(cpu_percent, 1),
        "ram": {
            "percent": round(ram_percent, 1),
            "used_gb": ram_used_gb,
            "total_gb": ram_total_gb
        }
    }

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    hostname = socket.gethostname()
    try:
        ip_address = socket.gethostbyname(hostname)
    except:
        ip_address = "Unknown"

    hysteria = check_service("hysteria-server")
    mtproxy = check_service("mtproxy")
    containers = get_docker_containers()
    resources = get_system_resources()

    all_ok = (
            hysteria["status"] == "active" and
            mtproxy["status"] == "active" and
            len(containers) > 0
    )
    global_color = "#00c853" if all_ok else "#ffab00"  # Ярко-зелёный и ярко-ор
    global_msg = "Все системы в норме 🟢" if all_ok else "Внимание: Проблемы 🔴"

    return templates.TemplateResponse("index.html", {
        "request": request,
        "global_msg": global_msg,
        "global_color": global_color,
        "hostname": hostname,
        "ip_address": ip_address,
        "hysteria": hysteria,
        "mtproxy": mtproxy,
        "containers": containers,
        "cpu_load": resources["cpu_load"],
        "ram": resources["ram"],
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)