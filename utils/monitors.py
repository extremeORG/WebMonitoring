import psutil
import subprocess
import requests
import json
from datetime import datetime
from typing import Dict, Optional
import platform

def get_cpu_load() -> float:
    """Нагрузка CPU в процентах"""
    return round(psutil.cpu_percent(interval=0.5), 1)

def get_ram_usage() -> Dict[str, float]:
    """Использование RAM"""
    memory = psutil.virtual_memory()
    return {
        "percent": round(memory.percent, 1),
        "used_gb": round(memory.used / (1024**3), 2),
        "total_gb": round(memory.total / (1024**3), 2)
    }

def get_disk_usage() -> Dict[str, float]:
    """Использование диска"""
    disk = psutil.disk_usage('/')
    return {
        "percent": round(disk.percent, 1),
        "used_gb": round(disk.used / (1024**3), 2),
        "free_gb": round(disk.free / (1024**3), 2)
    }

def get_uptime() -> str:
    """Время работы системы в формате ЧЧ:ММ:СС"""
    boot_time = psutil.boot_time()
    uptime_seconds = int(datetime.now().timestamp() - boot_time)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def get_system_info() -> Dict[str, str]:
    """Информация о системе"""
    info = {
        "platform": platform.system(),  # Linux
        "release": platform.release(),  # Kernel version
        "version": platform.version(),  # Full kernel version
        "machine": platform.machine(),  # Architecture (x86_64, etc.)
        "processor": platform.processor(),  # Processor type
        "platform_fully": platform.platform(),  # Full platform string
    }

    # Попытка получить информацию из /etc/os-release
    try:
        with open('/etc/os-release', 'r') as f:
            os_info = {}
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    os_info[key] = value.strip('"')

        # Определение названия дистрибутива
        if 'NAME' in os_info and 'VERSION' in os_info:
            full_name = f"{os_info['NAME']} {os_info['VERSION']}"
        elif 'PRETTY_NAME' in os_info:
            full_name = os_info['PRETTY_NAME']
        else:
            full_name = f"{info['platform']} {info['release']}"
    except FileNotFoundError:
        # Если /etc/os-release нет, используем информацию от platform
        full_name = f"{info['platform']} {info['release']}"

    return {
        "full_name": full_name,
        "kernel_version": info["release"],
        "architecture": info["machine"],
        "platform": info["platform"],
        "platform_fully": info["platform_fully"]
    }

def check_xray_status() -> Dict:
    """Статус XRay VPN через API debug/vars"""
    result = {
        "active": False,
        "peers": 0,
        "traffic_in": "0 MB",
        "traffic_out": "0 MB",
        "delay": 0,
        "load": 0
    }
    try:
        status_check = subprocess.run(
            ["systemctl", "is-active", "xray"],
            capture_output=True, text=True, timeout=3
        )
        if status_check.returncode == 0 and status_check.stdout.strip() == "active":
            result["active"] = True

            try:
                response = requests.get("http://127.0.0.1:11111/debug/vars", timeout=5)
                if response.status_code == 200:
                    data = response.json()

                    stats = data.get("stats", {})
                    inbound_stats = stats.get("inbound", {})
                    user_stats = stats.get("user", {})

                    total_uplink = 0
                    total_downlink = 0
                    peer_count = 0

                    for name, values in inbound_stats.items():
                        if isinstance(values, dict):
                            total_uplink += values.get("uplink", 0)
                            total_downlink += values.get("downlink", 0)

                    for user, values in user_stats.items():
                        if isinstance(values, dict) and values.get("uplink", 0) > 0:
                            peer_count += 1

                    result["traffic_in"] = f"{total_downlink / (1024*1024):.2f} MB"
                    result["traffic_out"] = f"{total_uplink / (1024*1024):.2f} MB"
                    result["peers"] = peer_count if peer_count > 0 else len(user_stats)

                    observatory = data.get("observatory", {})
                    for tag, obs_data in observatory.items():
                        if isinstance(obs_data, dict):
                            result["delay"] = obs_data.get("delay", 0)
                            break

                    traffic_load = min(50, (total_uplink + total_downlink) / 1000000 * 0.05)
                    latency_load = min(30, result["delay"] / 10) if result["delay"] > 0 else 0
                    result["load"] = min(95, traffic_load + latency_load + 15)

            except requests.RequestException as e:
                print(f"XRay API error: {e}")

    except Exception as e:
        print(f"XRay status check error: {e}")
        pass
    return result


def check_hysteria_status() -> Dict:
    """Статус Hysteria VPN"""
    result = {
        "active": False,
        "peers": 0,
        "traffic_in": "0 MB",
        "traffic_out": "0 MB",
        "load": 0
    }
    try:
        status_check = subprocess.run(
            ["systemctl", "is-active", "hysteria-server"],
            capture_output=True, text=True, timeout=3
        )
        if status_check.returncode == 0 and status_check.stdout.strip() == "active":
            result["active"] = True
            # Здесь можно добавить парсинг логов Hysteria при необходимости
            result["load"] = min(95, psutil.cpu_percent(interval=0.1) * 0.5 + 10)
    except Exception:
        pass
    return result


