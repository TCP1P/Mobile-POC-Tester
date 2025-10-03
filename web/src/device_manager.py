import time
from threading import Thread, Lock
from lamda.client import Device

class DeviceManager:
    def __init__(self, device_host="localhost"):
        self.device = Device(device_host)
        self.device_ready = False
        self.device_status_lock = Lock()
        self.running = False
        self.thread = None

    def check_device_status(self):
        """Check if device is ready and update global status"""
        try:
            cmd = self.device.execute_script('echo 1', timeout=3)
            is_ready = cmd.stdout.decode().strip() == '1'
        except Exception:
            is_ready = False
        
        with self.device_status_lock:
            self.device_ready = is_ready
        
        return is_ready

    def is_device_ready(self):
        """Get current device status (thread-safe)"""
        with self.device_status_lock:
            return self.device_ready

    def start_monitoring(self, check_interval=5):
        """Start the device monitoring thread"""
        if self.running:
            return
        
        self.running = True
        self.thread = DeviceCheckThread(self, check_interval)
        self.thread.start()

    def stop_monitoring(self):
        """Stop the device monitoring thread"""
        self.running = False
        if self.thread:
            self.thread.stop()

class DeviceCheckThread(Thread):
    def __init__(self, device_manager, check_interval=5):
        super().__init__(daemon=True)
        self.device_manager = device_manager
        self.check_interval = check_interval
        self.running = True

    def run(self):
        while self.running and self.device_manager.running:
            try:
                self.device_manager.check_device_status()
            except Exception as e:
                import traceback
                traceback.print_exc()
            
            time.sleep(self.check_interval)

    def stop(self):
        self.running = False
