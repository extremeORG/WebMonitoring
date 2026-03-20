from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import subprocess
import socket
import os

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
        # Вычисляем процент нагрузки относительно количества ядер
        percent = min(100, (load_avg / cpu_count) * 100)
        return round(percent, 1)
    except Exception:
        return 0.0

async def dashboard():
    hostname = socket.gethostname()
    
    # !!! ВАЖНО: Проверьте точные имена служб командой:
    # systemctl list-units --type=service | grep -E "hysteria|mtproto"
    # Если имена другие (например, 'hysteria' вместо 'hysteria-server'), замените их ниже.
    mtproxy = check_service("mtproxy")
    hysteria = check_service("hysteria-server")
    
    cpu_load = get_cpu_load()
    
    # Определяем общий статус для заголовка
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
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Hel>
            .container {{ width: 100%; max-width: 500px; }}
            h1 {{ text-align: center; color: {global_color}; font-size: 1.5rem; margin-bott>
            .subtitle {{ text-align: center; color: #888; font-size: 0.9rem; margin-bottom:>

            .card {{ background: #1e1e1e; border-radius: 12px; padding: 20px; margin-bottom>
            .card.ok {{ border-left-color: #00ff88; }}
            .card.err {{ border-left-color: #ff4444; }}

            .row {{ display: flex; justify-content: space-between; align-items: center; }}
            .label {{ font-size: 1.1rem; font-weight: 500; }}
            .badge {{ padding: 6px 12px; border-radius: 20px; font-weight: bold; color: #00>

            .cpu-section {{ text-align: center; }}
            .cpu-value {{ font-size: 2.5rem; font-weight: bold; color: #fff; margin: 10px 0>
            .progress-bg {{ background: #333; height: 10px; border-radius: 5px; overflow: h>
            .progress-fill {{ height: 100%; background: linear-gradient(90deg, #00c6ff, #00>

            small {{ display: block; text-align: center; color: #555; margin-top: 30px; fon>
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
                <div class="label">🖥 Нагрузка CPU</div>
                <div class="cpu-value">{cpu_load}%</div>
                <div class="progress-bg">
                    <div class="progress-fill" style="width: {cpu_load}%"></div>
                </div>
                <div style="font-size: 0.8rem; color: #666; margin-top: 8px;">Средняя за 1 мин</div>
            </div>

            <small>Автообновление через <span id="timer">5</span> сек</small>
        </div>

        <script>
            let seconds = 15;
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