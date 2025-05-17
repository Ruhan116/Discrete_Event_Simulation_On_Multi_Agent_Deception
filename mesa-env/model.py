from mesa import Model, Agent
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from agents import Crewmate, Imposter
from call_label_agent import CellLabelAgent
import random

class AmongUsModel(Model):
    def __init__(self, width=20, height=20, num_agents=10, num_imposters=1):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)
        self.schedule = RandomActivation(self)
        self.num_agents = num_agents
        self.num_imposters = num_imposters
        self.phase = "tasks"
        self.reported_body = None
        self.votes = {}
        
        # Define rooms and hallways
        self.rooms = [
            (1, 1, 8, 8, "Cafeteria"),
            (11, 1, 18, 8, "Weapons"),
            (1, 11, 8, 18, "Navigation"),
            (11, 11, 18, 18, "Shields"),
            (9, 3, 10, 6, "Hallway"),
            (9, 13, 10, 16, "Hallway"),      
            (3, 9, 6, 10, "Hallway"),
            (13, 9, 16, 10, "Hallway")      
        ]
        
        # Initialize agents with room-specific tasks
        for _ in range(num_agents):
            agent = Crewmate(self.next_id(), self)
            self.schedule.add(agent)
            room = random.choice(self.rooms[:4])  # Only place in main rooms
            x = random.randint(room[0], room[2])
            y = random.randint(room[1], room[3])
            self.grid.place_agent(agent, (x, y))
            # Assign tasks within the same room
            # agent.tasks = [
            #     Task(f"{room[4]} Task 1", (random.randint(room[0], room[2]), random.randint(room[1], room[3]))),
            #     Task(f"{room[4]} Task 2", (random.randint(room[0], room[2]), random.randint(room[1], room[3])))
            # ]
            
        for _ in range(num_imposters):
            agent = Imposter(self.next_id(), self)
            self.schedule.add(agent)
            room = random.choice(self.rooms[:4])  # Only place in main rooms
            x = random.randint(room[0], room[2])
            y = random.randint(room[1], room[3])
            self.grid.place_agent(agent, (x, y))
            # Fake task in a random room
            fake_room = random.choice(self.rooms[:4])
            # agent.fake_tasks = [Task("Fake Task", (random.randint(fake_room[0], fake_room[2]), random.randint(fake_room[1], fake_room[3])))]
        
        # Initialize room labels
        for i, room in enumerate(self.rooms):
            for x in range(room[0], room[2]+1):
                for y in range(room[1], room[3]+1):
                    label_agent = CellLabelAgent(
                        self.next_id(), 
                        self, 
                        str(i+1),  # Rooms labeled 1-8
                        room
                    )
                    self.grid.place_agent(label_agent, (x, y))

    def is_valid_position(self, pos):
        """Check if position has a CellLabelAgent (valid room/hallway)"""
        x, y = pos
        if not (0 <= x < self.grid.width and 0 <= y < self.grid.height):
            return False
        cell_contents = self.grid.get_cell_list_contents([pos])
        return any(isinstance(agent, CellLabelAgent) for agent in cell_contents)
        
    
    def get_room(self, pos):
        """Return the room name for a given position"""
        x, y = pos
        for room in self.rooms:
            if room[0] <= x <= room[2] and room[1] <= y <= room[3]:
                return room[4]
        return "Hallway"
    
    def discussion_step(self):
        """Process pairs containing the reported body, update votes, and clean up"""
        # Reset votes at start of each discussion
        self.votes = {}
        self.reported_body = None  # Prevent rediscovery
        
        # Find the dead agent
        dead_agent = next((a for a in self.schedule.agents 
                         if a.pos == self.reported_body and not a.alive), None)

        if dead_agent:
            dead_id = dead_agent.unique_id

            # Process crewmate votes (1 vote per crewmate)
            for agent in self.schedule.agents:
                if isinstance(agent, Crewmate) and agent.alive:
                    max_score = -1
                    candidate = None
                    
                    # Find most suspicious pair with dead agent
                    for pair, score in agent.suspicion_pairs.items():
                        if dead_id in pair:
                            alive_member = next((m for m in pair if m != dead_id), None)
                            if alive_member:
                                alive_agent = next((a for a in self.schedule.agents 
                                                 if a.unique_id == alive_member and a.alive), None)
                                if alive_agent and score > max_score:
                                    max_score = score
                                    candidate = alive_member
                    
                    # Cast 1 vote if valid candidate
                    if candidate:
                        self.votes[candidate] = self.votes.get(candidate, 0) + 1

            # Remove dead agent
            self.grid.remove_agent(dead_agent)
            self.schedule.remove(dead_agent)

        # Imposters vote (1 vote each)
        for agent in self.schedule.agents:
            if isinstance(agent, Imposter) and agent.alive:
                crewmates = [a.unique_id for a in self.schedule.agents 
                            if isinstance(a, Crewmate) and a.alive]
                if crewmates:
                    vote = self.random.choice(crewmates)
                    self.votes[vote] = self.votes.get(vote, 0) + 1

        self.phase = "voting"
        self.discussion_time = 5

    def reset_round(self):
        """Reset round and clear voting data"""
        self.phase = "tasks"
        self.reported_body = None
        self.votes = {}  # Now resetting votes each round
        self.discussion_time = 0

    def tally_votes(self):
        """Eject most-voted agent with proper tie-breaking"""
        if not self.votes:
            print("No votes cast! Skipping to next round.")
            self.reset_round()
            return
        
        max_votes = max(self.votes.values())
        candidates = [agent_id for agent_id, votes in self.votes.items() if votes == max_votes]
        
        # If tie, choose randomly among top candidates
        ejected_id = self.random.choice(candidates) if len(candidates) > 1 else candidates[0]
        
        # Find and eject the agent
        for agent in self.schedule.agents:
            if agent.unique_id == ejected_id:
                agent.alive = False
                # Move ejected agent to a corner for visual indication
                self.grid.move_agent(agent, (0, 0))
                print(f"Agent {ejected_id} was ejected with {max_votes} votes!")
                break
        
        self.reset_round()

    def step(self):
        if self.phase == "tasks":
            self.schedule.step()
            # Check if body was reported
            if self.reported_body:
                self.phase = "discussion"
                self.discussion_time = 5  # 5 steps for discussion
        
        elif self.phase == "discussion":
            if self.discussion_time > 0:
                self.discussion_time -= 1
                if self.discussion_time == 0:
                    self.discussion_step()  # Move to voting after discussion
        
        elif self.phase == "voting":
            if self.discussion_time > 0:
                self.discussion_time -= 1
                if self.discussion_time == 0:
                    self.tally_votes()
