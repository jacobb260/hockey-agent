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


def extract_json(text):
    """Extract JSON from LLM response, handling markdown and extra text."""
    # Try to find JSON in markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    
    # Try to find JSON object directly
    json_match = re.search(r'\{.*?\}', text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    
    return text

def decide_tool(question: str):
    prompt = f"""
You are a hockey data assistant.
{TOOLS_DESCRIPTION}
User question:
"{question}"

Decide which tool to use and return ONLY a JSON object with no markdown formatting, no explanation.
Example format:
{{"tool": "get_player_overview", "player_name": "Sidney Crosby" ,season": "20232024"}}
"""
    response = model.generate_content(prompt)
    raw_text = response.text.strip()
    
    # Extract JSON from the response
    json_text = extract_json(raw_text)
    
    return json_text

def run_agent(question: str):
    try:
        decision = decide_tool(question)
        print(f"Raw decision: {decision}")
        
        params = json.loads(decision)
        
        if params["tool"] == "get_player_overview":
            result = agentFunctions.get_player_overview(
                player_name = params.get("player_name") ,
                season=params.get("season"),
            )
            return result
        elif params["tool"] == "top_players":
            result = agentFunctions.top_players(
                season= params.get("season"),
                position=params.get("position"),
                metric=params.get("metric"),
                n=params.get("n", 5)
            )
            return result
            
        else:
            return f"Unknown tool: {params.get('tool')}"
    
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Attempted to parse: {decision}")
        return None
    except Exception as e:
        print(f"Error in run_agent: {e}")
        return None

def explain_result(question, table_text):
    prompt = f"""
User question:
{question}

Data:
{table_text}

Explain the result in clear hockey terms in Swedish.
"""
    # När du genererar innehåll
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=200,  # Sätt max antal tokens
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
You can use the following tools, deliver max 150 words:
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
"""

# Main execution
if __name__ == "__main__":
    
    # Test question
    #question = "How good was Sidney Crosby the 2023/2024 season?"
    question = "Vilka forwards var bäst i 5 mot 5 säsongen 2023/2024?"
    
    # Run the agent
    result = run_agent(question)
    
    if result is not None:
        print("\nResult:")
        print(result)
        
        # Explain the result
        table_text = result.to_string(index=False, justify="left")
        explanation = explain_result(question, table_text)
        print("\nExplanation:")
        print(explanation)
    else:
        print("Agent failed to produce results.")