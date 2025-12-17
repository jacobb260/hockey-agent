import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import google.generativeai as genai
import json
import pandas as pd
import re
import sys
import io

# Sätt UTF-8 encoding för stdout/stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from config import settings
from agentFunctions import agentFunctions


def extract_json(text: str) -> str:
    """Extract and validate JSON from text, handling incomplete responses."""
    # Remove markdown code blocks if present
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    # Try to find JSON object
    start = text.find('{')
    if start == -1:
        return text
    
    # Find the matching closing brace
    brace_count = 0
    end = start
    in_string = False
    escape_next = False
    
    for i in range(start, len(text)):
        char = text[i]
        
        if escape_next:
            escape_next = False
            continue
            
        if char == '\\':
            escape_next = True
            continue
            
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
            
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
    
    # If we didn't find a complete JSON, return what we have
    # and let the caller handle the error
    if brace_count != 0:
        return text[start:]
    
    return text[start:end]

def decide_tool(question: str, previous_results: list = None):
    """
    Decide which tool(s) to use based on the question and previous results.
    
    Args:
        question: The user's question
        previous_results: List of previous tool calls and their results
    """
    previous_context = ""
    if previous_results:
        previous_context = "\nPrevious tool calls and results:\n"
        for i, result in enumerate(previous_results, 1):
            previous_context += f"{i}. Tool: {result['tool']}, Params: {result['params']}\n"
            previous_context += f"   Result summary: {str(result['result'])[:200]}...\n"
    
    prompt = f"""
    You are a hockey data assistant.
    {TOOLS_DESCRIPTION}
    {previous_context}
    
    User question:
    "{question}"
    
    Decide which tool(s) to use. You can return:
    1. A single tool call
    2. Multiple tool calls (as a list) if the question requires data from multiple sources
    3. "done" if previous results are sufficient to answer the question
    4. "none" if no tools can help
    
    Return ONLY a JSON object with no markdown formatting, no explanation.
    
    Example formats:
    Single tool: {{"tool": "get_player_overview", "player_name": "Sidney Crosby", "season": "20232024"}}
    Multiple tools: {{"tools": [{{"tool": "get_player_overview", "player_name": "Sidney Crosby", "season": "20232024"}}, {{"tool": "get_player_overview", "player_name": "Connor McDavid", "season": "20232024"}}]}}
    Done: {{"tool": "done", "explanation": "Previous results contain all needed information"}}
    No tool: {{"tool": "none", "explanation": "I can only answer questions related to the NHL and not about fotboll."}}
    """
    
    response = model.generate_content(prompt)
    raw_text = response.text.strip()
    
    # Extract JSON from the response
    json_text = extract_json(raw_text)
    
    return json_text


def execute_tool(tool_name: str, params: dict):
    """Execute a single tool with given parameters."""
    if tool_name == "get_player_overview":
        return agentFunctions.get_player_overview(
            player_name=params.get("player_name"),
            season=params.get("season"),
        )
    elif tool_name == "top_players":
        return agentFunctions.top_players(
            season=params.get("season"),
            position=params.get("position"),
            metric=params.get("metric"),
            n=params.get("n", 5)
        )
    elif tool_name == "get_team_overview":
        return agentFunctions.get_team_overview(
            teamName=params.get("teamName"),
            season=params.get("season")
        )
    else:
        return f"Unknown tool: {tool_name}"


