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
            print(f"Agent {agent.unique_id} created at {agent.pos}")
        
        for _ in range(num_imposters):
            agent = Imposter(self.next_id(), self)
            self.schedule.add(agent)
            self.grid.place_agent(agent, self.grid.find_empty())
            print(f"Imposter {agent.unique_id} created at {agent.pos}")

    
    def discussion_step(self):
        """Process pairs containing the reported body, update votes, and clean up"""
        # Reset votes at start of each discussion
        self.votes = {}
        
        # Find the dead agent from reported body position
        dead_agent = None
        for agent in self.schedule.agents:
            if agent.pos == self.reported_body and not agent.alive:
                dead_agent = agent
                break

        if dead_agent:
            dead_id = dead_agent.unique_id

            # Process all agents' suspicion pairs containing the dead agent
            for agent in self.schedule.agents:
                if isinstance(agent, Crewmate) and agent.alive:
                    # Check each pair containing the dead agent
                    for pair in agent.suspicion_pairs:
                        if dead_id in pair:
                            members = list(pair)
                            alive_member = next((m for m in members if m != dead_id), None)
                            
                            if alive_member:
                                # Find if alive member is still living
                                alive_agent = next((a for a in self.schedule.agents 
                                                if a.unique_id == alive_member and a.alive), None)
                                
                                if alive_agent:
                                    # Update vote count with pair score
                                    self.votes[alive_member] = self.votes.get(alive_member, 0) + \
                                                            agent.suspicion_pairs[pair]

            # Remove dead agent from grid and schedule
            self.grid.remove_agent(dead_agent)
            self.schedule.remove(dead_agent)

        # Imposters vote for random crewmates (excluding themselves)
        for agent in self.schedule.agents:
            if isinstance(agent, Imposter) and agent.alive:
                crewmates = [
                    a.unique_id for a in self.schedule.agents
                    if isinstance(a, Crewmate) and a.alive and a.unique_id != agent.unique_id
                ]
                if crewmates:
                    vote = self.random.choice(crewmates)
                    self.votes[vote] = self.votes.get(vote, 0) + 1
                    print(f"Imposter {agent.unique_id} votes for {vote}")

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
