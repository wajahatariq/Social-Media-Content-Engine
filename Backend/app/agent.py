import os
import json
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage

tavily = TavilySearchResults(max_results=3)
llm = ChatGroq(
    temperature=0.7, 
    model_name="llama-3.3-70b-versatile", 
    api_key=os.getenv("GROQ_API_KEY")
)

async def generate_monthly_calendar(brand_data):
    # 1. Research phase
    query = f"latest trends and news in {brand_data['industry']} industry"
    try:
        results = tavily.invoke(query)
        research_context = "\n".join([f"- {r['content']}" for r in results])
    except:
        research_context = "Focus on general professional services, client success, and industry standards."

    # 2. Bulk Generation phase
    prompt = f"""
    You are the Chief Content Officer for {brand_data['name']} ({brand_data['industry']}).
    Your task is to generate a 1-Month Social Media Calendar containing exactly 12 posts.
    
    Industry Research to inspire topics: 
    {research_context}
    
    For each of the 12 posts, you must invent a unique, specific 'topic' and write a caption. 
    
    CAPTION RULES (STRICT):
    - NO EMOJIS anywhere.
    - Line 1: A short, punchy sentence (7 to 10 words maximum).
    - Line 2: A short supporting statement (5 to 8 words maximum).
    - Line 3: (Leave this line empty)
    - Line 4: [Creative CTA phrase]: {brand_data['phone_number']}
    - Line 5: [Creative CTA phrase]: {brand_data['website']}
    - Line 6: (Leave this line empty)
    - Line 7: 5 to 8 highly relevant hashtags starting with #.

    Output ONLY a valid JSON array of 12 objects, exactly like this format:
    [
        {{
            "topic": "Name of the specific topic",
            "visual_idea": "Description of what the graphic designer should draw/create.",
            "caption": "Line 1\\nLine 2\\n\\nCall today: +1 123-4567\\nVisit us: www.site.com\\n\\n#Tag1 #Tag2"
        }},
        ... (11 more)
    ]
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    try:
        clean_json = response.content.replace("```json", "").replace("```", "").strip()
        posts = json.loads(clean_json)
        # Ensure it's a list
        if not isinstance(posts, list):
            raise ValueError("AI did not return a list")
        return posts[:12] # Guarantee we only take 12
    except Exception as e:
        print(f"JSON Parsing Error: {e}")
        return {"error": "Failed to generate monthly calendar properly."}
