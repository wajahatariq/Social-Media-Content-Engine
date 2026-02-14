import os
import json
from typing import TypedDict, Annotated, List
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

# --- 1. Setup Tools & LLM ---
tavily = TavilySearchResults(max_results=3)
llm = ChatGroq(
    temperature=0, 
    model_name="llama-3.3-70b-versatile", 
    api_key=os.getenv("GROQ_API_KEY")
)

# --- 2. Define State ---
class AgentState(TypedDict):
    client_name: str
    industry: str
    notes: str
    research_data: str
    content_plan: str

# --- 3. Define Nodes ---

def research_node(state: AgentState):
    """Searches for trends relevant to the client's industry."""
    print(f"--- RESEARCHING: {state['industry']} ---")
    
    query = f"latest trends and news in {state['industry']} 2024 2025"
    if state['notes']:
        query += f" related to {state['notes']}"
        
    results = tavily.invoke(query)
    
    # Format results simply for the LLM
    context = "\n".join([f"- {r['content']}" for r in results])
    return {"research_data": context}

def drafting_node(state: AgentState):
    """Generates the content calendar based on research."""
    print("--- DRAFTING CONTENT ---")
    
    prompt = f"""
    You are an expert Social Media Strategist for {state['client_name']}.
    
    Here is the latest research on their industry:
    {state['research_data']}
    
    Task: Create a 3-Day Content Calendar based on these trends.
    Output MUST be valid JSON with this exact structure:
    {{
        "week_focus": "Summary of the strategy",
        "cards": [
            {{
                "day": "Day 1",
                "topic": "Headline",
                "caption": "Engaging caption with hashtags",
                "visual_idea": "Description of image/video"
            }},
            ... (for Day 2 and Day 3)
        ]
    }}
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"content_plan": response.content}

# --- 4. Build Graph ---
workflow = StateGraph(AgentState)

workflow.add_node("researcher", research_node)
workflow.add_node("writer", drafting_node)

workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", END)

app_workflow = workflow.compile()

# --- 5. Helper Function to Run ---
async def run_content_agent(client_input):
    inputs = {
        "client_name": client_input.client_name,
        "industry": client_input.industry,
        "notes": client_input.additional_notes,
        "research_data": "",
        "content_plan": ""
    }
    
    result = await app_workflow.ainvoke(inputs)
    
    # Parse the JSON string from the LLM into a Python dict
    try:
        # Sometimes LLMs wrap JSON in markdown blocks, we clean that
        clean_json = result['content_plan'].replace("```json", "").replace("```", "")
        return json.loads(clean_json)
    except Exception as e:
        return {"error": "Failed to parse content", "raw": result['content_plan']}