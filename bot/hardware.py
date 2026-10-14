"""Read-only Windows and NVIDIA hardware status helpers."""

import asyncio
import ctypes
import os
import platform
import re
import subprocess
import sys
import winreg

import psutil

from bot.gpu import get_gpu_status


def _format_bytes(value: int) -> str:
    return f"{value / (1024 ** 3):.1f} ГБ"


def _powershell_json(script: str) -> object | None:
    if os.name != "nt":
        return None
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        import json

        return json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _memory_modules() -> list[dict[str, object]]:
    result = _powershell_json(
        "Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer,PartNumber,Capacity,"
        "SMBIOSMemoryType,Speed,ConfiguredClockSpeed,DeviceLocator,BankLabel | ConvertTo-Json -Compress"
    )
    if isinstance(result, dict):
        return [result]
    return result if isinstance(result, list) and all(isinstance(row, dict) for row in result) else []


_MEMORY_TYPES = {
    20: "DDR",
    21: "DDR2",
    24: "DDR3",
    26: "DDR4",
    30: "LPDDR4",
    34: "DDR5",
    35: "LPDDR5",
}


async def get_memory_status() -> str:
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    lines = [
        "🧠 **Оперативная память**",
        f"• Установлено: {_format_bytes(memory.total)}",
        f"• Занято: {_format_bytes(memory.used)} ({memory.percent:.0f}%)",
        f"• Доступно: {_format_bytes(memory.available)}",
    ]
    if swap.total:
        lines.append(
            f"• Файл подкачки: {_format_bytes(swap.used)} занято из {_format_bytes(swap.total)} "
            f"(свободно {_format_bytes(swap.free)})"
        )
    else:
        lines.append("• Файл подкачки: Windows не предоставила счётчики через системный интерфейс.")

    modules = await asyncio.to_thread(_memory_modules)
    if modules:
        total_capacity = sum(int(module.get("Capacity") or 0) for module in modules)
        types = sorted(
            {
                _MEMORY_TYPES.get(int(module.get("SMBIOSMemoryType") or 0), "")
                for module in modules
            }
            - {""}
        )
        speeds = sorted({int(module.get("ConfiguredClockSpeed") or module.get("Speed") or 0) for module in modules} - {0})
        lines.append(f"• Модули: {len(modules)} × ориентировочно {_format_bytes(total_capacity // len(modules))}")
        lines.append(f"• Тип: {', '.join(types) if types else 'не сообщён прошивкой'}")
        lines.append(f"• Скорость: {', '.join(map(str, speeds)) + ' МТ/с' if speeds else 'нет данных'}")
        lines.append("• Канальность: Windows не сообщает активный режим каналов; число модулей не всегда ему равно.")
    else:
        lines.append("• Тип модулей, скорость и канальность: Windows не предоставила данные SMBIOS.")
    return "\n".join(lines)


def _cpu_model() -> str:
    if os.name == "nt":
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                if value.strip():
                    return value.strip()
        except OSError:
            pass
    return platform.processor() or platform.uname().processor or "Windows не сообщила модель процессора"


async def get_cpu_status() -> str:
    physical = psutil.cpu_count(logical=False)
    logical = psutil.cpu_count(logical=True)
    load = await asyncio.to_thread(psutil.cpu_percent, 0.7)
    frequency = psutil.cpu_freq()
    lines = [
        "⚙️ **Процессор**",
        f"• Модель: {_cpu_model()}",
        f"• Физические ядра: {physical if physical is not None else 'нет данных'}",
        f"• Логические ядра / потоки: {logical if logical is not None else 'нет данных'}",
        f"• Общая загрузка: {load:.0f}%",
    ]
    if frequency:
        maximum = f", максимум {frequency.max:.0f} МГц" if frequency.max else ""
        lines.append(f"• Текущая частота: {frequency.current:.0f} МГц{maximum}")
    else:
        lines.append("• Частота: нет данных от системы")
    lines.append("• Температуры ядер: стандартный интерфейс Windows не предоставляет показания датчика.")
    return "\n".join(lines)


