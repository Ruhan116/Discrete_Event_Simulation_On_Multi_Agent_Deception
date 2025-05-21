import json
import google.generativeai as genai
import random

class GeminiHandler:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')  # Updated to more reliable model
    
    def query_llm(self, prompt, system_message=None):
        """Simplified LLM query with robust error handling"""
        try:
            full_prompt = f"{system_message}\n\n{prompt}" if system_message else prompt
            response = self.model.generate_content(
                f"Respond strictly in JSON format. {full_prompt}",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=200,
                )
            )
            return response.text
        except Exception as e:
            print(f"Gemini API error: {e}")
            return '{"error": "API failed"}'

class DiscussionManagerGemini:
    def __init__(self, api_key):
        self.llm = GeminiHandler(api_key)
    
    def generate_crewmate_prompt(self, agent_id, trace_content, context):
        """Clear prompt with explicit JSON requirements"""
        return f"""As Crewmate Agent {agent_id}, analyze this data and respond ONLY in valid JSON:
        {{
            "observations": "{trace_content[-1000:]}",
            "dead_agent": {context['dead_agent_id']},
            "location": "{context['death_location']}",
            "suspicions": {context['dead_suspicions']}
        }}
        Identify suspicious patterns. Your response MUST be in this exact format:
        {{
            "suspect": "Agent X", 
            "reason": "...", 
            "confidence": 0-100
        }}"""

    def generate_imposter_prompt(self, agent_id, trace_content, context):
        """Structured prompt for imposters"""
        return f"""As Imposter Agent {agent_id}, create deception using this data (respond ONLY in JSON):
        {{
            "alibi": "{trace_content[-500:]}",
            "location": "{context['death_location']}",
            "crewmates": {context['alive_crewmates']}
        }}
        Frame someone plausibly. Response MUST be:
        {{
            "suspect": "Agent Y", 
            "reason": "...", 
            "confidence": 0-100
        }}"""

    def parse_response(self, response):
        """Bulletproof JSON parsing"""
        try:
            # Remove all markdown formatting
            clean_json = response.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except json.JSONDecodeError:
            print(f"Failed to parse Gemini response: {response[:200]}...")
            return {"suspect": f"Agent {random.randint(1,10)}", "reason": "Parse error", "confidence": 50}
        except Exception as e:
            print(f"Unexpected parse error: {e}")
            return None