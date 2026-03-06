import os
import json
import random
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage

tavily = TavilySearchResults(max_results=3)
llm = ChatGroq(
    temperature=0.8, 
    model_name="llama-3.3-70b-versatile", 
    api_key=os.getenv("GROQ_API_KEY")
)

async def generate_monthly_calendar(brand_data):
    # 1. Research phase with Dynamic Angles
    angles = [
        "biggest myths and misconceptions",
        "unconventional strategies and bold opinions",
        "hidden secrets and insider tips",
        "future predictions and upcoming shifts",
        "biggest mistakes clients make",
        "behind the scenes and process breakdowns",
        "advanced strategies and deep dives"
    ]
    chosen_angle = random.choice(angles)
    query = f"{chosen_angle} in {brand_data['industry']} industry"
    
    try:
        results = tavily.invoke(query)
        research_context = "\n".join([f"- {r['content']}" for r in results])
    except:
        research_context = "Focus on general professional services, client success, and industry standards."

    # 2. Bulk Generation phase
    prompt = f"""
    You are the Chief Content Officer for {brand_data['name']} ({brand_data['industry']}).
    Your task is to generate a 1-Month Social Media Calendar containing exactly 12 posts.
    
    Industry Research to inspire topics (Current Focus Angle: {chosen_angle}): 
    {research_context}
    
    STRICT TOPIC RULES:
    - NEVER use boring, generic topics like "Trends in...", "AI in...", or "Importance of...".
    - Each of the 12 posts must be highly unique, engaging, and dynamic.
    - Use diverse content pillars: bold opinions, deep-dive tips, myth-busting, client success frameworks, or unconventional advice.
    - Invent a unique, highly specific 'topic' for each post.
    
    For each of the 12 posts, you must invent this unique 'topic' and write a caption. 
    
    CAPTION RULES (STRICT):
    - NO EMOJIS anywhere.
    - No "-" this mark anywhere.
    - Line 1 to 2: 3 to 4 punchy sentences related to the topic with a supporting statement.
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
            "caption": "Line 1\\nLine 2\\n\\nCall today: +1 123 4567\\nVisit us: www.site.com\\n\\n#Tag1 #Tag2"
        }},
        ... (11 more)
    ]
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    try:
        clean_json = response.content.replace("```json", "").replace("```", "").strip()
        posts = json.loads(clean_json)
        # Ensure it is a list
        if not isinstance(posts, list):
            raise ValueError("AI did not return a list")
        return posts[:12] # Guarantee we only take 12
    except Exception as e:
        print(f"JSON Parsing Error: {e}")
        return {"error": "Failed to generate monthly calendar properly."}