def get_os_status() -> str:
    version = sys.getwindowsversion() if sys.platform == "win32" else None
    if version:
        build = version.build
        edition_data = _powershell_json(
            "Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion' | "
            "Select-Object ProductName,DisplayVersion,CurrentBuild,UBR | ConvertTo-Json -Compress"
        )
        if isinstance(edition_data, dict):
            name = edition_data.get("ProductName") or platform.system()
            display = edition_data.get("DisplayVersion")
            build = edition_data.get("CurrentBuild") or build
            ubr = edition_data.get("UBR")
            build_label = f"{build}.{ubr}" if ubr is not None else str(build)
            return (
                f"🪟 **Операционная система**\n• {name}"
                f"{f' {display}' if display else ''}\n• Версия {platform.version()}"
                f"; сборка {build_label}\n• Разрядность: {platform.architecture()[0]}"
            )
        return (
            f"🪟 **Операционная система**\n• {platform.system()} {platform.release()}"
            f"\n• Версия {platform.version()}; сборка {build}"
            f"\n• Разрядность: {platform.architecture()[0]}"
        )
    return f"🖥 **Операционная система**\n• {platform.platform()}"


def _disk_temperature(drive_letter: str) -> str | None:
    script = (
        f"$p=Get-Partition -DriveLetter '{drive_letter}' -ErrorAction Stop | Get-Disk -ErrorAction Stop; "
        "$physical=Get-PhysicalDisk -ErrorAction Stop | Where-Object { $_.DeviceId -eq $p.Number }; "
        "if ($null -eq $physical) { exit 2 }; "
        "@{Model=$physical.FriendlyName;Temperature=$physical.Temperature;Health=$physical.HealthStatus;"
        "MediaType=$physical.MediaType;BusType=$physical.BusType} | ConvertTo-Json -Compress"
    )
    result = _powershell_json(script)
    if isinstance(result, dict) and result.get("Temperature") is not None:
        return f"{result['Temperature']} °C"
    if os.name == "nt":
        try:
            handle = ctypes.windll.kernel32.CreateFileW(
                f"\\\\.\\{drive_letter}:", 0,
                0x1 | 0x2, None, 3, 0, None,
            )
            invalid_handle = ctypes.c_void_p(-1).value
            if handle == invalid_handle:
                return None

            class _StoragePropertyQuery(ctypes.Structure):
                _fields_ = [("PropertyId", ctypes.c_ulong), ("QueryType", ctypes.c_ulong), ("AdditionalParameters", ctypes.c_ubyte * 1)]

            class _TemperatureData(ctypes.Structure):
                _fields_ = [
                    ("CriticalTemperature", ctypes.c_ulong),
                    ("WarningTemperature", ctypes.c_ulong),
                    ("Temperature", ctypes.c_ulong),
                    ("Drivespeed", ctypes.c_ulong),
                    ("DriveMax", ctypes.c_ulong),
                    ("ControllerMax", ctypes.c_ulong),
                ]

            class _TemperatureDescriptor(ctypes.Structure):
                _fields_ = [
                    ("Version", ctypes.c_ulong),
                    ("Size", ctypes.c_ulong),
                    ("Health", ctypes.c_ubyte),
                    ("TemperatureInfo", _TemperatureData * 1),
                ]

            query = _StoragePropertyQuery(50, 0, (ctypes.c_ubyte * 1)(0))
            descriptor = _TemperatureDescriptor()
            returned = ctypes.c_ulong()
            ok = ctypes.windll.kernel32.DeviceIoControl(
                handle, 0x002D1400, ctypes.byref(query), ctypes.sizeof(query),
                ctypes.byref(descriptor), ctypes.sizeof(descriptor), ctypes.byref(returned), None,
            )
            ctypes.windll.kernel32.CloseHandle(handle)
            temperature = descriptor.TemperatureInfo[0].Temperature
            if ok and 1 <= temperature <= 150:
                return f"{temperature} °C"
        except (AttributeError, OSError, ValueError):
            pass
    return None


