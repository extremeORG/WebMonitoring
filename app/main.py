from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import subprocess
import socket
import os
import re

app = FastAPI()

# Указываем папку с шаблонами
templates = Jinja2Templates(directory="templates")

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=5)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), -1

def check_service(service_name):
    """Проверяет статус службы через systemctl"""
    output, code = run_command(f"systemctl is-active {service_name}")
    status = "active" if output == "active" else "inactive"
    color = "#00ff88" if status == "active" else "#ff4444"
    icon = "✅" if status == "active" else "❌"
    return {
        "name": service_name,
        "status": status,
        "color": color,
        "icon": icon
    }

def get_cpu_load():
    """Получает среднюю нагрузку на CPU за 1 минуту"""
    try:
        load_avg = os.getloadavg()[0]
        cpu_count = os.cpu_count() or 1
        percent = min(100, (load_avg / cpu_count) * 100)
        return round(percent, 1)
    except Exception:
        return 0.0

def get_ram_usage():
    """Получает использование RAM из /proc/meminfo"""
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()

        mem_total = 0
        mem_available = 0

        for line in lines:
            if line.startswith('MemTotal:'):
                mem_total = int(line.split()[1]) # В kB
            elif line.startswith('MemAvailable:'):
                mem_available = int(line.split()[1]) # В kB

        mem_used = mem_total - mem_available
        percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0

        # Конвертируем в ГБ для красивого вывода
        used_gb = round((mem_used / 1024 / 1024), 2)
        total_gb = round((mem_total / 1024 / 1024), 2)

        return {
            "percent": round(percent, 1),
            "used_gb": used_gb,
            "total_gb": total_gb
        }
    except Exception:
        return {"percent": 0.0, "used_gb": 0, "total_gb": 0}

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    hostname = socket.gethostname()

    # Проверка служб
    mtproxy = check_service("mtproxy")
    hysteria = check_service("hysteria-server")

    cpu_load = get_cpu_load()
    ram_data = get_ram_usage()

    all_ok = mtproxy["status"] == "active" and hysteria["status"] == "active"
    global_color = "#00ff88" if all_ok else "#ffaa00"
    global_msg = "Все системы в норме 🟢" if all_ok else "Внимание: Проблемы со службами 🔴"

    # Получаем IP (может не всегда корректно, но для примера подойдет)
    try:
        ip_address = socket.gethostbyname(socket.gethostname())
    except:
        ip_address = "Unknown"

    # Рендерим шаблон с передачей данных
    return templates.TemplateResponse("index.html", {
        "request": request,
        "global_msg": global_msg,
        "global_color": global_color,
        "hostname": hostname,
        "ip_address": ip_address,
        "mtproxy": mtproxy,
        "hysteria": hysteria,
        "cpu_load": cpu_load,
        "ram_data": ram_data,
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)