from mesa import Model, Agent
from task import Task
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
import random



class Crewmate(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.visibility = 6

        # Only use main rooms (not hallways) for tasks
        main_rooms = [room for room in model.rooms if room[4] not in ["Hallway"]]
        self.tasks = []
        for room in main_rooms:
            # Place the task at the center of the room
            center_x = (room[0] + room[2]) // 2
            center_y = (room[1] + room[3]) // 2
            self.tasks.append(Task(f"{room[4]} Task", (center_x, center_y)))

        self.suspicion_pairs = {} # {(agent1_id, agent2_id): score}
        self.alive = True

    def find_nearest_task(self):
        """Find closest incomplete task using Manhattan distance."""
        closest = None
        min_dist = float('inf')
        x, y = self.pos
        for task in self.tasks:
            if task.complete:
                continue
            tx, ty = task.location
            dist = abs(tx - x) + abs(ty - y)
            if dist < min_dist:
                min_dist = dist
                closest = task
        return closest

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

        # Try x-axis first if not already at target x
        if step_x != 0:
            new_pos = (x + step_x, y)
            if self.model.is_valid_position(new_pos):
                self.model.grid.move_agent(self, new_pos)
                return

        # Then try y-axis if not already at target y
        if step_y != 0:
            new_pos = (x, y + step_y)
            if self.model.is_valid_position(new_pos):
                self.model.grid.move_agent(self, new_pos)
                return

        # Finally try diagonal if both steps are needed
        if step_x != 0 and step_y != 0:
            new_pos = (x + step_x, y + step_y)
            if self.model.is_valid_position(new_pos):
                self.model.grid.move_agent(self, new_pos)

    def do_task(self, task):
        """Progress on a task."""
        if self.pos == task.location:
            task.do_task()
            if task.complete:
                print(f"Agent {self.unique_id} completed {task.name}!")
    
    def update_suspicions(self, visible_agents):
        """Update suspicion scores based on visible agent pairs."""
        # Track all pairs in visible area
        visible_ids = [a.unique_id for a in visible_agents if a != self]
        
        # Create all possible pairs
        for i in range(len(visible_ids)):
            for j in range(i+1, len(visible_ids)):
                pair = frozenset({visible_ids[i], visible_ids[j]})
                self.suspicion_pairs[pair] = self.suspicion_pairs.get(pair, 0) + 1

    def check_for_bodies(self, visible_agents):
        """Check for dead agents in visibility and trigger discussion."""
        for agent in visible_agents:
            # Only consider Crewmate or Imposter as valid bodies
            if hasattr(agent, "alive") and not agent.alive and isinstance(agent, (Crewmate, Imposter)) and self.model.phase == "tasks":
                print(f"Agent {self.unique_id} found body of {agent.unique_id}!")
                self.model.reported_body = agent.pos
                self.model.phase = "discussion"
                return True
        return False

    def step(self):
        if not self.alive:
            return
        
        # Move toward nearest task
        task = self.find_nearest_task()
        if task:
            self.move_toward(task.location)
            self.do_task(task)
        
        # Get visible agents
        visible_agents = self.model.grid.get_neighbors(
            self.pos, moore=True, radius=self.visibility, include_center=True
        )
        
        # Update suspicion pairs
        self.update_suspicions(visible_agents)
        
        # Check for dead bodies
        self.check_for_bodies(visible_agents)


class Imposter(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.visibility = 9

        # Only use main rooms (not hallways) for fake tasks
        main_rooms = [room for room in model.rooms if room[4] not in ["Hallway"]]
        self.fake_tasks = []
        for room in main_rooms:
            center_x = (room[0] + room[2]) // 2
            center_y = (room[1] + room[3]) // 2
            self.fake_tasks.append(Task(f"Fake {room[4]} Task", (center_x, center_y)))

        self.alive = True
        self.kill_cooldown = 0

    def find_isolated_agent(self):
        """Find a crewmate with no witnesses nearby."""
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, radius=1)
        potential_targets = [
            agent for agent in neighbors
            if isinstance(agent, Crewmate) and hasattr(agent, "alive") and agent.alive
        ]
        for target in potential_targets:
            target_neighbors = self.model.grid.get_neighbors(target.pos, moore=True, radius=1)
            if len([a for a in target_neighbors if isinstance(a, (Crewmate, Imposter)) and hasattr(a, "alive") and a.alive]) == 1:  # Only the imposter is nearby
                return target
        return None
    
    def kill(self, target):
        """Eliminate a crewmate if isolated."""
        if hasattr(target, "alive") and target.alive and self.is_isolated(target):
            target.alive = False
            self.kill_cooldown = 5
            print(f"Agent {target.unique_id} was killed!")

    def is_isolated(self, target):
        """Check if target is alone."""
        target_neighbors = self.model.grid.get_neighbors(target.pos, moore=True, radius=1)
        return len([agent for agent in target_neighbors if agent != self and isinstance(agent, (Crewmate, Imposter)) and hasattr(agent, "alive") and agent.alive]) == 0

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

        # Try x-axis first if not already at target x
        if step_x != 0:
            new_pos = (x + step_x, y)
            if self.model.is_valid_position(new_pos):
                self.model.grid.move_agent(self, new_pos)
                return

        # Then try y-axis if not already at target y
        if step_y != 0:
            new_pos = (x, y + step_y)
            if self.model.is_valid_position(new_pos):
                self.model.grid.move_agent(self, new_pos)
                return

        # Finally try diagonal if both steps are needed
        if step_x != 0 and step_y != 0:
            new_pos = (x + step_x, y + step_y)
            if self.model.is_valid_position(new_pos):
                self.model.grid.move_agent(self, new_pos)

    def step(self):
        if not self.alive or self.kill_cooldown > 0:
            self.kill_cooldown -= 1
            return
        
        # Attempt kill
        target = self.find_isolated_agent()
        if target:
            self.kill(target)
        
        # Fake task behavior
        task = self.fake_tasks[0]
        self.move_toward(task.location)
