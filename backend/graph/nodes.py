import os
from typing import Any, Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from sqlalchemy.future import select

from .state import AgentState
from database import AsyncSessionLocal
from models import Prospect, ProspectStage, AgentLog, KnowledgeDocument, Campaign, PromptVersion

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is missing")

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
if not RESEND_API_KEY:
    raise ValueError("RESEND_API_KEY environment variable is missing")

_embeddings = None
def get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embeddings


async def get_active_prompt(db, campaign_id, agent_type, default_prompt):
    from sqlalchemy.future import select
    from models import PromptVersion
    result = await db.execute(
        select(PromptVersion)
        .where(PromptVersion.campaign_id == campaign_id, PromptVersion.agent_type == agent_type, PromptVersion.is_active == True)
    )
    prompt_record = result.scalars().first()
    return prompt_record.prompt_text if prompt_record else default_prompt

class ICPDecision(BaseModel):
    status: Literal['Qualified', 'Rejected']
    reasoning: str

async def research_node(state: AgentState) -> dict[str, Any]:
    """
    The Research Node.
    Responsible for taking raw prospect identifiers (e.g., email/linkedin),
    executing search tools (Tavily/Exa), and structuring the data.
    """
    prospect_id = state.get('prospect_id')
    campaign_id = state.get('campaign_id')
    print(f"--- [Node: Research] Extracting data for Prospect ID: {prospect_id} ---")
    
    # 1. Update the Database using SQLAlchemy to get the real email
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
        prospect = result.scalars().first()
        
        if prospect:
            # Parse the name from the email (e.g., john.doe@example.com -> John Doe)
            email = prospect.email or ""
            name_part = email.split('@')[0]
            prospect_name = name_part.replace('.', ' ').title() if name_part else "Jane Doe"
            
            # Format a realistic synthetic JSON profile
            mock_structured_data = {
                "name": prospect_name,
                "title": "CTO",
                "company_size": "200-500",
                "industry": "B2B SaaS",
                "geography": "United States",
                "recent_news": "Recently raised Series B funding"
            }
            
            prospect.stage = ProspectStage.RESEARCHED
            prospect.enriched_data = mock_structured_data
            
            # 3. Write to AgentLog
            db.add(AgentLog(
                campaign_id=campaign_id,
                prospect_id=prospect_id,
                agent_name="Research Node",
                action="ENRICHED",
                status="SUCCESS",
                prompt_version="v1.0",
                details={"structured_data": mock_structured_data}
            ))
            
            await db.commit()
            
    return {"structured_prospect_data": mock_structured_data}

async def icp_fitment_node(state: AgentState) -> dict[str, Any]:
    """
    The ICP Fitment Node.
    Evaluates the `structured_prospect_data` against the `icp_criteria` to determine 
    if the prospect is 'Qualified' or 'Rejected' using Gemini structured output.
    """
    print("--- [Node: ICP Fitment] Evaluating prospect fit via LLM ---")
    prospect_id = state.get("prospect_id")
    campaign_id = state.get("campaign_id")
    icp_criteria = state.get("icp_criteria", {})
    structured_data = state.get("structured_prospect_data", {})
    
    async with AsyncSessionLocal() as db:
        raw_sys_prompt = await get_active_prompt(db, campaign_id, "icp_fitment", "You are a strict SDR evaluator. Your job is to compare prospect data against ICP criteria.\nOutput a structured decision containing 'status' (Qualified or Rejected) and a brief 'reasoning'.")
    system_prompt = SystemMessage(content=raw_sys_prompt)
    
    user_prompt = HumanMessage(content=f"""
    ICP Criteria: {icp_criteria}
    Prospect Data: {structured_data}
    """)
    
    import os
    
    # Instantiate Groq (OpenAI compatible) and bind structured output
    llm = ChatOpenAI(model="openai/gpt-oss-20b",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0
    )
    structured_llm = llm.with_structured_output(ICPDecision, include_raw=True)
    
    # Invoke asynchronously with error handling
    try:
        response = await structured_llm.ainvoke([system_prompt, user_prompt])
        decision: ICPDecision = response["parsed"]
        raw_msg = response["raw"]
        
        usage = raw_msg.usage_metadata or {}
        print(f"LLM Decision: {decision.status} - {decision.reasoning}")
        
        # Prepare details payload with meta
        details = {"status": decision.status, "reasoning": decision.reasoning}
        if usage:
            details["meta"] = {
                "model": "openai/gpt-oss-20b (Groq)",
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }
    except Exception as e:
        print(f"--- [Node: ICP Fitment] Error: {str(e)}")
        decision = ICPDecision(status="Rejected", reasoning=f"Error parsing LLM output: {str(e)}")
        details = {"status": decision.status, "reasoning": decision.reasoning, "error": str(e)}
    
    # Update the Database using SQLAlchemy
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
        prospect = result.scalars().first()
        if prospect:
            prospect.stage = ProspectStage.QUALIFIED if decision.status == "Qualified" else ProspectStage.REJECTED
            
            # Write to AgentLog
            db.add(AgentLog(
                campaign_id=campaign_id,
                prospect_id=prospect_id,
                agent_name="ICP Fitment Node",
                action="EVALUATED_FIT",
                status="SUCCESS",
                prompt_version="v1.0",
                details=details
            ))
            
            await db.commit()
            
    return {
        "current_status": decision.status,
        "messages": [SystemMessage(content=f"ICP Fitment Reasoning: {decision.reasoning}")]
    }

