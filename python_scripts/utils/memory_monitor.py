from __future__ import annotations

import time
import psutil
import threading
from datetime import datetime
from gpu_memory_manager import GPUMemoryManager


class SystemMemoryMonitor:
    """Monitor both GPU and system memory usage during FLASH-TV operation"""
    
    def __init__(self, log_interval: int = 300):  # 5 minutes default
        self.log_interval = log_interval
        self.monitoring = False
        self.monitor_thread = None
        self.log_file = None
        
    def start_monitoring(self, log_file_path: str | None = None) -> None:
        """Start continuous memory monitoring"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.log_file = log_file_path
        
        if self.log_file:
            with open(self.log_file, 'w') as f:
                f.write("timestamp,gpu_allocated_gb,gpu_reserved_gb,gpu_free_gb,gpu_utilization_pct,")
                f.write("ram_used_gb,ram_free_gb,ram_utilization_pct,cpu_percent\n")
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        print(f"Memory monitoring started (interval: {self.log_interval}s)")
        if self.log_file:
            print(f"Logging to: {self.log_file}")
    
    def stop_monitoring(self) -> None:
        """Stop memory monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        print("Memory monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop running in separate thread"""
        while self.monitoring:
            try:
                self._log_memory_status()
                time.sleep(self.log_interval)
            except Exception as e:
                print(f"Memory monitoring error: {e}")
                time.sleep(10)  # Wait before retry
    
    def _log_memory_status(self) -> None:
        """Log current memory status"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # GPU memory
        gpu_status = GPUMemoryManager.get_gpu_memory_status()
        
        # System memory  
        ram = psutil.virtual_memory()
        ram_used_gb = ram.used / (1024**3)
        ram_free_gb = ram.available / (1024**3) 
        ram_util_pct = ram.percent
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Console output
        print(f"\n[{timestamp}] Memory Status:")
        if gpu_status:
            print(f"  GPU: {gpu_status['allocated_gb']:.1f}GB allocated, "
                  f"{gpu_status['reserved_gb']:.1f}GB reserved, "
                  f"{gpu_status['utilization_pct']:.1f}% usage")
        print(f"  RAM: {ram_used_gb:.1f}GB used, {ram_free_gb:.1f}GB free, "
              f"{ram_util_pct:.1f}% usage")
        print(f"  CPU: {cpu_percent:.1f}%")
        
        # File logging
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    if gpu_status:
                        f.write(f"{timestamp},{gpu_status['allocated_gb']:.2f},"
                               f"{gpu_status['reserved_gb']:.2f},{gpu_status['free_gb']:.2f},"
                               f"{gpu_status['utilization_pct']:.1f},")
                    else:
                        f.write(f"{timestamp},0.0,0.0,0.0,0.0,")
                    
                    f.write(f"{ram_used_gb:.2f},{ram_free_gb:.2f},{ram_util_pct:.1f},"
                           f"{cpu_percent:.1f}\n")
            except Exception as e:
                print(f"Failed to write memory log: {e}")
    
    def get_current_status(self) -> dict[str, any]:
        """Get current memory status as dictionary"""
        gpu_status = GPUMemoryManager.get_gpu_memory_status()
        ram = psutil.virtual_memory()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'gpu': gpu_status,
            'ram': {
                'used_gb': ram.used / (1024**3),
                'free_gb': ram.available / (1024**3),
                'utilization_pct': ram.percent
            },
            'cpu_percent': psutil.cpu_percent()
        }


def start_flash_memory_monitoring(log_path: str | None = None, interval: int = 300) -> SystemMemoryMonitor:
    """Convenience function to start memory monitoring for FLASH-TV"""
    monitor = SystemMemoryMonitor(log_interval=interval)
    monitor.start_monitoring(log_path)
    return monitor


# Global monitor instance for easy access
_global_monitor = None

def get_global_monitor() -> SystemMemoryMonitor:
    """Get the global memory monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = SystemMemoryMonitor()
    return _global_monitor