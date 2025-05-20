from mesa import Model, Agent
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from agents import Crewmate, Imposter
from call_label_agent import CellLabelAgent
import random
from llm_handler import DiscussionManager
from config import OPENAI_API_KEY

class AmongUsModel(Model):
    def __init__(self, width=20, height=20, num_agents=10, num_imposters=1, openai_api_key=OPENAI_API_KEY):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)
        self.schedule = RandomActivation(self)
        self.num_agents = num_agents
        self.num_imposters = num_imposters
        self.phase = "tasks"
        self.reported_body = None
        self.votes = {}
        self.game_over = False  # New game state flag
        self.winner = None  # "Crewmates" or "Imposter"
        self.discussion_manager = DiscussionManager(openai_api_key)
        
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
    
    """
    def discussion_step(self):
        self.votes = {}  # Reset votes
        
        # Find the dead agent using persisted reported_body
        dead_agent = next((a for a in self.schedule.agents 
                        if hasattr(a, 'pos') and a.pos == self.reported_body and not a.alive), None)

        if not dead_agent:
            print("No dead agent found at reported location!")
            self.phase = "voting"
            self.discussion_time = 5
            return

        dead_id = dead_agent.unique_id
        print(f"Processing death of Agent {dead_id}")

        # Get all alive agents first (optimization)
        alive_agents = {a.unique_id: a for a in self.schedule.agents if getattr(a, 'alive', False)}

        # Crewmate voting
        for agent in self.schedule.agents:
            if isinstance(agent, Crewmate) and agent.alive:
                candidates = {}
                
                # Safely process suspicion pairs
                for pair, score in getattr(agent, 'suspicion_pairs', {}).items():
                    try:
                        # Convert frozen set to list
                        pair_members = list(pair)
                        if dead_id in pair_members:
                            alive_member = next((m for m in pair_members if m != dead_id and m in alive_agents), None)
                            if alive_member:
                                # Use score["count"] instead of score directly
                                count = score["count"] if isinstance(score, dict) and "count" in score else 0
                                candidates[alive_member] = candidates.get(alive_member, 0) + count
                    except Exception as e:
                        print(f"Error processing pair {pair}: {e}")
                        continue
                
                # Cast vote if valid candidates exist
                if candidates:
                    vote = max(candidates.items(), key=lambda x: x[1])[0]
                    self.votes[vote] = self.votes.get(vote, 0) + 1
                    print(f"Crewmate {agent.unique_id} votes for {vote}")
                else:
                    print(f"Crewmate {agent.unique_id} has no valid candidates")

        if dead_agent and isinstance(dead_agent, Crewmate):
            dead_agent.close_trace_file()
        # Remove dead agent
        try:
            self.grid.remove_agent(dead_agent)
            self.schedule.remove(dead_agent)
        except Exception as e:
            print(f"Error removing dead agent: {e}")

        # Imposter voting
        crewmate_ids = [uid for uid, a in alive_agents.items() if isinstance(a, Crewmate)]
        for agent in self.schedule.agents:
            if isinstance(agent, Imposter) and agent.alive and crewmate_ids:
                vote = self.random.choice(crewmate_ids)
                self.votes[vote] = self.votes.get(vote, 0) + 1
                print(f"Imposter {agent.unique_id} votes for {vote}")

        self.phase = "voting"
        self.discussion_time = 5
        print(f"Voting tally: {self.votes}")
    """

    def discussion_step(self):
        self.votes = {}

        # Find dead agent with error handling
        try:
            dead_agent = next(a for a in self.schedule.agents 
                            if a.pos == self.reported_body and not a.alive)
        except StopIteration:
            print("No dead agent found! Resetting round.")
            self.reset_round()
            return

        context = {
            'dead_agent_id': dead_agent.unique_id,
            'death_location': self.get_room(dead_agent.pos),
            'dead_suspicions': dead_agent.suspicion_pairs if isinstance(dead_agent, Crewmate) else {},
            'alive_crewmates': [a.unique_id for a in self.schedule.agents 
                              if isinstance(a, Crewmate) and a.alive]
        }

        for agent in self.schedule.agents:
            if not agent.alive:
                continue
            
            try:
                argument = None
                trace_content = ""

                # Read individual trace file
                try:
                    with open(f"agent_{agent.unique_id}_trace.log", "r") as f:
                        trace_content = f.read()[-1000:]  # Get last 1000 characters
                except FileNotFoundError:
                    pass

                # Generate argument based on agent type
                argument = agent.generate_argument(self.discussion_manager, context)

                # Process the argument directly here
                if argument and "suspect" in argument:
                    suspect_str = argument["suspect"].strip()
                    # Extract numerical ID from string
                    suspect_id = int(''.join(filter(str.isdigit, suspect_str)))

                    if any(a.unique_id == suspect_id for a in self.schedule.agents if a.alive):
                        # Calculate vote weight
                        vote_weight = 1
                        if "confidence" in argument:
                            vote_weight += int(argument["confidence"]) // 25

                        # Add heuristic suspicions for crewmates
                        if isinstance(agent, Crewmate):
                            heuristic_weight = len([
                                p for p in agent.suspicion_pairs 
                                if suspect_id in p and context['dead_agent_id'] in p
                            ])
                            vote_weight += heuristic_weight

                        self.votes[suspect_id] = self.votes.get(suspect_id, 0) + vote_weight
                        print(f"Agent {agent.unique_id} votes for {suspect_id}: {argument.get('reason', '')}")

            except ValueError as e:
                print(f"Invalid suspect ID from Agent {agent.unique_id}: {argument.get('suspect')}")
            except Exception as e:
                print(f"Error processing Agent {agent.unique_id}: {str(e)}")

        self.phase = "voting"
        print(f"Final votes: {self.votes}")

    def check_isolated_death(self):
        """Check if death occurred in isolated location"""
        neighbors = self.grid.get_neighbors(self.dead_agent.pos, moore=True, radius=2)
        return len([a for a in neighbors if isinstance(a, (Crewmate, Imposter)) and a.alive]) < 2

    def reset_round(self):
        """Reset round and clear voting data"""
        self.phase = "tasks"
        self.reported_body = None
        self.votes = {}  # Now resetting votes each round
        self.discussion_time = 0
        # Cleanup dead agents (safety net)
        for agent in self.schedule.agents:
            if isinstance(agent, Crewmate) and hasattr(agent, '_trace_file'):
                agent._trace_file.close()
                del agent._trace_file  # Ensures re-initialization next round

        for agent in list(self.schedule.agents):  # Use list() to avoid iteration issues
            if not agent.alive:
                self.grid.remove_agent(agent)
                self.schedule.remove(agent)
            

    def tally_votes(self):
        """Eject most-voted agent with proper tie-breaking"""

        print("Tallying votes...")
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
        if self.game_over:
            return
        
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
                self.tally_votes()
        
        alive_crewmates = sum(1 for a in self.schedule.agents 
                         if isinstance(a, Crewmate) and a.alive)
        alive_imposters = sum(1 for a in self.schedule.agents 
                            if isinstance(a, Imposter) and a.alive)
        
        if alive_imposters == 0:
            self.game_over = True
            self.winner = "Crewmates"
            print("GAME OVER - Crewmates win!")
        elif alive_crewmates == 0:
            self.game_over = True
            self.winner = "Imposter"
            print("GAME OVER - Imposter wins!")