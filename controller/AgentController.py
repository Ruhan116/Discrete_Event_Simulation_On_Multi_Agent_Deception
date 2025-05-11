import random
from simulation.Event import Event, EventType

class AgentController:
    def __init__(self, model, room_graph):
        self.model = model
        self.room_graph = room_graph

    def decide_next_action(self, current_time, agents):
        raise NotImplementedError("Subclasses must implement this method.")


class CrewmateController(AgentController):
    def decide_next_action(self, current_time, agents):
        if not self.model.alive:
            return None

        action_type = random.choice(['move', 'task'])

        if action_type == 'move':
            neighbors = self.room_graph.get_neighbors(self.model.current_room)
            if not neighbors:
                return None
            destination = random.choice(neighbors)
            return Event(EventType.MOVE, current_time + random.uniform(1, 5), self.model, {
                'source': self.model.current_room,
                'destination': destination,
                'path': [self.model.current_room, destination]
            })

        elif action_type == 'task':
            return Event(EventType.TASK_START, current_time + random.uniform(1, 3), self.model, {
                'room': self.model.current_room,
                'task': f"Task_{random.randint(1, 5)}"
            })



class ImposterController(AgentController):
    def decide_next_action(self, current_time, agents):
        if not self.model.alive:
            return None

        crewmates_in_room = [
            agent for agent in agents
            if agent.model.current_room == self.model.current_room and
            agent.model.alive and
            agent.model.role == "crewmate"
        ]

        if crewmates_in_room:
            target = random.choice(crewmates_in_room)
            return Event(EventType.KILL, current_time + random.uniform(1, 2), self.model, {
                'target': target.model.name,
                'room': self.model.current_room,
                'witnesses': []  
            })

        neighbors = self.room_graph.get_neighbors(self.model.current_room)
        if not neighbors:
            return None
        destination = random.choice(neighbors)
        return Event(EventType.MOVE, current_time + random.uniform(1, 5), self.model, {
            'source': self.model.current_room,
            'destination': destination,
            'path': [self.model.current_room, destination]
        })
