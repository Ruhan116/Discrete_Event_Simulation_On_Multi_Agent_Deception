import os
from datetime import datetime

class SimulationView:
    def __init__(self, trace_file="event_trace.log"):
        self.trace_file = trace_file
        self._setup_log_file()

    def _setup_log_file(self):
        with open(self.trace_file, "w") as f:
            f.write(f"--- Simulation Trace Log ({datetime.now()}) ---\n\n")

    def log_event(self, timestamp, agent_name, event_type):
        message = f"[{timestamp:.2f}] {agent_name} - {event_type}"
        print(message)
        with open(self.trace_file, "a") as f:
            f.write(message + "\n")

    def log_kill(self, killer_name, victim_name):
        message = f"{killer_name} killed {victim_name}!"
        print(message)
        with open(self.trace_file, "a") as f:
            f.write(message + "\n")

    def log_end(self, result):
        message = f"{result}\n"
        print(message)
        with open(self.trace_file, "a") as f:
            f.write(message)
