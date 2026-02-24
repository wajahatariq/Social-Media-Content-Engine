from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from .models import Brand, SocialPost, ApproveUpload, AutoMonthRequest
from .database import db, get_db_status
from .agent import generate_monthly_calendar
from bson import ObjectId
import logging
import httpx
import base64
from datetime import datetime, timedelta
import pytz

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

        # 1. Call the AI agent to get the raw ideas
        generated_posts = await generate_monthly_calendar({
            "name": brand['name'],
            "industry": brand['industry'],
            "website": brand.get('website', ''),
            "phone_number": brand.get('phone_number', '')
        })

        if isinstance(generated_posts, dict) and "error" in generated_posts:
            raise HTTPException(500, "AI Generation Failed. Try again.")
            
        # 2. Setup Timezone (Pakistan Standard Time)
        pkt = pytz.timezone('Asia/Karachi')
        day_offsets = [1, 3, 5, 8, 10, 12, 15, 17, 19, 22, 24, 26]
        
        # Get current time in PKT and lock the start time to 3:00 PM
        base_date = datetime.now(pkt)
        
        brand_name = brand.get("name", "the brand")
        website = brand.get("website", f"www.{brand_name.replace(' ', '').lower()}.com")
        
        saved_posts = []
        
        # 3. SINGLE LOOP: Process and Save
        for i, post_data in enumerate(generated_posts):
            if i >= 12: break # Failsafe
            
            # Calculate the specific date for this post
            scheduled_time = base_date + timedelta(days=day_offsets[i])
            scheduled_time = scheduled_time.replace(tzinfo=None)
            raw_visual_direction = post_data.get('visual_idea', '')

            # 4. Construct the automated God-Tier Prompt
            ai_prompt = (
                f"Generate a highly creative and visually striking social media post image for '{brand_name}'.\n\n"
                f"CORE VISUAL CONCEPT: {raw_visual_direction}\n\n"
                f"CREATIVE DIRECTION (CRITICAL): Do not use generic, standard, or repetitive layouts. "
                f"You must explore dynamic angles, fresh compositions, and imaginative visual metaphors specifically tailored to the core concept above. "
                f"The artwork must look entirely distinct and unique compared to previous posts, using creative element placement to stand out.\n\n"
                f"NON-NEGOTIABLE BRANDING RULES:\n"
                f"1. COLOR SCHEME: Match the color palette exactly to the '{brand_name}' logo provided in this chat.\n"
                f"2. LOGO PLACEMENT: Place the official '{brand_name}' logo clearly in the top right corner.\n"
                f"3. WEBSITE PLACEMENT: Render the website text '{website}' with flawless typography perfectly centered at the bottom.\n"
                f"4. BRAND VIBE: The overarching aesthetic (corporate, comic, minimal, etc.) must match the brand's identity while remaining highly creative.\n\n"
                f"Post Size: 1080x1080"
            )

            # 5. Create the post object
            new_post = SocialPost(
                brand_id=req.brand_id,
                topic=post_data.get('topic', 'Brand Highlight'),
                scheduled_date=scheduled_time,
                caption=post_data.get('caption', ''),
                visual_idea=raw_visual_direction,
                ai_prompt=ai_prompt,
                status="Generated"
            )
            
            # 6. Save to MongoDB
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
    # 1. Get the exact current time in Pakistan Standard Time
    pkt = pytz.timezone('Asia/Karachi')
    
    # 2. Strip the timezone so it matches the "Floating Time" in your database
    now_pkt = datetime.now(pkt).replace(tzinfo=None)
    
    # 3. Query the database using the matched PKT time
    posts_to_publish = await db.posts.find({
        "status": "Approved", 
        "scheduled_date": {"$lte": now_pkt}
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
                await db.posts.update_one(
                    {"_id": post["_id"]},
                    {"$set": {"status": "Published", "is_published": True}}
                )
                results.append({"post_id": str(post["_id"]), "status": "success"})
            else:
                results.append({"post_id": str(post["_id"]), "status": "failed", "error": response.text})

    return {"processed": len(results), "details": results}

