from enum import Enum

class EventType(Enum):
    MOVE = "agent_movement"
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    KILL = "kill"
    MEETING = "emergency_meeting"
    VOTE = "voting"



class Event:
    def __init__(self, event_type, time, agent, data=None):
        self.event_type = event_type
        self.time = time
        self.agent = agent
        self.data = data or {}

    def __lt__(self, other):
        return self.time < other.time

    