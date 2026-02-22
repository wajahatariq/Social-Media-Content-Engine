from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel  # <--- ADD THIS EXACT LINE
from typing import List
from .models import Brand, SocialPost, ApproveUpload, AutoMonthRequest
from .database import db, get_db_status
from .agent import generate_monthly_calendar
from bson import ObjectId
import logging
import httpx
import base64
from datetime import datetime, timedelta

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

@app.delete("/api/brands/{brand_id}")
async def delete_brand(brand_id: str):
    try:
        await db.posts.delete_many({"brand_id": brand_id})
        res = await db.brands.delete_one({"_id": ObjectId(brand_id)})
        if res.deleted_count == 0:
            raise HTTPException(404, "Brand not found")
        return {"status": "Deleted successfully"}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/brands/{brand_id}/posts", response_model=List[SocialPost])
async def get_posts(brand_id: str):
    return await db.posts.find({"brand_id": brand_id}).to_list(1000)

@app.post("/api/posts/generate_month")
async def generate_month(req: AutoMonthRequest):
    try:
        brand = await db.brands.find_one({"_id": ObjectId(req.brand_id)})
        if not brand:
            raise HTTPException(404, "Brand not found")

        # Call the bulk AI agent
        generated_posts = await generate_monthly_calendar({
            "name": brand['name'],
            "industry": brand['industry'],
            "website": brand.get('website', ''),
            "phone_number": brand.get('phone_number', '')
        })

        if isinstance(generated_posts, dict) and "error" in generated_posts:
            raise HTTPException(500, "AI Generation Failed. Try again.")

        # Schedule logic: 3 posts per week for 4 weeks (Days 1, 3, 5, 8, 10, 12...)
        day_offsets = [1, 3, 5, 8, 10, 12, 15, 17, 19, 22, 24, 26]
        base_date = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        
        saved_posts = []
        for i, post_data in enumerate(generated_posts):
            if i >= 12: break # Failsafe
            
            scheduled_time = base_date + timedelta(days=day_offsets[i])
            
            new_post = SocialPost(
                brand_id=req.brand_id,
                topic=post_data.get('topic', 'Brand Highlight'),
                scheduled_date=scheduled_time,
                caption=post_data.get('caption', ''),
                visual_idea=post_data.get('visual_idea', ''),
                status="Generated"
            )
            
            res = await db.posts.insert_one(new_post.model_dump(by_alias=True, exclude=["id"]))
            saved_posts.append(str(res.inserted_id))

        return {"status": "success", "generated_count": len(saved_posts)}

    except Exception as e:
        logger.error(f"Bulk Error: {e}")
        raise HTTPException(500, str(e))

@app.post("/api/posts/{post_id}/approve")
async def approve_post(post_id: str, upload: ApproveUpload):
    try:
        update_data = {
            "image_base64": upload.image_base64,
            "scheduled_date": upload.scheduled_date,
            "is_approved": True,
            "status": "Approved"
        }
        await db.posts.update_one({"_id": ObjectId(post_id)}, {"$set": update_data})
        return {"status": "Approved and scheduled"}
    except Exception as e:
        raise HTTPException(500, str(e))

# --- NEW: Edit Scheduled Time Endpoint ---
class UpdateScheduleRequest(BaseModel):
    scheduled_date: datetime

@app.patch("/api/posts/{post_id}/schedule")
async def update_post_schedule(post_id: str, req: UpdateScheduleRequest):
    try:
        await db.posts.update_one(
            {"_id": ObjectId(post_id)}, 
            {"$set": {"scheduled_date": req.scheduled_date}}
        )
        return {"status": "Schedule updated"}
    except Exception as e:
        raise HTTPException(500, str(e))
        
@app.get("/api/cron/publish")
async def auto_publish_posts():
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


