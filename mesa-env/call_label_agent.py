from mesa import Agent

class CellLabelAgent(Agent):
    """Agent for displaying room labels on the grid"""
    def __init__(self, unique_id, model, label, room_coords):
        super().__init__(unique_id, model)
        self.label = label
        self.room_coords = room_coords  
        self.layer = 0  
        self.alive = False