import asyncio
import csv
import io
import shutil


GPU_QUERY = (
    "--query-gpu=name,driver_version,pci.bus_id,temperature.gpu,fan.speed,power.draw,power.limit,"
    "utilization.gpu,utilization.memory,memory.total,memory.used,memory.free,"
    "clocks.current.graphics,clocks.current.memory,pstate,pcie.link.width.current,"
    "pcie.link.width.max,pcie.link.gen.current,pcie.link.gen.max"
)

GPU_MEMORY_BUS_WIDTH = {
    "NVIDIA GeForce RTX 4060 Ti": "128 бит",
    "NVIDIA GeForce RTX 4070 Ti SUPER": "256 бит",
}


async def get_gpu_status() -> str:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return "Не нашла `nvidia-smi`. Нужна NVIDIA-видеокарта и установленный драйвер NVIDIA."

    try:
        process = await asyncio.create_subprocess_exec(
            executable,
            GPU_QUERY,
            "--format=csv,noheader,nounits",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=8)
    except (OSError, asyncio.TimeoutError):
        return "Не получилось получить данные от `nvidia-smi`: команда не запустилась или превысила таймаут."

    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace").strip()
        return "`nvidia-smi` вернула ошибку" + (f": {detail[:300]}" if detail else ".")

    rows = []
    for columns in csv.reader(io.StringIO(stdout.decode("utf-8", errors="replace"))):
        columns = [column.strip() for column in columns]
        if len(columns) != 19:
            continue
        (
            name, driver, bus, temperature, fan, power, power_limit, gpu_load,
            memory_load, total_mb, used_mb, free_mb, graphics_clock, memory_clock, pstate,
            pcie_width_current, pcie_width_max, pcie_gen_current, pcie_gen_max,
        ) = columns
        try:
            total_gb = int(total_mb) / 1024
            used_gb = int(used_mb) / 1024
            free_gb = int(free_mb) / 1024
            temp_text = f"{int(temperature)} °C" if temperature.isdigit() else "нет данных"
        except ValueError:
            continue
        gpu_load_text = f"{gpu_load}%" if gpu_load.isdigit() else "нет данных"
        memory_load_text = f"{memory_load}%" if memory_load.isdigit() else "нет данных"
        fan_text = f"{fan}%" if fan.isdigit() else "нет данных"
        power_text = f"{power} / {power_limit} Вт" if power.isdigit() and power_limit.isdigit() else "нет данных"
        memory_bus_text = GPU_MEMORY_BUS_WIDTH.get(name, "нет в локальной таблице характеристик")
        pcie_width_text = (
            f"x{pcie_width_current} / x{pcie_width_max}"
            if pcie_width_current.isdigit() and pcie_width_max.isdigit()
            else "нет данных"
        )
        pcie_gen_text = (
            f"Gen {pcie_gen_current} / Gen {pcie_gen_max}"
            if pcie_gen_current.isdigit() and pcie_gen_max.isdigit()
            else "нет данных"
        )
        rows.append(
            f"• **{name}** (PCI {bus})\n"
            f"  Температура {temp_text}; вентилятор {fan_text}; питание {power_text}\n"
            f"  GPU {gpu_load_text}; контроллер памяти {memory_load_text}; "
            f"VRAM {used_gb:.1f}/{total_gb:.1f} ГБ (свободно {free_gb:.1f} ГБ)\n"
            f"  Шина памяти GPU {memory_bus_text}; PCIe сейчас/максимум {pcie_width_text}, {pcie_gen_text}\n"
            f"  Частоты ядра/памяти {graphics_clock}/{memory_clock} МГц; {pstate}; драйвер {driver}"
        )

    if not rows:
        return "`nvidia-smi` не вернула читаемые данные о видеокартах."
    return "📊 **Сейчас по видеокартам:**\n" + "\n".join(rows)