def run_agent(question: str, max_iterations: int = 5):
    """
    Run the agent with support for multiple tool calls.
    
    Args:
        question: The user's question
        max_iterations: Maximum number of tool call iterations to prevent infinite loops
    """
    previous_results = []
    
    try:
        for iteration in range(max_iterations):
            print(f"\n--- Iteration {iteration + 1} ---")
            
            decision = decide_tool(question, previous_results)
            print(f"Raw decision: {decision}")
            
            params = json.loads(decision)
            
            # Check if we're done
            if params.get("tool") == "done":
                print("Agent decided it has enough information")
                break
            
            # Check if no tool can help
            if params.get("tool") == "none":
                return params.get("explanation")
            
            # Handle multiple tools
            if "tools" in params:
                print(f"Executing {len(params['tools'])} tools...")
                for tool_call in params["tools"]:
                    tool_name = tool_call.get("tool")
                    tool_params = {k: v for k, v in tool_call.items() if k != "tool"}
                    
                    print(f"  Calling {tool_name} with params: {tool_params}")
                    result = execute_tool(tool_name, tool_params)
                    
                    previous_results.append({
                        "tool": tool_name,
                        "params": tool_params,
                        "result": result
                    })
            
            # Handle single tool
            elif "tool" in params:
                tool_name = params["tool"]
                tool_params = {k: v for k, v in params.items() if k != "tool"}
                
                print(f"  Calling {tool_name} with params: {tool_params}")
                result = execute_tool(tool_name, tool_params)
                
                previous_results.append({
                    "tool": tool_name,
                    "params": tool_params,
                    "result": result
                })
            
            else:
                return "Invalid response format from decision model"
        
        # After all iterations, compile all results into a single table_text
        if previous_results:
            table_text = "\n\n".join([
                f"Tool: {r['tool']}\nParameters: {r['params']}\nResult:\n{r['result']}"
                for r in previous_results
            ])
            
            # Use your existing explain_result function
            return explain_result(question, table_text)
        else:
            return "No tools were called to answer the question"
    
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Attempted to parse: {decision}")
        return None
    except Exception as e:
        print(f"Error in run_agent: {e}")
        import traceback
        traceback.print_exc()
        return None
    
def explain_result(question, table_text):
    prompt = f"""
User question:
{question}

Data:
{table_text}

Explain the result in clear hockey terms. Try to be as concise as possible.
"""
    # När du genererar innehåll
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=350,  # Sätt max antal tokens
            temperature=0.7,         # Valfritt: kreativitet (0.0-1.0)
            top_p=0.9,              # Valfritt: sampling
            top_k=40                # Valfritt: sampling
        )
    )
    return response.text

# Initialize
genai.configure(api_key= settings.GOOGLE_API_KEY)
model = genai.GenerativeModel("gemma-3-27b-it")
#print("Tillgängliga Gemini-modeller:\n")
"""
for model in genai.list_models():
    print(f"Modell: {model.name}")
    print(f"  Display name: {model.display_name}")
    print(f"  Stödjer generateContent: {model.supported_generation_methods}")
    print(f"  Input token limit: {model.input_token_limit}")
    print(f"  Output token limit: {model.output_token_limit}")
    print()
"""
# Tool descriptions
TOOLS_DESCRIPTION = """
You can use the following tools for answer questions related to the NHL
1. get_player_overview:
   Use when the user asks for season overview of a player. For example when the user asks "How good is Jesper Fast this season"
   Or when the user want a comparison of two players
   Parameters:
   - player_name: The full (first name and last name) name of the player
   - season: Which season. The format is YYYYYYYY, 20232024 for example
2. top_players:
   Use when the user asks for best players, rankings, leaders.
   Parameters:
   -season: Which season. The format is YYYYYYYY, 20232024 for example
   - position: "F" (forwards), "D" (defensemen), "C" (center), "L" (left wing), "R" (right wing), or null for all
   - metric: one of ["points", "points_per_game", "ev_points", "goals"]
     * "ev_points" means even-strength points (5 mot 5)
   - n: number of players to return
3. get_team_overview:
   Use when the user asks questions related to a specific NHL team.
   Parameters:
   -teamName: The full name of the team.
   -season: Which season. The format is YYYYYYYY, 20232024 for example
"""

# Main execution
if __name__ == "__main__":
    
    # Test question
    question = "How good was Sidney Crosby compared to Erik Karlsson in the 2023/2024 season?"
    #question = "What team is leading right now, also is Connor McDavid performing well?"
    #question = "Vilka forwards var bäst i 5 mot 5 säsongen 2023/2024?"
    #question = "Vad blir det för väder idag?"
    #question = "Hur många poäng har Colorado Avalanche i NHL 20252026?"

    
    # Run the agent
    result = run_agent(question)
    
    #If no tool could be used
    if type(result) is str:
        print(result)

    elif result is not None:
        print("\nResult:")
        print(result)
        
        # Explain the result
        table_text = result.to_string(index=False, justify="left")
        explanation = explain_result(question, table_text)
        print("\nExplanation:")
        print(explanation)
    else:
        print("Agent failed to produce results.")