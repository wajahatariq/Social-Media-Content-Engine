from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
    """Create a new Brand Card"""
    new_brand = await db.brands.insert_one(brand.model_dump(by_alias=True, exclude=["id"]))
    return {"id": str(new_brand.inserted_id), "name": brand.name}

@app.get("/api/brands")
async def get_brands():
    """Get all Brands"""
    brands = await db.brands.find().to_list(100)
    return brands  # Pydantic/FastAPI handles ObjectId conversion via our Model

@app.get("/api/brands/{brand_id}/posts")
async def get_brand_posts(brand_id: str):
    """Get all posts for a specific brand"""
    posts = await db.posts.find({"brand_id": brand_id}).sort("created_at", -1).to_list(100)
    return posts

# --- CONTENT GENERATION ---

@app.post("/api/schedule")
async def schedule_week(plan: WeeklyPlan):
    """Generate content for specific topics"""
    try:
        # 1. Fetch Brand Info
        brand = await db.brands.find_one({"_id": ObjectId(plan.brand_id)})
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")

        # 2. Run Agent
        agent_input = {
            "client_name": brand['name'],
            "industry": brand['industry'],
            "topics": plan.topics
        }
        
        generated = await run_content_agent(agent_input)
        
        if "error" in generated:
            raise HTTPException(status_code=500, detail="AI Generation Failed")

        # 3. Save Posts to DB
        new_posts = []
        for card in generated.get('cards', []):
            post = SocialPost(
                brand_id=plan.brand_id,
                day=card.get('day', 'Unscheduled'),
                topic=card.get('topic', 'General'),
                caption=card.get('caption', ''),
                visual_idea=card.get('visual_idea', '')
            )
            result = await db.posts.insert_one(post.model_dump(by_alias=True, exclude=["id"]))
            new_posts.append(str(result.inserted_id))

        return {"status": "Success", "generated_count": len(new_posts)}

    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
