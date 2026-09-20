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
            prompt_text="Evaluate if the prospect is a technical decision maker at a US SaaS company. Output a structured decision containing 'status' (Qualified or Rejected) and a brief 'reasoning'.",
            is_active=True
        )
        pv2 = PromptVersion(
            campaign_id=c1.id,
            agent_type="email_drafter",
            version_number=1,
            prompt_text="Write a 3-sentence cold email citing how our tech reduces API latency for SaaS engineering teams. Be engaging and highlight the value proposition.",
            is_active=True
        )
        
        from models import KnowledgeDocument
        from graph.nodes import embeddings
        
        # Seed Knowledge for RAG using the highly detailed JSON payload
        payloads = [
          {
            "title": "core_value_proposition",
            "content": "Product: Autonomous SDR Platform. We automate the entire outbound sales motion across email, LinkedIn, and voice calls. Unlike basic sequencers, our platform acts as an intelligent agent that independently researches prospects, writes personalized hooks based on real-time company news, and autonomously handles scheduling."
          },
          {
            "title": "saas_cto_outbound_metrics",
            "content": "Case Study - TechFlow (B2B SaaS): TechFlow deployed the Autonomous SDR to target mid-market CTOs. Result: Outbound pipeline velocity increased by 3.5x, rep hours spent researching fell by 80%, and demo booking rates climbed from 2.1% to 8.4% within 60 days."
          },
          {
            "title": "already_use_competitor",
            "content": "If the prospect says they already use a competitor (e.g., Apollo, Outreach), acknowledge their current setup. Counter by explaining that our Autonomous SDR platform does not replace their database; it acts as the intelligence layer on top of it. Ask: 'Are you open to a 10-minute chat to see how we automate the manual follow-ups your current tool requires?'"
          },
          {
            "title": "too_expensive_budget",
            "content": "If the prospect raises budget concerns or says it is too expensive, clarify our pricing model. State: 'Unlike traditional seat-based software, we price based on performance and qualified meetings booked.' Offer to send the 'Acme Corp Case Study' which demonstrates a 40% reduction in overall Customer Acquisition Cost (CAC) within two months."
          }
        ]
        
        kd_objects = []
        for p in payloads:
            vector = embeddings.embed_query(p["content"])
            kd_objects.append(
                KnowledgeDocument(
                    campaign_id=c1.id,
                    title=p["title"],
                    content=p["content"],
                    embedding=vector
                )
            )

        # Seed Sample Prospects for Campaign 1
        p1 = Prospect(
            campaign_id=c1.id,
            email="sarah.cto@cloudscale.io",
            linkedin_url="https://linkedin.com/in/sarah-cloudscale",
            stage=ProspectStage.DISCOVERED,
            enriched_data={"role": "CTO", "company": "CloudScale", "location": "San Francisco, CA"},
            is_active_target=True
        )
        p2 = Prospect(
            campaign_id=c1.id,
            email="marcus.vp@datastream.com",
            linkedin_url="https://linkedin.com/in/marcus-datastream",
            stage=ProspectStage.DISCOVERED,
            enriched_data={"role": "VP of Engineering", "company": "DataStream", "location": "Austin, TX"},
            is_active_target=True
        )

        session.add_all([pv1, pv2, p1, p2])
        session.add_all(kd_objects)
        await session.commit()
        print("Seeding successfully finished!")

if __name__ == "__main__":
    asyncio.run(seed_data())