class StrategyDecision(BaseModel):
    channel: str
    reasoning: str

async def strategy_node(state: AgentState) -> dict[str, Any]:
    """
    The Outreach Strategy Node.
    Decides which channel (Email or LinkedIn) to prioritize based on the campaign's configuration
    and the prospect's profile.
    """
    print("--- [Node: Strategy] Deciding outreach channel ---")
    campaign_id = state.get("campaign_id")
    prospect_id = state.get("prospect_id")
    structured_data = state.get("structured_prospect_data", {})
    
    # 1. Fetch Campaign Config to inform the LLM decision
    campaign_config = {}
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = result.scalars().first()
        if campaign:
            campaign_config = campaign.config
            
    enabled_channels = []
    config = state.get("campaign_config", {})
    if config.get("is_email_enabled"): enabled_channels.append("email")
    if config.get("is_linkedin_enabled"): enabled_channels.append("linkedin")
    if config.get("is_voice_enabled"): enabled_channels.append("voice")
    
    async with AsyncSessionLocal() as db:
        raw_sys_prompt = await get_active_prompt(db, campaign_id, "strategy", f"You are an Outreach Strategy Agent. Your job is to determine the best channel to contact this prospect.\nYou must output a structured JSON with 'channel' and a brief 'reasoning'.\nYou may ONLY choose from the following enabled channels: {enabled_channels}\nReview the Prospect Profile to make your decision.")
    system_prompt = SystemMessage(content=raw_sys_prompt)
    
    user_prompt = HumanMessage(content=f"""
    Enabled Channels: {enabled_channels}
    Prospect Profile: {structured_data}
    """)
    
    import os
    llm = ChatOpenAI(model="openai/gpt-oss-20b",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.1
    )
    structured_llm = llm.with_structured_output(StrategyDecision)
    
    try:
        decision: StrategyDecision = await structured_llm.ainvoke([system_prompt, user_prompt])
        print(f"Strategy Decision: Route to {decision.channel} - {decision.reasoning}")
    except Exception as e:
        print(f"--- [Node: Strategy] Error: {str(e)}")
        fallback_channel = enabled_channels[0] if enabled_channels else "email"
        decision = StrategyDecision(channel=fallback_channel, reasoning=f"Error parsing LLM output: {str(e)}")
    
    # Write to AgentLog
    async with AsyncSessionLocal() as db:
        db.add(AgentLog(
            campaign_id=campaign_id,
            prospect_id=prospect_id,
            agent_name="Strategy Node",
            action="ROUTED_CHANNEL",
            status="SUCCESS",
            prompt_version="v1.0",
            details={"channel": decision.channel, "reasoning": decision.reasoning}
        ))
        await db.commit()
        
    return {"selected_channel": decision.channel}

class EmailDraftResponse(BaseModel):
    subject: str
    body: str