async def get_model_disk_status() -> str:
    drive = "L:\\"
    try:
        usage = await asyncio.to_thread(psutil.disk_usage, drive)
    except (OSError, ValueError):
        return "💽 Диск моделей L: сейчас недоступен или не подключён."

    lines = [
        "💽 **Диск моделей L:**",
        f"• Объём: {_format_bytes(usage.total)}",
        f"• Занято: {_format_bytes(usage.used)} ({usage.percent:.1f}%)",
        f"• Свободно: {_format_bytes(usage.free)}",
    ]
    temperature = await asyncio.to_thread(_disk_temperature, "L")
    lines.append(f"• Температура накопителя: {temperature or 'контроллер не предоставил датчик через Windows.'}")
    return "\n".join(lines)


def hardware_request(text: str) -> str | None:
    normalized = text.casefold().replace("ё", "е")
    normalized = re.sub(r"(.)\1{2,}", r"\1\1", normalized, flags=re.UNICODE)
    gpu_terms = (
        "видеокарт", "видеокар", "видокарт", "видокарат", "video card", "graphics card", "graphics", "grapphics",
        "video memory", "видеопамят", "видеопам", "видеочип", "video", "видео",
        "видюх", "видях", "видюха", "видяха", "gpu", "гпу", "nvidia", "nvidia-smi",
        "графическ", "графика", "3d accelerator", "3д акселератор", "3d акселератор", "ускорител", "vram", "врам",
    )
    ram_terms = (
        "оператив", "операт", "опиратив", "операта", "оперативка", "оперативочк", "оперативная память",
        "озу", "ram", "рам", "ddr", "димм", "dimm",
        "своп", "swap", "файл подкач", "виртуальн память", "память занята", "занято памяти",
        "сколько памяти", "тип памяти", "канальност", "память", "памяти", "memory",
    )
    cpu_terms = (
        "процессор", "процесор", "проц", "камень", "камушек", "камешек", "камуш", "cpu", "цпу",
        "центральн процессор", "центральный проц", "central processing unit", "ядр процессора", "ядра cpu",
        "сколько ядер", "много ядер", "поток процессора", "частот процессора", "processor", "core count",
    )
    os_terms = (
        "операционн систем", "операционка", "какая ось", "оська", "оска", "какая виндовс", "какая windows",
        "винда", "виндовс", "windows", "win 10", "win 11", "версия винд", "версия windows",
        "сборка", "билд винд", "build windows",
    )
    disk_terms = (
        "носител", "диск", "накопител", "хранилище", "storage", "drive", "ssd", "ссд", "nvme", "нвме", "нвм", "hdd", "хдд",
        "винт", "жестк", "жёстк", "хард", "флешк", "hard drive", "storage drive", "solid state drive",
    )
    all_hardware_terms = (
        "железо", "железки", "характеристики компьютера", "характеристики компа", "характеристики пк",
        "конфигурация компьютера", "спеки компа", "спеки пк", "что за компьютер", "что за комп",
        "весь комп",
    )
    if any(term in normalized for term in all_hardware_terms):
        return "all"
    if re.search(r"(?<![а-яa-z])граф(?:а|ы|е|у|ой)(?![а-яa-z])", normalized):
        return "gpu"
    disk_letter = bool(re.search(r"(?:\bдиск\s+|\bнакопител\w*\s+|\bdrive\s+|\bна\s+)l\s*:?(?![a-zа-я])|(?<!\w)l\s*:", normalized))
    if disk_letter or any(term in normalized for term in disk_terms):
        return "disk"
    if any(term in normalized for term in os_terms):
        return "os"
    if any(term in normalized for term in cpu_terms):
        return "cpu"
    if any(term in normalized for term in gpu_terms) or re.search(r"(?<!\w)чип\w*", normalized):
        return "gpu"
    if any(term in normalized for term in ram_terms):
        return "ram"
    if any(term in normalized for term in ("температур", "темпа", "горяч", "жар", "нагрева", "нагрузк", "загрузк", "температура", "сколько градусов")):
        return "gpu"
    return None

