import os
import signal
import subprocess

def kill_processes_on_port(port=8521):
    try:
        result = subprocess.check_output(
            f'netstat -ano | findstr :{port}', shell=True).decode()
        pids = set()
        for line in result.split('\n'):
            if 'LISTENING' in line:
                pid = line.strip().split()[-1]
                pids.add(pid)
        
        for pid in pids:
            os.kill(int(pid), signal.SIGTERM)
            print(f"Killed process {pid} on port {port}")
            
    except subprocess.CalledProcessError:
        print(f"No processes found on port {port}")
    except Exception as e:
        print(f"Error cleaning port {port}: {e}")

if __name__ == "__main__":
    kill_processes_on_port(8521)  