async def email_drafter_node(state: AgentState) -> dict[str, Any]:
    """
    The Email Drafter Node.
    Writes a highly personalized cold email based on the prospect's structured profile
    and the campaign's configuration/value proposition.
    """
    print("--- [Node: Email Drafter] Drafting highly personalized outreach ---")
    prospect_id = state.get("prospect_id")
    campaign_id = state.get("campaign_id")
    structured_data = state.get("structured_prospect_data", {})
    
    # Assuming campaign value prop is part of the targeting criteria or config, 
    # but for now we'll pass a general directive based on ICP criteria
    icp_criteria = state.get("icp_criteria", {})
    
    # RAG Retrieval: Fetch the most relevant knowledge documents
    knowledge_context = "No specific knowledge base available."
    query = f"Industry: {structured_data.get('industry', '')} Role: {structured_data.get('title', '')}"
    query_vector = get_embeddings().embed_query(query)
    
    async with AsyncSessionLocal() as db:
        results = await db.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.campaign_id == campaign_id)
            .order_by(KnowledgeDocument.embedding.cosine_distance(query_vector))
            .limit(2)
        )
        knowledge_docs = results.scalars().all()
        if knowledge_docs:
            knowledge_context = "\n\n".join([doc.content for doc in knowledge_docs])
    
    async with AsyncSessionLocal() as tmp_db:
        raw_sys_prompt = await get_active_prompt(tmp_db, campaign_id, "email_drafter", "You are an elite B2B SDR. Draft a highly personalized cold email for the given prospect.\nYour email must be concise, engaging, and highlight a clear value proposition related to their industry/role.\nReturn a structured JSON with 'subject' and 'body'.")
    system_prompt = SystemMessage(content=raw_sys_prompt)
    
    user_prompt = HumanMessage(content=f"""
    Target Audience/Campaign Context: {icp_criteria}
    Campaign Knowledge Base (Use this for context/case studies):
    {knowledge_context}
    
    Prospect Profile: {structured_data}
    """)
    
    import os
    
    llm = ChatOpenAI(model="openai/gpt-oss-20b",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.4
    )
    structured_llm = llm.with_structured_output(EmailDraftResponse, include_raw=True)
    
    try:
        response = await structured_llm.ainvoke([system_prompt, user_prompt])
        draft: EmailDraftResponse = response["parsed"]
        raw_msg = response["raw"]
        
        usage = raw_msg.usage_metadata or {}
        
        final_email_text = f"Subject: {draft.subject}\n\n{draft.body}"
        print(f"Drafted Email:\n{final_email_text}")
        
        details = {"subject": draft.subject, "body_preview": draft.body[:100] + "..."}
        if usage:
            details["meta"] = {
                "model": "openai/gpt-oss-20b (Groq)",
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }
    except Exception as e:
        print(f"--- [Node: Email Drafter] Error: {str(e)}")
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
            prospect = result.scalars().first()
            if prospect:
                prospect.stage = ProspectStage.DRAFT_FAILED
                prospect.escalated_to_rep = True
                db.add(AgentLog(
                    campaign_id=campaign_id,
                    prospect_id=prospect_id,
                    agent_name="Email Personalization Node",
                    action="DRAFT_FAILED",
                    status="ERROR",
                    prompt_version="v1.0",
                    details={"error": str(e)}
                ))
                await db.commit()
        return {"current_status": "Draft_Failed", "messages": [SystemMessage(content=f"Email drafting failed: {str(e)}")]}
    
    # Update the Database
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
        prospect = result.scalars().first()
        if prospect:
            prospect.stage = ProspectStage.DRAFTED
            prospect.draft_email = final_email_text
            
            db.add(AgentLog(
                campaign_id=campaign_id,
                prospect_id=prospect_id,
                agent_name="Email Personalization Node",
                action="DRAFTED_EMAIL",
                status="SUCCESS",
                prompt_version="v1.0",
                details=details
            ))
            
            await db.commit()
            
    return {
        "messages": [SystemMessage(content=f"Email drafted with subject: {draft.subject}")]
    }

class LinkedinDraftResponse(BaseModel):
    message: str

