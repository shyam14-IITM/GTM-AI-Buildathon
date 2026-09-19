import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, 
    DateTime, Enum, Index, text
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from database import Base

class CampaignStatus(str, enum.Enum):
    DRAFT = "Draft"
    LIVE = "Live"
    PAUSED = "Paused"
    COMPLETED = "Completed"

class ProspectStage(str, enum.Enum):
    DISCOVERED = "Discovered"
    RESEARCHED = "Researched"
    QUALIFIED = "Qualified"
    DRAFTED = "Drafted"
    CONTACTED = "Contacted"
    ENGAGED = "Engaged"
    MEETING = "Meeting"
    OPPORTUNITY = "Opportunity"
    REJECTED = "Rejected"

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    """
    Represents a human manager in the system with login credentials.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    campaigns = relationship("Campaign", back_populates="user")

class Campaign(Base):
    """
    Represents an outreach campaign with specific targeting and configuration.
    """
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False)
    
    # Stores configuration like daily limits, channels to use, and assigned rep details
    # E.g., {"assigned_rep": {"name": "Alex", "email": "alex@co.com", "daily_limit": 50, "timezone": "EST"}}
    config = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    # Stores targeting rules for the ICP fitment phase
    targeting_criteria = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="campaigns")
    prospects = relationship("Prospect", back_populates="campaign", cascade="all, delete-orphan")
    agent_logs = relationship("AgentLog", back_populates="campaign", cascade="all, delete-orphan")
    prompt_versions = relationship("PromptVersion", back_populates="campaign", cascade="all, delete-orphan")
    knowledge_documents = relationship("KnowledgeDocument", back_populates="campaign", cascade="all, delete-orphan")

    __table_args__ = (
        # Index on status since we'll frequently query for LIVE campaigns
        Index("ix_campaigns_status", "status"),
    )

class Prospect(Base):
    """
    Represents a lead/prospect moving through the outreach funnel.
    """
    __tablename__ = "prospects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    
    email = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    
    stage = Column(Enum(ProspectStage), default=ProspectStage.DISCOVERED, nullable=False)
    
    # Stores raw data from discovery APIs and enriched data during Research phase
    enriched_data = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    
    # A boolean lock to designate if this prospect is actively being targeted
    is_active_target = Column(Boolean, default=True, nullable=False)
    
    # Store the generated draft outreach message
    draft_email = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="prospects")
    agent_logs = relationship("AgentLog", back_populates="prospect", cascade="all, delete-orphan")

    __table_args__ = (
        # Prevent cross-campaign collision: An email or linkedin can only be actively targeted once across the system.
        # This solves the requirement: "ensure a prospect email/LinkedIn isn't actively targeted by two live campaigns simultaneously"
        Index("ix_prospects_unique_active_email", "email", unique=True, postgresql_where=(is_active_target.is_(True))),
        Index("ix_prospects_unique_active_linkedin", "linkedin_url", unique=True, postgresql_where=(is_active_target.is_(True))),
        
        # Optimize filtering by stage and campaign
        Index("ix_prospects_stage", "stage"),
        Index("ix_prospects_campaign_id", "campaign_id"),
    )

class AgentLog(Base):
    """
    Audit trail of all agent actions linked to a prospect and a campaign.
    Designed for chronological fetching by the DronaHQ Control Plane UI.
    """
    __tablename__ = "agent_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    
    # Auditability: Track which prompt version produced this outcome
    prompt_version = Column(String, nullable=False, default="v1.0")
    
    # Name of the agent node performing the action
    agent_name = Column(String, nullable=False)
    
    # E.g., 'ENRICHED', 'EVALUATED_FIT', 'DRAFTED_EMAIL'
    action = Column(String, nullable=False)
    
    # E.g., 'SUCCESS', 'FAILED'
    status = Column(String, nullable=False)
    
    # Detailed reasoning, summary, or payload
    details = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    prospect = relationship("Prospect", back_populates="agent_logs")
    campaign = relationship("Campaign", back_populates="agent_logs")

    __table_args__ = (
        Index("ix_agent_logs_campaign_id", "campaign_id"),
        Index("ix_agent_logs_prospect_id", "prospect_id"),
        Index("ix_agent_logs_created_at", "created_at"),
    )

class PromptVersion(Base):
    """
    Tracks iterations of generative AI prompts per campaign to allow rapid A/B testing and rollbacks.
    """
    __tablename__ = "prompt_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    
    # E.g., 'icp_fitment', 'personalization', 'conversation_handler'
    agent_type = Column(String, nullable=False) 
    
    version_number = Column(Integer, nullable=False)
    prompt_text = Column(String, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="prompt_versions")

    __table_args__ = (
        # Ensure only one active prompt per AGENT TYPE within a campaign
        Index("ix_prompt_versions_active_per_campaign_agent", "campaign_id", "agent_type", unique=True, postgresql_where=(is_active.is_(True))),
    )

class KnowledgeDocument(Base):
    """
    Documents or case studies converted into embeddings for isolated campaign RAG.
    """
    __tablename__ = "knowledge_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    
    # Store vector embeddings for pgvector
    # 384 is the dimension for the standard free HuggingFace all-MiniLM-L6-v2 model
    embedding = Column(Vector(384))
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="knowledge_documents")

    __table_args__ = (
        Index("ix_knowledge_documents_campaign_id", "campaign_id"),
    )

class GlobalSuppression(Base):
    """
    Do-not-contact list. Agents must check this table before sending any outreach.
    """
    __tablename__ = "global_suppression"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=True, index=True)
    linkedin_url = Column(String, unique=True, nullable=True, index=True)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
