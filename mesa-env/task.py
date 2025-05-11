class Task:
    def __init__(self, name, location):
        self.name = name
        self.location = location
        self.progress = 0
        self.complete = False

    def do_task(self):
        self.progress += 1
        if self.progress >= 3:  # Short task
            self.complete = True