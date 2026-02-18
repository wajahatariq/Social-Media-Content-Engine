from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from .models import Brand, SocialPost
from .database import db, get_db_status
from .agent import run_content_agent
from bson import ObjectId
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kinetix Pro")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- BRANDS ---
@app.post("/api/brands")
async def create_brand(brand: Brand):
    res = await db.brands.insert_one(brand.model_dump(by_alias=True, exclude=["id"]))
    return {"id": str(res.inserted_id), "name": brand.name}

@app.get("/api/brands", response_model=List[Brand])
async def get_brands():
    return await db.brands.find().to_list(100)

# --- POSTS ---
@app.get("/api/brands/{brand_id}/posts", response_model=List[SocialPost])
async def get_posts(brand_id: str):
    return await db.posts.find({"brand_id": brand_id}).to_list(1000)

@app.post("/api/posts/plan")
async def plan_post(post: SocialPost):
    """Step 1: Save a slot on the calendar (Topic + Date only)"""
    post.status = "Planned"
    res = await db.posts.insert_one(post.model_dump(by_alias=True, exclude=["id"]))
    return {"id": str(res.inserted_id), "status": "Planned"}

@app.post("/api/posts/{post_id}/generate")
async def generate_single_post(post_id: str):
    """Step 2: Run AI for this specific slot"""
    try:
        # 1. Get the planned post
        post = await db.posts.find_one({"_id": ObjectId(post_id)})
        brand = await db.brands.find_one({"_id": ObjectId(post['brand_id'])})
        
        # 2. Run Agent (Targeted for this single topic)
        agent_input = {
            "client_name": brand['name'],
            "industry": brand['industry'],
            "topics": [post['topic']] # <--- Only research this one topic
        }
        generated = await run_content_agent(agent_input)
        
        if "error" in generated:
            raise HTTPException(500, "AI Generation Failed")

        # 3. Update the DB with the result
        card = generated['cards'][0]
        update_data = {
            "caption": card['caption'],
            "visual_idea": card['visual_idea'],
            "status": "Generated"
        }
        
        await db.posts.update_one({"_id": ObjectId(post_id)}, {"$set": update_data})
        return {**post, **update_data, "id": post_id, "_id": str(post["_id"])} # Return full updated obj

    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(500, str(e))
