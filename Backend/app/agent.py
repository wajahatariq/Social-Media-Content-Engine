import os
import json
from typing import TypedDict, List, Optional
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
    topics: Optional[List[str]]  # <--- Added this to hold specific topics
    research_data: str
    content_plan: str

# --- 3. Define Nodes ---

def research_node(state: AgentState):
    """Searches for trends relevant to the client's industry."""
    print(f"--- RESEARCHING: {state['industry']} ---")
    
    # If we have specific topics, research those specifically
    if state.get('topics'):
        query = f"news and trends related to {', '.join(state['topics'])} in {state['industry']} industry"
    else:
        query = f"latest trends and news in {state['industry']} 2025"
        
    results = tavily.invoke(query)
    context = "\n".join([f"- {r['content']}" for r in results])
    return {"research_data": context}

def drafting_node(state: AgentState):
    """Generates the content calendar based on research."""
    print("--- DRAFTING CONTENT ---")
    
    topics = state.get('topics', [])
    
    # MODE A: Strict Topic Schedule (Trello Style)
    if topics:
        prompt = f"""
        You are a Social Media Manager for {state['client_name']}.
        
        STRICT TASK: Create exactly {len(topics)} posts based on these specific topics provided by the user:
        {json.dumps(topics)}
        
        Industry Context & Research:
        {state['industry']}
        {state['research_data']}
        
        Output MUST be valid JSON with this exact structure:
        {{
            "cards": [
                {{
                    "day": "Day 1",
                    "topic": "{topics[0] if topics else 'Topic'}",
                    "caption": "Engaging caption...",
                    "visual_idea": "Description of visual..."
                }}
                ... (one card per topic)
            ]
        }}
        """
    # MODE B: Auto-Pilot (General Trends)
    else:
        prompt = f"""
        You are an expert Social Media Strategist for {state['client_name']}.
        Research: {state['research_data']}
        
        Task: Create a 3-Day Content Calendar based on trends.
        Output MUST be valid JSON:
        {{
            "cards": [ ... ]
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
async def run_content_agent(inputs):
    # Ensure all state keys exist
    state_input = {
        "client_name": inputs["client_name"],
        "industry": inputs["industry"],
        "topics": inputs.get("topics", []),
        "research_data": "",
        "content_plan": ""
    }
    
    result = await app_workflow.ainvoke(state_input)
    
    try:
        clean_json = result['content_plan'].replace("```json", "").replace("```", "")
        return json.loads(clean_json)
    except Exception as e:
        return {"error": "Failed to parse content", "raw": result['content_plan']}
