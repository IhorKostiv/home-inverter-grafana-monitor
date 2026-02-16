# todo: add throttled monitoring
import subprocess
import time
from datetime import datetime

# Log file to store power status
log_file = "power_status_log.txt"

# Bitmask definitions for throttled flags
flags = {
    0: "Under-voltage detected (currently)",
    1: "ARM frequency capped (currently)",
    2: "Currently throttled",
    3: "Soft temperature limit active",
    16: "Under-voltage has occurred",
    17: "ARM frequency capping has occurred",
    18: "Throttling has occurred",
    19: "Soft temperature limit has occurred"
}

def decode_throttled(hex_value):
    value = int(hex_value, 16)
    return [desc for bit, desc in flags.items() if value & (1 << bit)]

def log_status(timestamp, hex_value, messages):
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] Throttled: {hex_value} - {'; '.join(messages) if messages else 'All good'}\n")

def monitor_power_status(interval=10):
    print("Monitoring Raspberry Pi power status. Press Ctrl+C to stop.")
    try:
        while True:
            result = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True)
            output = result.stdout.strip()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if output.startswith("throttled="):
                hex_value = output.split("=")[1]
                messages = decode_throttled(hex_value)
                log_status(timestamp, hex_value, messages)

                if messages:
                    print(f"[{timestamp}] ALERT: {', '.join(messages)}")
                else:
                    print(f"[{timestamp}] OK: No issues detected.")

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == '__main__':
    monitor_power_status()

