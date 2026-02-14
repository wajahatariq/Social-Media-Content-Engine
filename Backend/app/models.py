from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ClientInput(BaseModel):
    client_name: str
    website_url: str
    industry: str
    additional_notes: str = Field(default="", description="Any specific campaign goals")

class ContentCard(BaseModel):
    day: str
    topic: str
    caption: str
    visual_idea: str
    status: str = "Draft"  # Draft, Approved, Posted

class ContentCalendar(BaseModel):
    client_name: str
    generated_at: datetime = Field(default_factory=datetime.now)
    week_focus: str
    cards: List[ContentCard]