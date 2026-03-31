"""
System Monitor Tool
Provides system resource monitoring capabilities
"""

import psutil
from typing import Dict, List
from ..utils.logger import setup_logger

logger = setup_logger()

class SystemMonitor:
    """Monitor system resources and processes"""
    
    def get_cpu_usage(self) -> Dict[str, float]:
        """Get CPU usage information"""
        return {
            "overall": psutil.cpu_percent(interval=1),
            "per_core": psutil.cpu_percent(interval=1, percpu=True),
            "count": psutil.cpu_count()
        }
    
    def get_memory_usage(self) -> Dict[str, any]:
        """Get RAM usage information"""
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent": mem.percent
        }
    
    def get_disk_usage(self, path: str = "C:\\") -> Dict[str, any]:
        """Get disk usage information"""
        disk = psutil.disk_usage(path)
        return {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent
        }
    
    def get_top_processes(self, limit: int = 5, sort_by: str = "memory") -> List[Dict]:
        """Get top processes by CPU or memory usage"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                processes.append({
                    "pid": pinfo['pid'],
                    "name": pinfo['name'],
                    "cpu_percent": pinfo['cpu_percent'],
                    "memory_percent": round(pinfo['memory_percent'], 2)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by specified metric
        if sort_by == "cpu":
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
        else:
            processes.sort(key=lambda x: x['memory_percent'], reverse=True)
        
        return processes[:limit]
    
    def get_system_summary(self) -> str:
        """Get human-readable system summary"""
        cpu = self.get_cpu_usage()
        mem = self.get_memory_usage()
        disk = self.get_disk_usage()
        
        summary = f"""
**System Status:**
- **CPU**: {cpu['overall']}% ({cpu['count']} cores)
- **RAM**: {mem['used_gb']}/{mem['total_gb']} GB ({mem['percent']}%)
- **Disk**: {disk['used_gb']}/{disk['total_gb']} GB ({disk['percent']}%)
"""
        return summary.strip()
    
    def get_process_info(self, process_name: str = None, pid: int = None) -> Dict:
        """Get detailed info about a specific process"""
        try:
            if pid:
                proc = psutil.Process(pid)
            elif process_name:
                # Find process by name
                for proc in psutil.process_iter(['name']):
                    if process_name.lower() in proc.info['name'].lower():
                        break
                else:
                    return {"error": f"Process '{process_name}' not found"}
            else:
                return {"error": "Must provide either process_name or pid"}
            
            return {
                "pid": proc.pid,
                "name": proc.name(),
                "status": proc.status(),
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_percent": round(proc.memory_percent(), 2),
                "memory_mb": round(proc.memory_info().rss / (1024**2), 2),
                "num_threads": proc.num_threads(),
                "create_time": proc.create_time()
            }
        except Exception as e:
            return {"error": str(e)}

    def get_battery_status(self) -> Dict:
        """Get battery charge level, charging status, and time remaining."""
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return {"error": "No battery found (this may be a desktop PC)"}
            
            percent = round(battery.percent, 1)
            plugged = battery.power_plugged
            secs = battery.secsleft
            
            # Format time remaining
            if plugged:
                time_info = "Charging"
            elif secs == psutil.POWER_TIME_UNLIMITED:
                time_info = "Full (plugged in)"
            elif secs == psutil.POWER_TIME_UNKNOWN:
                time_info = "Calculating..."
            else:
                hours, rem = divmod(secs, 3600)
                mins = rem // 60
                time_info = f"{int(hours)}h {int(mins)}m remaining"
            
            # Health indicator based on charge
            if percent >= 80:
                health = "Good"
            elif percent >= 40:
                health = "Moderate"
            elif percent >= 20:
                health = "Low — consider charging"
            else:
                health = "Critical — charge immediately!"
            
            return {
                "percent": percent,
                "plugged_in": plugged,
                "status": "Charging" if plugged else "Discharging",
                "time_info": time_info,
                "health": health
            }
        except Exception as e:
            return {"error": str(e)}
