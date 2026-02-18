from pydantic import BaseModel, Field, BeforeValidator
from typing import List, Optional, Annotated
from datetime import datetime

# --- MongoDB ID Helper ---
# This converts MongoDB's ObjectId to a string automatically
PyObjectId = Annotated[str, BeforeValidator(str)]

class Brand(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    industry: str
    website: str
    tone_voice: str = "Professional"
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

class WeeklyPlan(BaseModel):
    brand_id: str
    week_focus: str  # e.g., "Product Launch Week"
    topics: List[str] # ["Feature X", "Customer Story Y", "Tips Z"]

class SocialPost(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    brand_id: str
    day: str
    topic: str
    caption: str
    visual_idea: str
    status: str = "Draft"
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
