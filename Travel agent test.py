AGENT_SYSTEM_PROMPT = """
You are an intelligent travel assistant. Your task is to analyze user requests and solve problems step by step using available tools.

# Available Tools:
- `get_weather(city: str)`: Query real-time weather information for a specified city.
- `get_attraction(city: str, weather: str)`: Search and recommend tourist attractions based on city and weather conditions.

# Action Format:
Your response must strictly follow the format below. First describe your thought process, then the specific action to execute. Output only one Thought-Action pair per response:
Thought: [Your thought process and next plan]
Action: [The tool you want to call, in the format function_name(arg_name="arg_value")]

# Task Completion:
When you have collected enough information to answer the user's final question, you must output the final answer using `finish(answer="...")` after the `Action:` field.

Let's begin!
"""

import requests

def get_weather(city: str) -> str:
    """
    Query real-time weather information by calling wttr.in API.
    """
    url = f"https://wttr.in/{city}?format=j1"
    
    try:
        response = requests.get(url)
        response.raise_for_status() 
        data = response.json()
        
        current_condition = data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']
        
        return f"Current weather in {city}: {weather_desc}, Temperature: {temp_c}°C"
        
    except requests.exceptions.RequestException as e:
        return f"Error: Network issue while querying weather - {e}"
    except (KeyError, IndexError) as e:
        return f"Error: Failed to parse weather data, city name may be invalid - {e}"
    
import os
from tavily import TavilyClient

def get_attraction(city: str, weather: str) -> str:
    """
    Search and return optimized tourist attraction recommendations based on city and weather using Tavily Search API.
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY environment variable not configured."

    tavily = TavilyClient(api_key=api_key)
    
    query = f"Best tourist attractions to visit in '{city}' during '{weather}' weather and reasons why"
    
    try:
        response = tavily.search(query=query, search_depth="basic", include_answer=True)
        
        if response.get("answer"):
            return response["answer"]
        
        formatted_results = []
        for result in response.get("results", []):
            formatted_results.append(f"- {result['title']}: {result['content']}")
        
        if not formatted_results:
             return "Sorry, no relevant tourist attraction recommendations were found."

        return "Based on search results, here are the findings:\n" + "\n".join(formatted_results)

    except Exception as e:
        return f"Error: Problem occurred while executing Tavily search - {e}"
    
available_tools = {
    "get_weather": get_weather,
    "get_attraction": get_attraction,
}


from openai import OpenAI

class OpenAICompatibleClient:
    """
    A client for calling LLM services compatible with OpenAI interface.
    """
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, prompt: str, system_prompt: str) -> str:
        """Call LLM API to generate responses."""
        print("Calling language model...")
        try:
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': prompt}
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False
            )
            answer = response.choices[0].message.content
            print("Language model response successful.")
            return answer
        except Exception as e:
            print(f"Error occurred while calling LLM API: {e}")
            return "Error: Failed to call language model service."

        
import re

API_KEY = "ms-5c56cf4f-7457-45e8-9ab4-3af1f3e089bb"
BASE_URL = "https://api-inference.modelscope.cn/v1"
MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"
TAVILY_API_KEY="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"
os.environ['TAVILY_API_KEY'] = TAVILY_API_KEY

llm = OpenAICompatibleClient(
    model=MODEL_ID,
    api_key=API_KEY,
    base_url=BASE_URL
)

user_prompt = "Hello, please check today's weather in New York, then recommend a suitable tourist attraction based on the weather."
prompt_history = [f"User request: {user_prompt}"]

print(f"User input: {user_prompt}\n" + "="*40)

for i in range(5):
    print(f"--- Loop {i+1} ---\n")
    
    full_prompt = "\n".join(prompt_history)
    
    llm_output = llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)
    match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
    if match:
        truncated = match.group(1).strip()
        if truncated != llm_output.strip():
            llm_output = truncated
            print("Truncated excess Thought-Action pairs")
    print(f"Model output:\n{llm_output}\n")
    prompt_history.append(llm_output)
    
    action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
    if not action_match:
        print("Parse error: Action not found in model output.")
        break
    action_str = action_match.group(1).strip()

    if action_str.startswith("finish"):
        final_answer = re.search(r'finish\(answer="(.*)"\)', action_str).group(1)
        print(f"Task completed, final answer: {final_answer}")
        break
    
    tool_name = re.search(r"(\w+)\(", action_str).group(1)
    args_str = re.search(r"\((.*)\)", action_str).group(1)
    kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

    if tool_name in available_tools:
        observation = available_tools[tool_name](**kwargs)
    else:
        observation = f"Error: Undefined tool '{tool_name}'"

    observation_str = f"Observation: {observation}"
    print(f"{observation_str}\n" + "="*40)
    prompt_history.append(observation_str)