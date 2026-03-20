from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import subprocess
import socket
import os
import re

app = FastAPI()

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
async def dashboard():
    hostname = socket.gethostname()
    
    # Проверка служб
    mtproxy = check_service("mtproxy")
    hysteria = check_service("hysteria-server")
    
    cpu_load = get_cpu_load()
    ram_data = get_ram_usage()
    
    all_ok = mtproxy["status"] == "active" and hysteria["status"] == "active"
    global_color = "#00ff88" if all_ok else "#ffaa00"
    global_msg = "Все системы в норме 🟢" if all_ok else "Внимание: Проблемы со службами 🔴"

    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Server Status</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 20px; display: flex; justify-content: center; }}
            .container {{ width: 100%; max-width: 500px; }}
            h1 {{ text-align: center; color: {global_color}; font-size: 1.5rem; margin-bottom: 5px; }}
            .subtitle {{ text-align: center; color: #888; font-size: 0.9rem; margin-bottom: 30px; }}
            .card {{ background: #1e1e1e; border-radius: 12px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border-left: 6px solid #555; }}
            .card.ok {{ border-left-color: #00ff88; }}
            .card.err {{ border-left-color: #ff4444; }}
            .row {{ display: flex; justify-content: space-between; align-items: center; }}
            .label {{ font-size: 1.1rem; font-weight: 500; }}
            .badge {{ padding: 6px 12px; border-radius: 20px; font-weight: bold; color: #000; font-size: 0.9rem; min-width: 80px; text-align: center; }}
            .cpu-section {{ text-align: center; }}
            .cpu-value {{ font-size: 2.5rem; font-weight: bold; color: #fff; margin: 10px 0; }}
            .progress-bg {{ background: #333; height: 10px; border-radius: 5px; overflow: hidden; }}
            .progress-fill {{ height: 100%; transition: width 0.5s ease; }}
            /* Градиент для CPU */
            .cpu-fill {{ background: linear-gradient(90deg, #00c6ff, #0072ff); }}
            /* Градиент для RAM */
            .ram-fill {{ background: linear-gradient(90deg, #f12711, #f5af19); }}
            
            small {{ display: block; text-align: center; color: #555; margin-top: 30px; font-size: 0.8rem; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{global_msg}</h1>
            <div class="subtitle">{hostname} • {socket.gethostbyname(socket.gethostname())}</div>

            <!-- MTProto Status -->
            <div class="card {'ok' if mtproxy['status'] == 'active' else 'err'}">
                <div class="row">
                    <span class="label">📦 MTProto Proxy</span>
                    <span class="badge" style="background:{mtproxy['color']}">{mtproxy['icon']} {mtproxy['status'].upper()}</span>
                </div>
            </div>

            <!-- Hysteria Status -->
            <div class="card {'ok' if hysteria['status'] == 'active' else 'err'}">
                <div class="row">
                    <span class="label">⚡ Hysteria 2</span>
                    <span class="badge" style="background:{hysteria['color']}">{hysteria['icon']} {hysteria['status'].upper()}</span>
                </div>
            </div>

            <!-- CPU Load -->
            <div class="card cpu-section">
                <div class="label">🖥️ Нагрузка CPU</div>
                <div class="cpu-value">{cpu_load}%</div>
                <div class="progress-bg">
                    <div class="progress-fill cpu-fill" style="width: {cpu_load}%"></div>
                </div>
                <div style="font-size: 0.8rem; color: #666; margin-top: 8px;">Средняя за 1 мин</div>
            </div>

            <!-- RAM Usage (НОВОЕ) -->
            <div class="card cpu-section">
                <div class="label">💾 Оперативная память (RAM)</div>
                <div class="cpu-value">{ram_data['percent']}%</div>
                <div style="font-size: 0.9rem; color: #ccc; margin-bottom: 5px;">
                    {ram_data['used_gb']} ГБ / {ram_data['total_gb']} ГБ
                </div>
                <div class="progress-bg">
                    <div class="progress-fill ram-fill" style="width: {ram_data['percent']}%"></div>
                </div>
            </div>

            <small>Автообновление через <span id="timer">5</span> сек</small>
        </div>

        <script>
            let seconds = 5;
            const timerElem = document.getElementById('timer');
            setInterval(() => {{
                seconds--;
                timerElem.innerText = seconds;
                if (seconds <= 0) {{
                    window.location.reload();
                }}
            }}, 1000);
        </script>
    </body>
    </html>
    """
    return html