from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from models import CampaignStatus, ProspectStage

class CampaignBase(BaseModel):
    name: str
    config: Optional[Dict[str, Any]] = {}
    targeting_criteria: Optional[Dict[str, Any]] = {}

class CampaignCreate(CampaignBase):
    pass

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[CampaignStatus] = None
    config: Optional[Dict[str, Any]] = None
    targeting_criteria: Optional[Dict[str, Any]] = None

class CampaignResponse(CampaignBase):
    id: UUID
    user_id: UUID
    status: CampaignStatus
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ProspectResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    stage: ProspectStage
    is_active_target: bool
    draft_email: Optional[str] = None
    draft_linkedin_msg: Optional[str] = None
    escalated_to_rep: bool = False
    conversation_history: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class FunnelMetricsResponse(BaseModel):
    discovered: int = 0
    researched: int = 0
    qualified: int = 0
    drafted: int = 0
    drafted_linkedin: int = 0
    contacted: int = 0
    engaged: int = 0
    meeting: int = 0
    opportunity: int = 0
    rejected: int = 0

class AgentLogResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    prospect_id: UUID
    agent_name: str
    action: str
    status: str
    prompt_version: str
    details: Dict[str, Any]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class KnowledgeUpload(BaseModel):
    title: Optional[str] = None
    content: str
    category: Optional[str] = None
    topic: Optional[str] = None
    id: Optional[str] = None

class WebhookReply(BaseModel):
    prospect_id: UUID
    channel: str = "email"
    message_body: str

class PromptVersionCreate(BaseModel):
    agent_type: str
    prompt_text: str

class PromptVersionResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    agent_type: str
    version_number: int
    prompt_text: str
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
