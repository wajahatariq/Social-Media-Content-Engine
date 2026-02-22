from pydantic import BaseModel, Field, BeforeValidator, ConfigDict
from typing import List, Optional, Annotated
from datetime import datetime

PyObjectId = Annotated[str, BeforeValidator(str)]

class Brand(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    industry: str
    website: str = ""       # <--- Add = "" here
    phone_number: str = ""  # <--- Add = "" here
    website: str
    phone_number: str
    tone_voice: str = "Professional"
    facebook_page_id: Optional[str] = None
    facebook_access_token: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

class SocialPost(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    brand_id: str
    topic: str
    scheduled_date: datetime
    caption: Optional[str] = None
    visual_idea: Optional[str] = None
    image_base64: Optional[str] = None  
    is_approved: bool = False           
    status: str = "Generated" 
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

class ApproveUpload(BaseModel):
    image_base64: str
    scheduled_date: datetime

class DraftRequest(BaseModel):
    brand_id: str
    topic: str

