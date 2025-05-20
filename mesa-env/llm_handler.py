# llm_handler.py
import json
import requests

class GrokHandler:
    def __init__(self, api_key):
        self.api_url = "https://api.groq.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def query_grok(self, prompt, system_message=None):
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "messages": messages,
            "model": "mixtral-8x7b-32768",
            "temperature": 0.7,
            "max_tokens": 150
        }
        
        try:
            response = requests.post(self.api_url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            print(f"Grok API error: {e}")
            return None

class DiscussionManager:
    def __init__(self, api_key):
        self.grok = GrokHandler(api_key)
        self.step_logs = {}  # {step: [pairs]}
    
    def add_step_log(self, step, pairs):
        """Store step-wise positional data"""
        self.step_logs[step] = pairs
    
    def _analyze_logs(self, agent_id=None, max_steps=5):
        """Analyze recent logs for patterns"""
        analysis = {
            "frequent_pairs": {},
            "common_rooms": {},
            "agent_paths": defaultdict(list)
        }
        
        # Analyze last N steps
        recent_steps = sorted(self.step_logs.keys())[-max_steps:]
        for step in recent_steps:
            for pair in self.step_logs[step]:
                agents = sorted(pair)
                room = pair[2]
                
                # Track pairs
                pair_key = f"Agents {agents[0]} & {agents[1]}"
                analysis["frequent_pairs"][pair_key] = analysis["frequent_pairs"].get(pair_key, 0) + 1
                
                # Track rooms
                analysis["common_rooms"][room] = analysis["common_rooms"].get(room, 0) + 1
                
                # Track individual paths
                for agent in agents[:2]:
                    analysis["agent_paths"][agent].append({
                        "step": step,
                        "room": room,
                        "with": agents[1] if agent == agents[0] else agents[0]
                    })
        
        # Add agent-specific insights if requested
        if agent_id:
            agent_log = analysis["agent_paths"].get(f"Agent {agent_id}", [])
            analysis["agent_summary"] = {
                "recent_rooms": Counter([log["room"] for log in agent_log]).most_common(3),
                "common_companions": Counter([log["with"] for log in agent_log]).most_common(2)
            }
        
        return analysis
    
    def generate_crewmate_prompt(self, agent_id, observations, dead_id, location, suspicion_data):
        prompt = f"""As Crewmate Agent {agent_id}, analyze:
        - Last observations: {observations}
        - Victim ID: Agent {dead_id}
        - Death location: {location}
        - Suspicious pairs: {suspicion_data}
        Who is most likely guilty? Respond with JSON: {{"suspect": "Agent X", "reason": "..."}}"""
        
        return prompt

    def generate_imposter_prompt(self, agent_id, death_location, circumstances):
        prompt = f"""As Imposter Agent {agent_id}, create accusation considering:
        - Body found in {death_location} ({circumstances})
        Suggest plausible suspect. Respond with JSON: {{"suspect": "Agent Y", "reason": "..."}}"""
        
        return prompt
    
    def parse_response(self, response):
        try:
            return json.loads(response)
        except:
            return None