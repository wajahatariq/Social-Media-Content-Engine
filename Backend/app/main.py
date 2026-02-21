from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from .models import Brand, SocialPost, ImageUpload
from .database import db, get_db_status
from .agent import run_content_agent
from bson import ObjectId
import logging
import httpx
import base64
from datetime import datetime

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

@app.post("/api/brands")
async def create_brand(brand: Brand):
    res = await db.brands.insert_one(brand.model_dump(by_alias=True, exclude=["id"]))
    return {"id": str(res.inserted_id), "name": brand.name}

@app.get("/api/brands", response_model=List[Brand])
async def get_brands():
    return await db.brands.find().to_list(100)

@app.get("/api/brands/{brand_id}/posts", response_model=List[SocialPost])
async def get_posts(brand_id: str):
    return await db.posts.find({"brand_id": brand_id}).to_list(1000)

@app.post("/api/posts/plan")
async def plan_post(post: SocialPost):
    post.status = "Planned"
    res = await db.posts.insert_one(post.model_dump(by_alias=True, exclude=["id"]))
    return {"id": str(res.inserted_id), "status": "Planned"}

@app.post("/api/posts/{post_id}/generate")
async def generate_single_post(post_id: str):
    try:
        post = await db.posts.find_one({"_id": ObjectId(post_id)})
        brand = await db.brands.find_one({"_id": ObjectId(post['brand_id'])})
        
        agent_input = {
            "client_name": brand['name'],
            "industry": brand['industry'],
            "topics": [post['topic']] 
        }
        generated = await run_content_agent(agent_input)
        
        if "error" in generated:
            raise HTTPException(500, "AI Generation Failed")

        card = generated['cards'][0]
        update_data = {
            "caption": card['caption'],
            "visual_idea": card['visual_idea'],
            "status": "Generated"
        }
        
        await db.posts.update_one({"_id": ObjectId(post_id)}, {"$set": update_data})
        return {**post, **update_data, "id": post_id, "_id": str(post["_id"])} 

    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(500, str(e))

@app.post("/api/posts/{post_id}/approve")
async def approve_post(post_id: str, upload: ImageUpload):
    try:
        update_data = {
            "image_base64": upload.image_base64,
            "is_approved": True,
            "status": "Approved"
        }
        await db.posts.update_one({"_id": ObjectId(post_id)}, {"$set": update_data})
        return {"status": "Approved and queued for auto-posting"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/cron/publish")
async def auto_publish_posts():
    """This endpoint is called automatically by Vercel every 5 minutes."""
    now = datetime.now()
    posts_to_publish = await db.posts.find({
        "status": "Approved", 
        "scheduled_date": {"$lte": now}
    }).to_list(100)

    results = []
    async with httpx.AsyncClient() as client:
        for post in posts_to_publish:
            brand = await db.brands.find_one({"_id": ObjectId(post["brand_id"])})
            if not brand or not brand.get("facebook_access_token"):
                continue

            image_data = post["image_base64"]
            if "," in image_data:
                image_data = image_data.split(",")[1]

            image_bytes = base64.b64decode(image_data)
            url = f"https://graph.facebook.com/v19.0/{brand['facebook_page_id']}/photos"
            files = {'source': ('image.jpg', image_bytes, 'image/jpeg')}
            data = {
                'message': post.get("caption", ""),
                'access_token': brand['facebook_access_token']
            }

            response = await client.post(url, data=data, files=files)

            if response.status_code == 200:
                await db.posts.delete_one({"_id": post["_id"]})
                results.append({"post_id": str(post["_id"]), "status": "success"})
            else:
                results.append({"post_id": str(post["_id"]), "status": "failed", "error": response.text})

    return {"processed": len(results), "details": results}