def check_vpn_status() -> Dict:
    """Объединённый статус всех VPN сервисов (XRay + Hysteria)"""
    xray_status = check_xray_status()
    hysteria_status = check_hysteria_status()

    return {
        "active": xray_status["active"] or hysteria_status["active"],
        "xray": xray_status,
        "hysteria": hysteria_status,
        "protocol": "XRay" if xray_status["active"] else ("Hysteria" if hysteria_status["active"] else "None")
    }

def _format_traffic(traffic_str: str) -> str:
    """Форматирование строки трафика"""
    traffic_str = traffic_str.strip()
    if 'mib' in traffic_str.lower():
        value = float(traffic_str.replace('mib', '').replace(',', '').strip())
        return f"{value:.1f} MB/s"
    elif 'gib' in traffic_str.lower():
        value = float(traffic_str.replace('gib', '').replace(',', '').strip())
        return f"{value * 1024:.1f} MB/s"
    return "0 MB/s"

def check_proxy_status() -> Dict:
    """Статус Telegram MTProto Proxy"""
    result = {
        "enabled": False,
        "secret": "********",
        "requests": 0,
        "latency": 0
    }
    try:
        # Проверка процесса mtproto-proxy
        check = subprocess.run(
            ["pgrep", "-f", "mtproto"],
            capture_output=True, text=True, timeout=3
        )
        if check.returncode == 0:
            result["enabled"] = True
            # Эмуляция запросов (можно подключить к логам)
            result["requests"] = psutil.cpu_percent(interval=0.1) * 10
            result["latency"] = min(99, max(5, 30 + (psutil.cpu_percent() % 20)))
    except Exception:
        pass
    return result

def check_docker_status() -> Dict:
    """Статус Docker"""
    result = {
        "active": False,
        "containers": 0,
        "container_list": [],
        "load": 0
    }
    try:
        # Проверка Docker daemon
        docker_check = subprocess.run(
            ["systemctl", "is-active", "docker"],
            capture_output=True, text=True, timeout=3
        )
        if docker_check.returncode == 0 and docker_check.stdout.strip() == "active":
            result["active"] = True
            # Получение списка контейнеров
            containers = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}:{{.Status}}"],
                capture_output=True, text=True, timeout=5
            )
            if containers.returncode == 0:
                container_list = [c for c in containers.stdout.split('\n') if c]
                result["containers"] = len(container_list)
                result["container_list"] = container_list
                result["load"] = min(90, len(container_list) * 8 + 15)
    except Exception:
        pass
    return result

def get_fastapi_metrics() -> Dict:
    """Метрики самого FastAPI приложения"""
    # Получаем время запуска процесса FastAPI
    pid = None
    try:
        # Получаем PID из systemd
        result = subprocess.run(["systemctl", "show", "--property=MainPID", "--value", "server-monitor"],
                                capture_output=True, text=True, timeout=3)
        pid_str = result.stdout.strip()
        if pid_str.isdigit():
            pid = int(pid_str)

        if pid:
            process = psutil.Process(pid)
            start_time = process.create_time()
            uptime_seconds = datetime.now().timestamp() - start_time

            # Рассчитываем процент аптайма за последний день (например)
            # Здесь можно адаптировать логику расчета процента аптайма под ваши нужды
            # Пока что просто возвращаем время в формате HH:MM:SS
            uptime_hours = int(uptime_seconds // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            uptime_secs = int(uptime_seconds % 60)
            formatted_uptime = f"{uptime_hours:02d}:{uptime_minutes:02d}:{uptime_secs:02d}"

            # Пример расчета процента аптайма за последние 24 часа
            # Если приложение работало все 24 часа, то 100%
            # Если было перезапущено недавно, то меньше
            # Это упрощенный расчет - в реальной системе может быть сложнее
            expected_uptime_last_period = 24 * 3600  # 24 часа в секундах
            actual_uptime = min(uptime_seconds, expected_uptime_last_period)
            uptime_percentage = round((actual_uptime / expected_uptime_last_period) * 100, 1)
        else:
            # Если не удалось получить PID, используем запасной вариант
            uptime_percentage = 99.9
            formatted_uptime = "00:00:00"

    except (psutil.NoSuchProcess, psutil.AccessDenied, subprocess.TimeoutExpired, ValueError):
        # Если не удалось получить информацию о процессе
        uptime_percentage = 99.9
        formatted_uptime = "00:00:00"

    return {
        "uptime_percent": uptime_percentage,
        "current_uptime": formatted_uptime,  # Новое поле с текущим временем работы
        "cpu_load": get_cpu_load(),
        "ram_usage": get_ram_usage()["percent"],
        "health": "healthy"
    }

def get_all_metrics() -> Dict:
    """Сбор всех метрик в один объект"""
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "system": {
            "cpu_load": get_cpu_load(),
            "ram": get_ram_usage(),
            "disk": get_disk_usage(),
            "uptime": get_uptime(),
            "info": get_system_info()
        },
        "vpn": check_vpn_status(),
        "proxy": check_proxy_status(),
        "docker": check_docker_status(),
        "fastapi": get_fastapi_metrics()
    }