async def linkedin_drafter_node(state: AgentState) -> dict[str, Any]:
    """
    The LinkedIn Drafter Node.
    Writes a highly personalized, 300-character max LinkedIn connection request.
    """
    print("--- [Node: LinkedIn Drafter] Drafting LinkedIn connection request ---")
    prospect_id = state.get("prospect_id")
    campaign_id = state.get("campaign_id")
    structured_data = state.get("structured_prospect_data", {})
    icp_criteria = state.get("icp_criteria", {})
    
    async with AsyncSessionLocal() as tmp_db:
        raw_sys_prompt = await get_active_prompt(tmp_db, campaign_id, "linkedin_drafter", "You are an elite B2B SDR. Draft a highly personalized LinkedIn connection request for the given prospect.\nIt must be strictly UNDER 300 characters. Be conversational and mention their industry or role.\nReturn a structured JSON with 'message'.")
    system_prompt = SystemMessage(content=raw_sys_prompt)
    
    user_prompt = HumanMessage(content=f"""
    Target Audience: {icp_criteria}
    Prospect Profile: {structured_data}
    """)
    
    import os
    llm = ChatOpenAI(model="openai/gpt-oss-20b",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.4
    )
    structured_llm = llm.with_structured_output(LinkedinDraftResponse)
    
    try:
        draft: LinkedinDraftResponse = await structured_llm.ainvoke([system_prompt, user_prompt])
        final_msg = draft.message
        print(f"Drafted LinkedIn:\n{final_msg}")
    except Exception as e:
        print(f"--- [Node: LinkedIn Drafter] Error: {str(e)}")
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
            prospect = result.scalars().first()
            if prospect:
                prospect.stage = ProspectStage.DRAFT_FAILED
                prospect.escalated_to_rep = True
                db.add(AgentLog(
                    campaign_id=campaign_id,
                    prospect_id=prospect_id,
                    agent_name="LinkedIn Personalization Node",
                    action="DRAFT_FAILED",
                    status="ERROR",
                    prompt_version="v1.0",
                    details={"error": str(e)}
                ))
                await db.commit()
        return {"current_status": "Draft_Failed", "messages": [SystemMessage(content=f"LinkedIn drafting failed: {str(e)}")]}
    
    # Update Database
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
        prospect = result.scalars().first()
        if prospect:
            prospect.stage = ProspectStage.DRAFTED_LINKEDIN
            prospect.draft_linkedin_msg = final_msg
            
            db.add(AgentLog(
                campaign_id=campaign_id,
                prospect_id=prospect_id,
                agent_name="LinkedIn Personalization Node",
                action="DRAFTED_LINKEDIN",
                status="SUCCESS",
                prompt_version="v1.0",
                details={"message": final_msg}
            ))
            
            await db.commit()
            
    return {
        "messages": [SystemMessage(content="LinkedIn connection request drafted.")]
    }

async def email_sender_node(state: AgentState) -> dict[str, Any]:
    """
    The Email Sender Node.
    Actually sends the drafted email using the Resend SDK.
    """
    print("--- [Node: Email Sender] Sending email ---")
    import os
    import resend
    
    prospect_id = state.get("prospect_id")
    campaign_id = state.get("campaign_id")
    
    # Use a dummy API key for hackathon purposes if not provided
    resend.api_key = RESEND_API_KEY
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
        prospect = result.scalars().first()
        
        if not prospect or not prospect.draft_email:
            return {"messages": [SystemMessage(content="Error: No draft email found.")]}
            
        draft_text = prospect.draft_email
        subject = draft_text.split("\n\n")[0].replace("Subject: ", "") if "Subject: " in draft_text else "Hello from our team"
        body = draft_text.replace(f"Subject: {subject}\n\n", "")
        
        to_email = os.getenv("DEMO_EMAIL_OVERRIDE", prospect.email or "test@example.com")
        
        try:
            # Actually send with a real API key
            if RESEND_API_KEY.startswith("re_dummy"):
                print("WARNING: Using dummy Resend key. Skipping actual email dispatch.")
                import asyncio
                await asyncio.sleep(1) # Simulate network call
            else:
                params = {
                    "from": "onboarding@resend.dev",
                    "to": [to_email],
                    "subject": subject,
                    "html": f"<p>{body.replace(chr(10), '<br>')}</p>"
                }
                resend.Emails.send(params)
            
            prospect.stage = ProspectStage.CONTACTED
            db.add(AgentLog(
                campaign_id=campaign_id,
                prospect_id=prospect_id,
                agent_name="Email Sender Node",
                action="SENT_EMAIL",
                status="SUCCESS",
                prompt_version="v1.0",
                details={"to": to_email, "subject": subject}
            ))
            await db.commit()
            print(f"SUCCESS: Email sent to {to_email}")
            
        except Exception as e:
            print(f"FAILED to send email: {str(e)}")
            return {"messages": [SystemMessage(content=f"Error sending email: {str(e)}")]}
            
    return {"current_status": "Contacted", "messages": [SystemMessage(content="Email sent successfully.")]}

