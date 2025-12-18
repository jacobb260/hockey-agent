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
    if brace_count != 0:
        return text[start:]
    
    return text[start:end]

def decide_tool(question: str, previous_results: list = None, history_text: str = ""):
    """
    Decide which tool(s) to use based on the question and previous results.
    
    Args:
        question: The user's question
        previous_results: List of previous tool calls and their results
        history_text: Previous conversation history
    """
    previous_context = ""
    if previous_results:
        previous_context = "\nPrevious tool calls and results:\n"
        for i, result in enumerate(previous_results, 1):
            previous_context += f"{i}. Tool: {result['tool']}, Params: {result['params']}\n"
            previous_context += f"   Result summary: {str(result['result'])[:200]}...\n"
    print("Previous context:",previous_context)
    print()
    conversation_context = ""
    if history_text:
        conversation_context = f"\nConversation history:\n{history_text}\n"
    
    prompt = f"""
    You are a hockey data assistant.
    {TOOLS_DESCRIPTION}
    {conversation_context}
    {previous_context}
    
    User question:
    "{question}"
    
    Decide which tool(s) to use. You can return:
    1. A single tool call
    2. Multiple tool calls (as a list) if the question requires data from multiple sources
    3. "done" if previous results are sufficient to answer the question
    4. "none" if no tools can help (or if you can answer from conversation history)
    5. "enough" if the chat history contains the information needed for answering a question
    
    Return ONLY a JSON object with no markdown formatting, no explanation.
    
    Example formats:
    Single tool: {{"tool": "get_player_overview", "player_name": "Sidney Crosby", "season": "20232024"}}
    Multiple tools: {{"tools": [{{"tool": "get_player_overview", "player_name": "Sidney Crosby", "season": "20232024"}}, {{"tool": "get_player_overview", "player_name": "Connor McDavid", "season": "20232024"}}]}}    
    Done: {{"tool": "done", "explanation": "Previous results contain all needed information"}}
    No tool: {{"tool": "none", "explanation": "I can only answer questions related to the NHL and not about fotboll."}}
    Enough, answer with chat history: {{"tool": "enough", "explanation": "Based on Sidney Crosby and Steven Stamkos data from earlier in the conversation, Sidney Crosby had the better season"}}
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


def run_agent(question: str, history_text: str = ""):
    """
    Run the agent with support for multiple tool calls.
    
    Args:
        question: The user's question
        history_text: Previous conversation history
        max_iterations: Maximum number of tool call iterations to prevent infinite loops
    """
    previous_results = []
    
    try:
        decision = decide_tool(question, previous_results, history_text)
        print(f"Raw decision: {decision}")
        
        params = json.loads(decision)
        
        # Check if no tool can help
        if params.get("tool") == "none":
            return params.get("explanation"), "text"
        if params.get("tool") == "enough":
            return params.get("explanation"), "text"
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
        elif "tool" in params and params.get("tool") not in ["done", "none", "enough"]:
            tool_name = params["tool"]
            tool_params = {k: v for k, v in params.items() if k != "tool"}
            
            print(f"  Calling {tool_name} with params: {tool_params}")
            result = execute_tool(tool_name, tool_params)
            
            previous_results.append({
                "tool": tool_name,
                "params": tool_params,
                "result": result
            })
        
        # After executing tools, compile results
        if previous_results:
            # Return the results for formatting
            return previous_results, "data"
        else:
            return "No tools were called to answer the question", "text"
    
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Attempted to parse: {decision}")
        return f"Error parsing decision: {str(e)}", "text"
    except Exception as e:
        print(f"Error in run_agent: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}", "text"

def explain_result(question, table_text):
    prompt = f"""
User question:
{question}

Data:
{table_text}

Explain the result in clear hockey terms. Try to be as concise as possible.
"""
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=350,
            temperature=0.7,
            top_p=0.9,
            top_k=40
        )
    )
    return response.text

# Initialize
genai.configure(api_key=settings.GOOGLE_API_KEY)
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
    """Convert Gradio history to text format."""
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
        
        # Get tool decision and execute
        result, result_type = run_agent(question, history_text=history_text)
        
        # If it's a text response (error or no tool needed)
        if result_type == "text":
            return result
        
        # If we have data results
        if result_type == "data":
            # Combine all results into markdown tables
            all_tables = []
            table_texts = []
            
            for r in result:
                if isinstance(r['result'], pd.DataFrame):
                    table_md = r['result'].to_markdown(index=False)
                    all_tables.append(table_md)
                    table_texts.append(r['result'].to_string(index=False, justify="left"))
                else:
                    all_tables.append(str(r['result']))
                    table_texts.append(str(r['result']))
            
            # Combine all table texts for explanation
            combined_table_text = "\n\n".join([
                f"Tool: {r['tool']}\nParameters: {r['params']}\nResult:\n{table_texts[i]}"
                for i, r in enumerate(result)
            ])
            
            # Get explanation
            explanation = explain_result(question, combined_table_text)
            
            # Format final response - only tables and explanation, no tool names
            tables_section = "\n\n".join(all_tables)
            return f"{tables_section}\n\n{explanation}"
        
        return "Unexpected result type"
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"

demo = gr.ChatInterface(
    fn=chat_interface,
    title="🏒 NHL Assistant",
    description="Ask questions about NHL player statistics. For example: 'Which forwards had the most points the 2023/2024 season?' or 'Who are the top defensemen the 2023/2024 season?' You can also compare players or ask multiple questions at once!",
    examples=[
        "Which forwards was best in 5 against 5?",
        "Compare Sidney Crosby and Connor McDavid in the 2023/2024 season",
        "Top 10 defensemen by points",
        "How did Erik Karlsson perform compared to Cale Makar in 2023/2024?",
    ],
)

if __name__ == "__main__":
    demo.launch()