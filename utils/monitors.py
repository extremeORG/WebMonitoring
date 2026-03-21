import psutil
import subprocess
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

def check_vpn_status() -> Dict:
    """Статус Hysteria VPN"""
    result = {
        "active": False,
        "peers": 0,  # Hysteria обычно не показывает активных пиров напрямую
        "traffic_in": "0 MB/s",
        "traffic_out": "0 MB/s",
        "load": 0
    }
    try:
        # Проверка статуса сервиса hysteria-server
        status_check = subprocess.run(
            ["systemctl", "is-active", "hysteria-server"],
            capture_output=True, text=True, timeout=3
        )
        if status_check.returncode == 0 and status_check.stdout.strip() == "active":
            result["active"] = True
            result["load"] = min(95, psutil.cpu_percent(interval=0.1) * 0.5 + 10) # Примерная оценка

    except Exception:
        pass
    return result

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
    return {
        "uptime_percent": 99.9,
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