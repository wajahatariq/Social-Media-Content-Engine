from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # <--- IMPORT THIS
from .models import ClientInput
from .database import calendars_collection, get_db_status
from .agent import run_content_agent
import logging

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Techware Hub AI Engine")

# --- ADD THIS SECTION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (works for local files & localhost)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (POST, GET, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers
)
# ------------------------

@app.get("/")
async def root():
    db_status = await get_db_status()
    return {"status": "Online", "database": db_status}

@app.post("/api/generate")
async def generate_content(client: ClientInput):
    try:
        logger.info(f"Starting agent for {client.client_name}")
        
        # 1. Run the Agent
        generated_data = await run_content_agent(client)
        
        if "error" in generated_data:
            raise HTTPException(status_code=500, detail="AI failed to generate valid JSON")

        # 2. Structure data
        calendar_doc = {
            "client_name": client.client_name,
            "week_focus": generated_data.get("week_focus", "General Update"),
            "cards": generated_data.get("cards", [])
        }
        
        # 3. Save to MongoDB
        new_calendar = await calendars_collection.insert_one(calendar_doc)
        
        # --- FIX: Convert the ObjectId to a string so FastAPI doesn't crash ---
        calendar_doc["_id"] = str(new_calendar.inserted_id) 
        # ----------------------------------------------------------------------

        return {
            "message": "Content Calendar Generated Successfully",
            "id": str(new_calendar.inserted_id),
            "data": calendar_doc
        }

    except Exception as e:
        logger.error(f"Error: {e}")

        raise HTTPException(status_code=500, detail=str(e))