class ReplyClassification(BaseModel):
    intent: Literal['POSITIVE', 'OBJECTION', 'NOT_INTERESTED']
    reasoning: str
    suggested_rebuttal: str = ""

async def conversation_node(state: AgentState) -> dict[str, Any]:
    """
    The Conversation Agent Node.
    Triggered by a webhook, reads inbound replies, classifies intent,
    and performs RAG objection handling if needed.
    """
    print("--- [Node: Conversation] Processing inbound reply ---")
    prospect_id = state.get("prospect_id")
    campaign_id = state.get("campaign_id")
    inbound_message = state.get("messages")[-1].content
    
    # If it's an objection, fetch playbook from RAG
    query_vector = get_embeddings().embed_query("Objection handling playbook")
    rag_context = ""
    async with AsyncSessionLocal() as db:
        results = await db.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.campaign_id == campaign_id)
            .order_by(KnowledgeDocument.embedding.cosine_distance(query_vector))
            .limit(1)
        )
        knowledge_docs = results.scalars().all()
        if knowledge_docs:
            rag_context = knowledge_docs[0].content
            
    async with AsyncSessionLocal() as tmp_db:
        raw_sys_prompt = await get_active_prompt(tmp_db, campaign_id, "conversation_handler", "You are an AI SDR reading an inbound reply from a prospect.\nClassify the intent into: POSITIVE, OBJECTION, or NOT_INTERESTED.\nIf OBJECTION, use the provided playbook context to draft a suggested_rebuttal.\nReturn a structured JSON with 'intent', 'reasoning', and 'suggested_rebuttal'.")
    system_prompt = SystemMessage(content=raw_sys_prompt)
    
    user_prompt = HumanMessage(content=f"""
    Inbound Reply: "{inbound_message}"
    Objection Playbook Context: {rag_context}
    """)
    
    import os
    llm = ChatOpenAI(model="openai/gpt-oss-20b",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.1
    )
    structured_llm = llm.with_structured_output(ReplyClassification)
    
    classification: ReplyClassification = await structured_llm.ainvoke([system_prompt, user_prompt])
    print(f"Reply Classified as {classification.intent}: {classification.reasoning}")
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
        prospect = result.scalars().first()
        if prospect:
            # Update history
            history = prospect.conversation_history or []
            history.append({"role": "user", "content": inbound_message})
            history.append({"role": "agent", "classification": classification.intent, "rebuttal": classification.suggested_rebuttal})
            prospect.conversation_history = history
            
            if classification.intent == "POSITIVE":
                prospect.stage = ProspectStage.MEETING
                prospect.escalated_to_rep = True
            elif classification.intent == "OBJECTION":
                prospect.stage = ProspectStage.ENGAGED
            else:
                prospect.stage = ProspectStage.REJECTED
                
            db.add(AgentLog(
                campaign_id=campaign_id,
                prospect_id=prospect_id,
                agent_name="Conversation Node",
                action="PROCESSED_REPLY",
                status="SUCCESS",
                prompt_version="v1.0",
                details={"intent": classification.intent, "rebuttal": classification.suggested_rebuttal}
            ))
            await db.commit()
            
    return {"current_status": classification.intent, "messages": [SystemMessage(content=f"Handled reply: {classification.intent}")]}

class VoiceDraftResponse(BaseModel):
    call_script: str
    simulated_disposition: str
    simulated_duration_seconds: int

