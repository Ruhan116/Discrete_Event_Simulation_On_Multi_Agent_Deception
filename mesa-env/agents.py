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
        self.tasks = [
            Task("Fix Wiring", (5, 5)),
            Task("Upload Data", (15, 15))
        ]
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
        """Move 1 cell toward target location."""
        if not target_location:
            return
        x, y = self.pos
        tx, ty = target_location
        
        # Calculate direction
        dx = tx - x
        dy = ty - y

        if dx > 0:
            step_x = 1
        elif dx < 0:
            step_x = -1
        else:
            step_x = 0

        if dy > 0:
            step_y = 1
        elif dy < 0:
            step_y = -1
        else:
            step_y = 0
        
        # Prioritize larger axis
        if abs(dx) > abs(dy):
            new_pos = (x + step_x, y)
        else:
            new_pos = (x, y + step_y)
        
        # Move if cell is empty
        if self.model.grid.is_cell_empty(new_pos):
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
            if not agent.alive and self.model.phase == "tasks":
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
        self.fake_tasks = [Task("Fake Task", (10, 10))]
        self.alive = True
        self.kill_cooldown = 0

    def find_isolated_agent(self):
        """Find a crewmate with no witnesses nearby."""
        neighbors = self.model.grid.get_neighbors(self.pos, moore=True, radius=1)
        potential_targets = [
            agent for agent in neighbors
            if isinstance(agent, Crewmate) and agent.alive
        ]
        for target in potential_targets:
            target_neighbors = self.model.grid.get_neighbors(target.pos, moore=True, radius=1)
            if len(target_neighbors) == 1:  # Only the imposter is nearby
                return target
        return None
    
    def kill(self, target):
        """Eliminate a crewmate if isolated."""
        if target.alive and self.is_isolated(target):
            target.alive = False
            self.kill_cooldown = 5
            print(f"Agent {target.unique_id} was killed!")

    def is_isolated(self, target):
        """Check if target is alone."""
        target_neighbors = self.model.grid.get_neighbors(target.pos, moore=True, radius=1)
        return len([agent for agent in target_neighbors if agent != self]) == 0

    def move_toward(self, target_location):
        """Move 1 cell toward target location."""
        if not target_location:
            return
        x, y = self.pos
        tx, ty = target_location
        
        # Calculate direction
        dx = tx - x
        dy = ty - y

        if dx > 0:
            step_x = 1
        elif dx < 0:
            step_x = -1
        else:
            step_x = 0

        if dy > 0:
            step_y = 1
        elif dy < 0:
            step_y = -1
        else:
            step_y = 0
        
        # Prioritize larger axis
        if abs(dx) > abs(dy):
            new_pos = (x + step_x, y)
        else:
            new_pos = (x, y + step_y)
        
        # Move if cell is empty
        if self.model.grid.is_cell_empty(new_pos):
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
