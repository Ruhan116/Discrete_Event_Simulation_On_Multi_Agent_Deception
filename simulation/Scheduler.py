import heapq

class Scheduler:
    _instance = None
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.__init__()
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.clock = 0.0
            self.event_queue = []
            self.initialized = True
    
    def add_event(self, event):
        heapq.heappush(self.event_queue, event)
    
    def get_next_event(self):
        try:
            return heapq.heappop(self.event_queue)
        except IndexError:
            return None
    
    def process_next_event(self):
        next_event = self.get_next_event()
        if next_event:
            self.clock = next_event.time
            return next_event
        return None