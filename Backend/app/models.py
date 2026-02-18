# Backend/app/models.py
from pydantic import BaseModel, Field, BeforeValidator, ConfigDict
from typing import List, Optional, Annotated
from datetime import datetime

# --- 1. Robust MongoDB ID Helper ---
# This tells Pydantic: "If you see an ObjectId, turn it into a string before doing anything else."
PyObjectId = Annotated[str, BeforeValidator(str)]

class Brand(BaseModel):
    # The alias="_id" is critical because Mongo uses "_id" but Python uses "id"
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    industry: str
    website: str
    tone_voice: str = "Professional"
    created_at: datetime = Field(default_factory=datetime.now)

    # This config block is required for Pydantic V2 to handle MongoDB data
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

class WeeklyPlan(BaseModel):
    brand_id: str
    week_focus: str
    topics: List[str]

class SocialPost(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    brand_id: str
    day: str
    topic: str
    caption: str
    visual_idea: str
    status: str = "Draft"
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
