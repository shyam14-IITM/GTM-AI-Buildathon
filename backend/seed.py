import asyncio
import uuid
from database import AsyncSessionLocal
from models import Campaign, CampaignStatus, PromptVersion, Prospect, ProspectStage, User
from auth import get_password_hash

async def seed_data():
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        from sqlalchemy import select
        existing = await session.execute(select(Campaign))
        if existing.scalars().first():
            print("Database already seeded. Skipping.")
            return

        print("Seeding Admin User...")
        admin_user = User(
            id=uuid.uuid4(),
            name="Admin User",
            email="admin@company.com",
            hashed_password=get_password_hash("password123")
        )
        session.add(admin_user)
        await session.flush()

        print("Seeding campaigns...")
        
        # 1. Campaign: US SaaS CTO
        c1 = Campaign(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            name="US SaaS CTO",
            status=CampaignStatus.LIVE,
            config={
                "channels": ["email", "linkedin"],
                "daily_limit": 50,
                "assigned_rep": {"name": "Alex Miller", "email": "alex@company.com"}
            },
            targeting_criteria={
                "roles": ["CTO", "VP of Engineering"],
                "geography": "United States",
                "industry": "B2B SaaS",
                "company_size": "50-500"
            }
        )

        # 2. Campaign: India BFSI CIO
        c2 = Campaign(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            name="India BFSI CIO",
            status=CampaignStatus.PAUSED,
            config={
                "channels": ["email", "voice"],
                "daily_limit": 25,
                "assigned_rep": {"name": "Priya Sharma", "email": "priya@company.com"}
            },
            targeting_criteria={
                "roles": ["CIO", "Chief Technology Officer", "Head of IT"],
                "geography": "India",
                "industry": "Banking, Financial Services, Insurance",
                "company_size": "500+"
            }
        )

        # 3. Campaign: Voice AI Founders
        c3 = Campaign(
            id=uuid.uuid4(),
            user_id=admin_user.id,
            name="Voice AI Founders",
            status=CampaignStatus.LIVE,
            config={
                "channels": ["email", "linkedin"],
                "daily_limit": 40,
                "assigned_rep": {"name": "Devin Reed", "email": "devin@company.com"}
            },
            targeting_criteria={
                "roles": ["Founder", "Co-Founder", "CEO"],
                "geography": "Global",
                "industry": "Voice AI & Speech Tech",
                "company_size": "1-50"
            }
        )

        session.add_all([c1, c2, c3])
        await session.flush()

        # Seed Active Prompt Harnesses for Campaign 1
        pv1 = PromptVersion(
            campaign_id=c1.id,
            agent_type="icp_fitment",
            version_number=1,
            prompt_text="Evaluate if the prospect is a technical decision maker at a US SaaS company.",
            is_active=True
        )
        pv2 = PromptVersion(
            campaign_id=c1.id,
            agent_type="personalization",
            version_number=1,
            prompt_text="Write a 3-sentence cold email citing how our tech reduces API latency for SaaS engineering teams.",
            is_active=True
        )

        # Seed Sample Prospects for Campaign 1
        p1 = Prospect(
            campaign_id=c1.id,
            email="sarah.cto@cloudscale.io",
            linkedin_url="https://linkedin.com/in/sarah-cloudscale",
            stage=ProspectStage.QUALIFIED,
            enriched_data={"role": "CTO", "company": "CloudScale", "location": "San Francisco, CA"},
            is_active_target=True
        )
        p2 = Prospect(
            campaign_id=c1.id,
            email="marcus.vp@datastream.com",
            linkedin_url="https://linkedin.com/in/marcus-datastream",
            stage=ProspectStage.CONTACTED,
            enriched_data={"role": "VP of Engineering", "company": "DataStream", "location": "Austin, TX"},
            is_active_target=True
        )

        session.add_all([pv1, pv2, p1, p2])
        await session.commit()
        print("Seeding successfully finished!")

if __name__ == "__main__":
    asyncio.run(seed_data())