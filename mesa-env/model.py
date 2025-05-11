from mesa import Model, Agent
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from agents import Crewmate, Imposter
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
        
        # Initialize agents
        for _ in range(num_agents):
            agent = Crewmate(self.next_id(), self)
            self.schedule.add(agent)
            self.grid.place_agent(agent, self.grid.find_empty())
        
        for _ in range(num_imposters):
            agent = Imposter(self.next_id(), self)
            self.schedule.add(agent)
            self.grid.place_agent(agent, self.grid.find_empty())

    def discussion_step(self):
        """Agents share suspicions."""
        self.votes = {}
        for agent in self.schedule.agents:
            if isinstance(agent, Crewmate) and agent.alive:
                # Vote for most suspected agent
                if agent.suspicions:
                    max_sus = max(agent.suspicions.values())
                    suspects = [k for k, v in agent.suspicions.items() if v == max_sus]
                    vote = random.choice(suspects)
                    self.votes[vote] = self.votes.get(vote, 0) + 1
        self.phase = "voting"

    def tally_votes(self):
        """Eject most-voted agent."""
        if not self.votes:
            print("No votes cast!")
            self.reset_round()
            return
        
        max_votes = max(self.votes.values())
        candidates = [agent_id for agent_id, votes in self.votes.items() if votes == max_votes]
        ejected_id = random.choice(candidates)
        
        for agent in self.schedule.agents:
            if agent.unique_id == ejected_id:
                agent.alive = False
                print(f"Agent {ejected_id} was ejected!")
                break
        
        self.reset_round()

    def reset_round(self):
        """Reset for next round."""
        self.phase = "tasks"
        self.reported_body = None
        self.votes = {}
        
        # Reset suspicions
        for agent in self.schedule.agents:
            if isinstance(agent, Crewmate):
                agent.suspicions = {}

    def step(self):
        if self.phase == "tasks":
            self.schedule.step()
            # Check if body was reported
            if self.reported_body:
                self.phase = "discussion"
        elif self.phase == "discussion":
            self.discussion_step()
        elif self.phase == "voting":
            self.tally_votes()