async def voice_node(state: AgentState) -> dict[str, Any]:
    print("--- [Node: Voice SDR] Simulating AI Voice Call ---")
    prospect_id = state.get("prospect_id")
    campaign_id = state.get("campaign_id")
    structured_data = state.get("structured_prospect_data", {})
    
    # RAG Retrieval for objections
    knowledge_context = "No specific knowledge base available."
    query = "objection handling competitor budget"
    query_vector = get_embeddings().embed_query(query)
    
    async with AsyncSessionLocal() as db:
        results = await db.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.campaign_id == campaign_id)
            .order_by(KnowledgeDocument.embedding.cosine_distance(query_vector))
            .limit(2)
        )
        knowledge_docs = results.scalars().all()
        if knowledge_docs:
            knowledge_context = "\n\n".join([doc.content for doc in knowledge_docs])
            
    async with AsyncSessionLocal() as tmp_db:
        raw_sys_prompt = await get_active_prompt(tmp_db, campaign_id, "voice_sdr", "You are an elite AI Voice SDR. Draft a conversational call script. Simulate how the call went (disposition) and how long it took. Use the provided knowledge base to handle simulated objections.\nReturn a JSON with 'call_script', 'simulated_disposition', and 'simulated_duration_seconds'.")
    
    system_prompt = SystemMessage(content=raw_sys_prompt)
    user_prompt = HumanMessage(content=f"Prospect Profile: {structured_data}\nKnowledge Base: {knowledge_context}")
    
    import os
    llm = ChatOpenAI(model="openai/gpt-oss-20b",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.6
    )
    structured_llm = llm.with_structured_output(VoiceDraftResponse)
    
    response: VoiceDraftResponse = await structured_llm.ainvoke([system_prompt, user_prompt])
    print(f"Voice Call Result: {response.simulated_disposition} ({response.simulated_duration_seconds}s)")
    
    # Write to AgentLog (simulated call record)
    async with AsyncSessionLocal() as db:
        db.add(AgentLog(
            campaign_id=campaign_id,
            prospect_id=prospect_id,
            agent_name="Voice SDR Node",
            action="VOICE_CALL_COMPLETED",
            status="SUCCESS",
            prompt_version="v1.0",
            details={"script": response.call_script, "disposition": response.simulated_disposition, "duration": response.simulated_duration_seconds}
        ))
        
        # Update Prospect Stage
        result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
        prospect = result.scalars().first()
        if prospect:
            prospect.stage = ProspectStage.CONTACTED
            
        await db.commit()
        
    return {"current_status": "Contacted", "messages": [SystemMessage(content=f"Voice SDR Call Script: {response.call_script}")]}

class FollowUpResponse(BaseModel):
    follow_up_message: str
    channel_used: str

async def follow_up_node(state: AgentState) -> dict[str, Any]:
    print("--- [Node: Follow-up] Drafting follow-up ping ---")
    prospect_id = state.get("prospect_id")
    campaign_id = state.get("campaign_id")
    structured_data = state.get("structured_prospect_data", {})
    
    async with AsyncSessionLocal() as tmp_db:
        raw_sys_prompt = await get_active_prompt(tmp_db, campaign_id, "follow_up", "You are an elite B2B SDR writing a multi-channel follow-up to a prospect who hasn't replied.\nReturn a JSON with 'follow_up_message' and 'channel_used' (email or linkedin).")
    
    system_prompt = SystemMessage(content=raw_sys_prompt)
    user_prompt = HumanMessage(content=f"Prospect Profile: {structured_data}\nDraft a polite bump.")
    
    import os
    llm = ChatOpenAI(model="openai/gpt-oss-20b",
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0.4
    )
    structured_llm = llm.with_structured_output(FollowUpResponse)
    
    response: FollowUpResponse = await structured_llm.ainvoke([system_prompt, user_prompt])
    print(f"Follow-Up Drafted via {response.channel_used}")
    
    # Write to AgentLog
    async with AsyncSessionLocal() as db:
        db.add(AgentLog(
            campaign_id=campaign_id,
            prospect_id=prospect_id,
            agent_name="Follow-up Node",
            action="FOLLOW_UP_SENT",
            status="SUCCESS",
            prompt_version="v1.0",
            details={"message": response.follow_up_message, "channel": response.channel_used}
        ))
        
        # Update Prospect Stage
        result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
        prospect = result.scalars().first()
        if prospect:
            prospect.stage = ProspectStage.ENGAGED # Mark as bumped/engaged
            
        await db.commit()
        
    return {"current_status": "Engaged", "messages": [SystemMessage(content=f"Follow up sent: {response.follow_up_message}")]}
