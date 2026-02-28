import os
import shutil

from notify import main as notify_main


def read_memory_usage() -> float:
    mem_total = 0
    mem_available = 0
    with open("/proc/meminfo", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("MemTotal"):
                mem_total = int(line.split()[1])
            if line.startswith("MemAvailable"):
                mem_available = int(line.split()[1])
    if mem_total == 0:
        return 0.0
    return (mem_total - mem_available) / mem_total


def read_cpu_usage() -> float:
    load1, _, _ = os.getloadavg()
    cpu_count = os.cpu_count() or 1
    return min(load1 / cpu_count, 1.0)


def read_disk_usage(path: str = "/") -> float:
    usage = shutil.disk_usage(path)
    return usage.used / usage.total


def main() -> None:
    cpu_threshold = float(os.getenv("CPU_THRESHOLD", "0.8"))
    memory_threshold = float(os.getenv("MEMORY_THRESHOLD", "0.85"))
    disk_threshold = float(os.getenv("DISK_THRESHOLD", "0.85"))

    cpu = read_cpu_usage()
    memory = read_memory_usage()
    disk = read_disk_usage()

    breaches = []
    if cpu >= cpu_threshold:
        breaches.append(f"CPU {cpu:.0%} >= {cpu_threshold:.0%}")
    if memory >= memory_threshold:
        breaches.append(f"memory {memory:.0%} >= {memory_threshold:.0%}")
    if disk >= disk_threshold:
        breaches.append(f"disk {disk:.0%} >= {disk_threshold:.0%}")

    if breaches:
        os.environ["NOTIFICATION_TEXT"] = "PulseBoard resource alert: " + ", ".join(breaches)
        notify_main()
        raise SystemExit(1)

    print(f"Resource checks passed (cpu={cpu:.0%}, memory={memory:.0%}, disk={disk:.0%})")


if __name__ == "__main__":
    main()
