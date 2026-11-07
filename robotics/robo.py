import esptool
import serial
import serial.tools.list_ports
import threading
import time
from queue import Queue

ESP_exit_event = threading.Event()

### detect esp ports
class ESPPort:
    def __init__(self):
        self.running = False
        self.poll_interval = 2
        self.last_ports = set()
        self.esp_ports = set()
        self.active_esp_port = None
        self.port_lock = threading.Lock()
        self.verify_queue = Queue()
        self.worker_thread = None
        self.monitor_thread = None
        self.scanned = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.scanned = False
        self.worker_thread = threading.Thread(
            target = self.verification_worker,
            daemon = False
        )
        self.worker_thread.start()
        self.startup_scan()
        self.monitor_thread  = threading.Thread(
            target = self.monitor_esp,
            daemon = False
        )
        self.monitor_thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.verify_queue.put(None)
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout = 1)
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout = 1)
        ESP_exit_event.set()

    # gets active ports
    def get_active_port(self):
        with self.port_lock:
            return self.active_esp_port

    # detect any esp by boot loader
    def detect_esp_by_bootloader(self, port):
        try :
            esp = esptool.get_default_connected_device(
                serial_list=[port],
                port = port,
                connect_attempts = 1,
                # initial_baud = baud
            )
            if esp is None:
                return {
                    "detected": False,
                    "chip": None,
                    "error": "No esp device detected"
                }
            esp._port.close()
            return {
                "detected": True,
                "chip": esp.CHIP_NAME,
                "error": None
            }
        except Exception as e:
            return {
                "detected": False,
                "chip": None,
                "error": str(e)
            }

    # gets the available serial ports
    def get_serial_ports(self):
        return {port.device for port in serial.tools.list_ports.comports()}

    # first scan after startup
    def startup_scan(self):
        ports = self.get_serial_ports()
        self.last_ports = ports
        for port in ports:
            self.verify_queue.put(port)

    # verify port with bootloader
    def verification_worker(self):
        while self.running:
            try:
                port = self.verify_queue.get(timeout = 1)
            except:
                continue
            if port is None:
                return
            result = self.detect_esp_by_bootloader(port)
            if result['detected']:
                print(f"[ESP FOUND] {result['chip']} detected on {port}")
                with self.port_lock:
                    self.esp_ports.add(port)
                    if not self.active_esp_port:
                        self.active_esp_port = port
                        print(f"active esp port: {self.active_esp_port}")
            self.verify_queue.task_done()
            if self.verify_queue.empty():
                self.scanned = True
                print("scanned")

    # scan new ports after startup scan
    def monitor_esp(self):
        while self.running:
            current_ports = self.get_serial_ports()
            connected_ports = current_ports - self.last_ports
            disconnected_ports = self.last_ports - current_ports
            for port in connected_ports:
                self.scanned = False
                self.verify_queue.put(port)
            for port in disconnected_ports:
                self.scanned = False
                with self.port_lock:
                    if port in self.esp_ports:
                        print(f"[ESP DISC] disconnected from {port}")
                        self.esp_ports.remove(port)
                        if port == self.active_esp_port:
                            self.active_esp_port = next(iter(self.esp_ports), None)
                            print(f"active esp port: {self.active_esp_port}")
                self.scanned = True
            self.last_ports = current_ports
            time.sleep(self.poll_interval)

if __name__ == "__main__":
    esp_port = ESPPort()
    esp_port.start()

    while not ESP_exit_event.is_set():
        time.sleep(1)

    print("ESP exited")
