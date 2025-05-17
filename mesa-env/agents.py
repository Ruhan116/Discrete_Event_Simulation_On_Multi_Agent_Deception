from mesa import Model, Agent
from task import Task
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
import random



class PlayerAgent(Agent):
    def __init__(self, unique_id, model, visibility):
        super().__init__(unique_id, model)
        self.visibility = visibility
        self.alive = True

    def move_toward(self, target_location):
        """Move 1 cell toward target location only if valid and not already there."""
        if not target_location or self.pos == target_location:
            return

        x, y = self.pos
        tx, ty = target_location

        dx = tx - x
        dy = ty - y

        step_x = 1 if dx > 0 else -1 if dx < 0 else 0
        step_y = 1 if dy > 0 else -1 if dy < 0 else 0

        # Try x-axis first
        if step_x != 0:
            new_pos = (x + step_x, y)
            if self.model.is_valid_position(new_pos):
                self.model.grid.move_agent(self, new_pos)
                return

        # Then try y-axis
        if step_y != 0:
            new_pos = (x, y + step_y)
            if self.model.is_valid_position(new_pos):
                self.model.grid.move_agent(self, new_pos)
                return

        # Finally try diagonal
        if step_x != 0 and step_y != 0:
            new_pos = (x + step_x, y + step_y)
            if self.model.is_valid_position(new_pos):
                self.model.grid.move_agent(self, new_pos)


class Crewmate(PlayerAgent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model, visibility=6)
        main_rooms = [room for room in model.rooms if room[4] != "Hallway"]
        self.tasks = [
            Task(f"{room[4]} Task", ((room[0] + room[2]) // 2, (room[1] + room[3]) // 2))
            for room in main_rooms
        ]
        self.suspicion_pairs = {}  # Format: {frozenset: {"count": int, "rooms": list}}

    def update_suspicions(self, visible_agents):
        current_room = self.model.get_room(self.pos)
        visible_players = [
            a for a in visible_agents 
            if a != self and isinstance(a, (Crewmate, Imposter))
        ]
        
        # Initialize suspicion_pairs if missing
        if not hasattr(self, 'suspicion_pairs'):
            self.suspicion_pairs = {}

        # Collect all unique pairs this step for tracing
        trace_pairs = set()
        # Track pairs for suspicion (separate from tracing)
        for i in range(len(visible_players)):
            for j in range(i + 1, len(visible_players)):
                agent1 = visible_players[i].unique_id
                agent2 = visible_players[j].unique_id
                pair = frozenset({agent1, agent2})

                # For tracing (your original format)
                trace_pairs.add(f"{{Agent {min(agent1, agent2)}, Agent {max(agent1, agent2)}, {current_room}}}")

                # Initialize pair data structure properly
                if pair not in self.suspicion_pairs:
                    self.suspicion_pairs[pair] = {"count": 0, "rooms": []}
                
                # Update count (not the whole dict)
                self.suspicion_pairs[pair]["count"] += 1
                self.suspicion_pairs[pair]["rooms"].append(current_room)
        
        # Write to trace file
        if not hasattr(self, '_trace_file'):
            self._trace_file = open(f"agent_{self.unique_id}_trace.log", "w")
        self._trace_file.write(
            f"Step {self.model.schedule.steps}: [{', '.join(sorted(trace_pairs))}]\n"
        )
        self._trace_file.flush()
        
        # Debug output
        # print(f"Agent {self.unique_id} suspicion_pairs: {self.suspicion_pairs}")

        
    def close_trace_file(self):
        if hasattr(self, '_trace_file'):
            self._trace_file.close()

    def find_nearest_task(self):
        closest, min_dist = None, float("inf")
        x, y = self.pos
        for task in self.tasks:
            if task.complete:
                continue
            tx, ty = task.location
            dist = abs(tx - x) + abs(ty - y)
            if dist < min_dist:
                closest, min_dist = task, dist
        return closest

    def do_task(self, task):
        if self.pos == task.location:
            task.do_task()
            if task.complete:
                print(f"Agent {self.unique_id} completed {task.name}!")

    
    def check_for_bodies(self, visible_agents):
        if self.model.phase != "tasks":
            return False
        for agent in visible_agents:
            if isinstance(agent, (Crewmate, Imposter)) and not agent.alive:
                print(f"Agent {self.unique_id} found body of {agent.unique_id}!")
                self.model.reported_body = agent.pos
                self.model.phase = "discussion"
                return True
        return False

    def step(self):
        if not self.alive:
            return

        task = self.find_nearest_task()
        if task:
            self.move_toward(task.location)
            self.do_task(task)

        visible_agents = self.model.grid.get_neighbors(
            self.pos, moore=True, radius=self.visibility, include_center=True
        )

        self.update_suspicions(visible_agents)
        self.check_for_bodies(visible_agents)


class Imposter(PlayerAgent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model, visibility=9)

        main_rooms = [room for room in model.rooms if room[4] != "Hallway"]
        self.fake_tasks = [
            Task(f"Fake {room[4]} Task", ((room[0] + room[2]) // 2, (room[1] + room[3]) // 2))
            for room in main_rooms
        ]
        self.kill_cooldown = 0

    def find_isolated_agent(self):
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, radius=1)
        potential_targets = [
            a for a in neighbors if isinstance(a, Crewmate) and a.alive
        ]
        for target in potential_targets:
            nearby = self.model.grid.get_neighbors(target.pos, moore=True, radius=1)
            if len([a for a in nearby if a.alive and isinstance(a, (Crewmate, Imposter))]) == 1:
                return target
        return None

    def is_isolated(self, target):
        neighbors = self.model.grid.get_neighbors(target.pos, moore=True, radius=1)
        return len([a for a in neighbors if a != self and a.alive and isinstance(a, (Crewmate, Imposter))]) == 0

    def kill(self, target):
        if target.alive and self.is_isolated(target):
            target.alive = False
            self.kill_cooldown = 5
            print(f"Agent {target.unique_id} was killed!")

    def step(self):
        if not self.alive:
            return

        if self.kill_cooldown > 0:
            self.kill_cooldown -= 1
            return

        target = self.find_isolated_agent()
        if target:
            self.kill(target)

        # Move toward a fake task
        task = self.fake_tasks[0]
        self.move_toward(task.location)
