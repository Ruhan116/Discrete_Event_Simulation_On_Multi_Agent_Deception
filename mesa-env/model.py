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
        # Initialize votes only once (persist across rounds)
        if not hasattr(self, 'votes'):
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
                    pairs_to_remove = []

                    temp_votes = self.votes.copy()

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
                                    temp_votes[alive_member] = temp_votes.get(alive_member, 0) + \
                                                              agent.suspicion_pairs[pair]

                            # Mark pair for removal
                            pairs_to_remove.append(pair)
                    
                    max_vote = max(temp_votes.values(), default=0)
                    candidate = [k for k, v in temp_votes.items() if v == max_vote and max_vote > 0]
                    if candidate:
                        self.votes[candidate[0]] = self.votes.get(candidate[0], 0) + 1
                        print(f"Agent {agent.unique_id} votes for {candidate[0]} with max score {max_vote}")

                    # Remove processed pairs
                    for pair in pairs_to_remove:
                        del agent.suspicion_pairs[pair]

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

    def reset_round(self):
        """Reset round WITHOUT clearing votes"""
        self.phase = "tasks"
        self.reported_body = None
        # Do NOT reset self.votes here

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
