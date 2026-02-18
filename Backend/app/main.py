# Backend/app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List  # <--- Make sure this is imported
from .models import Brand, WeeklyPlan, SocialPost
from .database import db, get_db_status
from .agent import run_content_agent
from bson import ObjectId
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kinetix Brand Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "Online", "db": await get_db_status()}

# --- BRAND MANAGEMENT ---

@app.post("/api/brands")
async def create_brand(brand: Brand):
    # We exclude 'id' because MongoDB generates it automatically
    brand_data = brand.model_dump(by_alias=True, exclude=["id"])
    new_brand = await db.brands.insert_one(brand_data)
    return {"id": str(new_brand.inserted_id), "name": brand.name}

# --- FIX IS HERE: Added response_model=List[Brand] ---
@app.get("/api/brands", response_model=List[Brand]) 
async def get_brands():
    brands = await db.brands.find().to_list(100)
    return brands

# --- FIX IS HERE: Added response_model=List[SocialPost] ---
@app.get("/api/brands/{brand_id}/posts", response_model=List[SocialPost])
async def get_brand_posts(brand_id: str):
    posts = await db.posts.find({"brand_id": brand_id}).sort("created_at", -1).to_list(100)
    return posts

# --- CONTENT GENERATION ---

@app.post("/api/schedule")
async def schedule_week(plan: WeeklyPlan):
    try:
        brand = await db.brands.find_one({"_id": ObjectId(plan.brand_id)})
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")

        agent_input = {
            "client_name": brand['name'],
            "industry": brand['industry'],
            "topics": plan.topics
        }
        
        generated = await run_content_agent(agent_input)
        
        if "error" in generated:
            raise HTTPException(status_code=500, detail="AI Generation Failed")

        new_posts_ids = []
        for card in generated.get('cards', []):
            post = SocialPost(
                brand_id=plan.brand_id,
                day=card.get('day', 'Unscheduled'),
                topic=card.get('topic', 'General'),
                caption=card.get('caption', ''),
                visual_idea=card.get('visual_idea', '')
            )
            # Save to DB
            result = await db.posts.insert_one(post.model_dump(by_alias=True, exclude=["id"]))
            new_posts_ids.append(str(result.inserted_id))

        return {"status": "Success", "generated_count": len(new_posts_ids)}

    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
