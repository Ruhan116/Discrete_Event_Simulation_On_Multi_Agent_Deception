from mesa import Model, Agent
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from agents import Crewmate, Imposter
from call_label_agent import CellLabelAgent
from llm_benchmark import OpenAILoader, GeminiLoader
import random
import json
import os
from dotenv import load_dotenv
import re

class AmongUsModel(Model):
    def __init__(self, width=20, height=20, num_agents=10, num_imposters=1, llm_type="gemini", openai_model="gemini-2.0-flash"):
        super().__init__()
        # Load environment variables
        load_dotenv()
        
        # Initialize LLM
        if llm_type == "openai":
            self.llm = OpenAILoader(os.getenv("OPENAI_KEY"), model=openai_model)
        elif llm_type == "gemini":
            self.llm = GeminiLoader(os.getenv("GEMINI_KEY"))
        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}")
        
        # Load standardized prompts
        with open("prompts.json") as f:
            self.prompts = json.load(f)

        self.grid = MultiGrid(width, height, torus=False)
        self.schedule = RandomActivation(self)
        self.num_agents = num_agents
        self.num_imposters = num_imposters
        self.phase = "tasks"
        self.reported_body = None
        self.votes = {}
        self.game_over = False  # New game state flag
        self.winner = None  # "Crewmates" or "Imposter"
        self.running = True  # New game state flag
        
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

    def generate_argument(self, agent, context):
        role = "imposter" if isinstance(agent, Imposter) else "crewmate"
        try:
            # Format the prompt template with safe defaults
            prompt_template = self.prompts[role]["user"].format(
                trace_content=context.get('trace_content', ''),
                dead_agent_id=context.get('dead_agent_id', 'Unknown'),
                death_location=context.get('death_location', 'Unknown'),
                dead_suspicions=context.get('dead_suspicions', {}),
                alive_crewmates=context.get('alive_crewmates', [])
            )
            system_msg = self.prompts[role]["system"]
            
            response = self.llm.query_llm(prompt_template, system_msg)
            parsed_response = self.llm.parse_response(response)
            if parsed_response:
                print(f"Agent {agent.unique_id} argument: {parsed_response}")
            return parsed_response
        except Exception as e:
            return None

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
        """Process discussion phase with LLM integration"""
        self.votes = {}

        # Find dead agent with error handling
        try:
            dead_agent = next(a for a in self.schedule.agents 
                            if a.pos == self.reported_body and not a.alive)
        except StopIteration:
            print("No dead agent found! Resetting round.")
            self.reset_round()
            return

        # Capture death location BEFORE removal
        death_location = self.get_room(dead_agent.pos)

        # Remove dead agent properly
        try:
            self.grid.remove_agent(dead_agent)
            self.schedule.remove(dead_agent)
            if isinstance(dead_agent, Crewmate):
                dead_agent.close_trace_file()
        except Exception as e:
            print(f"Error removing dead agent: {e}")

        # Prepare context for LLM
        context = {
            'dead_agent_id': dead_agent.unique_id,
            'death_location': death_location,
            'dead_suspicions': dead_agent.suspicion_pairs if isinstance(dead_agent, Crewmate) else {},
            'alive_crewmates': [a.unique_id for a in self.schedule.agents 
                              if isinstance(a, Crewmate) and a.alive]
        }

        # Collect arguments and votes from all alive agents
        for agent in self.schedule.agents:
            if not agent.alive:
                continue
            
            try:
                # Read individual trace file
                trace_content = ""
                try:
                    with open(f"agent_{agent.unique_id}_trace.log", "r") as f:
                        trace_content = f.read()[-1000:]  # Get last 1000 characters
                except FileNotFoundError:
                    pass

                # Add trace content to context
                context['trace_content'] = trace_content

                # Generate argument using the new method
                argument = self.generate_argument(agent, context)

                # Process the argument
                if argument and "suspect" in argument:
                    print(f"Raw argument from Agent {agent.unique_id}: {argument}")  # Debug raw argument
                    # Handle numeric extraction safely
                    suspect_str = str(argument["suspect"]).strip()
                    print(f"Suspect string before processing: '{suspect_str}'")  # Debug suspect string
                    try:
                        match = re.search(r'\d+', suspect_str)
                        if match:
                            suspect_id = int(match.group())
                            print(f"Found suspect ID: {suspect_id}")  # Debug found ID
                        else:
                            print(f"No number found in suspect string: '{suspect_str}'")  # Debug no match
                            suspect_id = -1
                    except Exception as e:
                        print(f"Error extracting suspect ID: {str(e)}")  # Debug extraction error
                        suspect_id = -1

                    if suspect_id != -1 and any(a.unique_id == suspect_id for a in self.schedule.agents if a.alive):
                        self.votes[suspect_id] = self.votes.get(suspect_id, 0) + 1
                        print(f"Agent {agent.unique_id} reasoning: {argument.get('reason', 'No reason provided')}")
                    else:
                        print(f"Invalid suspect ID from Agent {agent.unique_id}: {suspect_str} (ID: {suspect_id})")

            except Exception as e:
                print(f"Error processing agent {agent.unique_id}: {str(e)}")
                print(f"Full error details: {type(e).__name__}: {str(e)}")  # Debug full error
                import traceback
                print(f"Traceback: {traceback.format_exc()}")  # Debug traceback

        self.phase = "voting"
        self.discussion_time = 5
        print(f"Voting tally: {self.votes}")

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
            self.running = False  # Stop the simulation
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
                self.discussion_time -= 1
                if self.discussion_time == 0:
                    self.tally_votes()
        
        # Game state check
        alive_crewmates = sum(1 for a in self.schedule.agents 
                         if isinstance(a, Crewmate) and a.alive)
        alive_imposters = sum(1 for a in self.schedule.agents 
                            if isinstance(a, Imposter) and a.alive)

        # 1) Win by elimination
        if alive_imposters == 0:
            self.game_over = True
            self.running = False  # Stop the simulation
            self.winner = "Crewmates"
            print("GAME OVER - Crewmates win by eliminating all imposters!")
            return
        if alive_crewmates == 0:
            self.game_over = True
            self.running = False  # Stop the simulation
            self.winner = "Imposter"
            print("GAME OVER - Imposter wins by eliminating all crewmates!")
            return

        # 2) Win by task completion
        all_tasks_done = all(
            task.complete
            for agent in self.schedule.agents
            if isinstance(agent, Crewmate) and agent.alive
            for task in agent.tasks
        )
        if all_tasks_done:
            self.game_over = True
            self.running = False  # Stop the simulation
            self.winner = "Crewmates"
            print("GAME OVER - Crewmates win! All tasks have been completed.")
            return