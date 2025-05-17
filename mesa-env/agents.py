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
        self.suspicion_pairs = {}

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

    def update_suspicions(self, visible_agents):
        visible_ids = [a.unique_id for a in visible_agents if a != self]
        for i in range(len(visible_ids)):
            for j in range(i + 1, len(visible_ids)):
                pair = frozenset({visible_ids[i], visible_ids[j]})
                self.suspicion_pairs[pair] = self.suspicion_pairs.get(pair, 0) + 1

    def check_for_bodies(self, visible_agents):
        if self.model.phase != "tasks":
            return False
        for agent in visible_agents:
            if hasattr(agent, "alive") and not agent.alive and isinstance(agent, (Crewmate, Imposter)) and self.model.phase == "tasks":
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
