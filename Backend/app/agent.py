import os
import json
from typing import TypedDict, List
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

tavily = TavilySearchResults(max_results=3)
llm = ChatGroq(
    temperature=0.7, 
    model_name="llama-3.3-70b-versatile", 
    api_key=os.getenv("GROQ_API_KEY")
)

class AgentState(TypedDict):
    client_name: str
    industry: str
    website: str
    phone_number: str
    topics: List[str]
    research_data: str
    raw_concept: str
    visual_idea: str
    final_caption: str

def research_node(state: AgentState):
    query = f"latest trends related to {', '.join(state['topics'])} in {state['industry']} industry"
    results = tavily.invoke(query)
    context = "\n".join([f"- {r['content']}" for r in results])
    return {"research_data": context}

def strategist_node(state: AgentState):
    prompt = f"""
    You are a Content Strategist for {state['client_name']} ({state['industry']}).
    Topic: {state['topics'][0] if state['topics'] else 'General Trends'}
    Research: {state['research_data']}
    
    Task: 
    1. Develop an extremely short core message (strictly 7 to 15 words maximum).
    2. Suggest a strong visual idea.
    
    Output MUST be valid JSON exactly like this:
    {{
        "raw_concept": "Short message here.",
        "visual_idea": "Description of the visual graphic"
    }}
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    
    try:
        clean_json = response.content.replace("```json", "").replace("```", "")
        data = json.loads(clean_json)
        return {
            "raw_concept": data.get("raw_concept", "Elevate your brand with professional services."), 
            "visual_idea": data.get("visual_idea", "Professional brand graphic.")
        }
    except Exception:
        return {"raw_concept": "Elevate your brand with our professional services.", "visual_idea": "Professional brand graphic."}

def copywriter_node(state: AgentState):
    prompt = f"""
    You are an expert Social Media Copywriter for {state['client_name']}.
    
    Take this raw concept from the strategist: {state['raw_concept']}
    
    Write the final social media caption STRICTLY following this exact structural pattern. 
    Do not deviate from this pattern under any circumstances.
    
    [Line 1-2]: The short, punchy sentences based on the concept (3-4 sentences)
    [Line 3]: (Leave this line entirely empty)
    [Line 4]: [Creative CTA phrase]: {state['phone_number']}
    [Line 5]: [Creative CTA phrase]: {state['website']}
    [Line 6]: (Leave this line entirely empty)
    [Line 7]: 5 to 8 highly relevant hashtags starting with #.

    Constraints:
    - NO EMOJIS. You are strictly forbidden from outputting emojis in any part of the text.
    - NO extra introductory or concluding text.
    - Output ONLY the final text intended for the post.
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"final_caption": response.content.strip()}

workflow = StateGraph(AgentState)
workflow.add_node("researcher", research_node)
workflow.add_node("strategist", strategist_node)
workflow.add_node("copywriter", copywriter_node)

workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "strategist")
workflow.add_edge("strategist", "copywriter")
workflow.add_edge("copywriter", END)

app_workflow = workflow.compile()

async def run_content_agent(inputs):
    state_input = {
        "client_name": inputs["client_name"],
        "industry": inputs["industry"],
        "website": inputs["website"],
        "phone_number": inputs.get("phone_number", ""),
        "topics": inputs.get("topics", []),
        "research_data": "",
        "raw_concept": "",
        "visual_idea": "",
        "final_caption": ""
    }
    
    result = await app_workflow.ainvoke(state_input)
    
    return {
        "caption": result["final_caption"],
        "visual_idea": result["visual_idea"]
    }

