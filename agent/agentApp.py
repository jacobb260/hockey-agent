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
from config import settings
from agentFunctions import agentFunctions
import gradio as gr

# Sätt UTF-8 encoding för stdout/stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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

def decide_tool(question: str, history_text: str = ""):
    prompt = f"""
You are a hockey data assistant.
{TOOLS_DESCRIPTION}

Conversation so far (may be empty):
{history_text}

User question:
"{question}"

Decide which tool to use and return ONLY a JSON object with no markdown formatting, no explanation.
Example format:
{{"tool": "get_player_overview", "player_name": "Sidney Crosby" ,season": "20232024"}}
If no tools can answer the question, give a brief explantion of why. For example:
{{"tool": "none", "explanation": "I can only answer questions related to the NHL and not about fotboll."}}
You can also answer the question based ob the conversation history. For example:
{{"tool": "none", "explanation": "Based on Sidney Crosby and Steven Stamkos data from earlier in the conversation, Sidney Crosby had the better season"}}
"""
    response = model.generate_content(prompt)
    raw_text = response.text.strip()
    
    # Extract JSON from the response
    json_text = extract_json(raw_text)
    
    return json_text

def run_agent(question: str, history_text: str = ""):
    try:
        decision = decide_tool(question, history_text)
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
        elif params["tool"] == "get_team_overview":
            result = agentFunctions.get_team_overview(
                teamName=params.get("teamName"),
                season=params.get("season")
            )
            return result
        elif params["tool"] == "none":
            return params.get("explanation")
            
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
   Use when the user asks NHL team related questions.
   Parameters:
   -teamName: The full name of the team.
   -season: Which season. The format is YYYYYYYY, 20232024 for example
"""

def history_to_text(history, max_turns=6):
    #Code generated by ChatGPT
    if not history:
        return ""
    # take the N latest turns
    h = history[-max_turns:]

    # tuple-format: [(user, bot), ...]
    if isinstance(h[0], (list, tuple)) and len(h[0]) == 2:
        lines = []
        for u, a in h:
            if u: lines.append(f"User: {u}")
            if a: lines.append(f"Assistant: {a}")
        return "\n".join(lines)

    # dict-format: [{"role":"user","content":"..."}, ...]
    if isinstance(h[0], dict):
        lines = []
        for m in h:
            role = m.get("role", "user")
            content = m.get("content", "")
            lines.append(f"{role.capitalize()}: {content}")
        return "\n".join(lines)

    return str(h)

def chat_interface(question, history): 
    try:
        history_text = history_to_text(history, max_turns=6)
        #print(history_text)
        # Get tool decision
        result = run_agent(question, history_text=history_text)
    
        #If no tool could be used
        if type(result) is str:
            return result

        elif result is not None:
            print("\nResult:")
            print(result)
            table_md = result.to_markdown(index=False)
            # Explain the result
            table_text = result.to_string(index=False, justify="left")
            explanation = explain_result(question, table_text)
            return f"{table_md}\n\n{explanation}"
        else:
            return "Agent failed to produce results."
    
    except Exception as e:
        return f"Error: {str(e)}"

demo = gr.ChatInterface(
    fn=chat_interface,
    title="🏒 NHL Assistant",
    description="Ask questions about NHL player statistics. For example: 'Which forwrads had the most points the 2023/2024 season?' or 'Who are the top defensemen the 2023/2024 season?'",
    examples=[
        "Which forwards was best in 5 against 5?",
        "Which forwards had the most points?",
        "Top 10 defensemen by points",
    ],
)

if __name__ == "__main__":
    demo.launch()

