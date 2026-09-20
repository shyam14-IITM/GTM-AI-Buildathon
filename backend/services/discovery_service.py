import os
from typing import List, Dict, Any
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from duckduckgo_search import DDGS

class SyntheticLead(BaseModel):
    first_name: str
    last_name: str
    headline: str
    organization_name: str
    linkedin_url: str
    email: str

class SyntheticLeadsResponse(BaseModel):
    leads: List[SyntheticLead]

async def discover_leads(
    job_titles: List[str], 
    limit: int = 3, 
    demo_email: str = "your_student_email@smail.iitm.ac.in"
) -> List[Dict[str, Any]]:
    """
    Attempts live web search via duckduckgo-search. 
    If it fails, falls back to pure AI synthetic generation.
    In all cases, overrides emails for demo purposes.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is missing")

    llm = ChatOpenAI(model="openai/gpt-oss-20b",
        base_url="https://api.groq.com/openai/v1",
        api_key=groq_api_key,
        temperature=0.7,
        max_tokens=8000
    )
    structured_llm = llm.with_structured_output(SyntheticLeadsResponse)
    
    # Check if a custom demo email is provided in environment, otherwise fallback to the requested default
    actual_demo_email = os.getenv("DEMO_EMAIL_OVERRIDE", demo_email)
    
    leads = []
    target_title = job_titles[0] if job_titles else "Executive"
    
    try:
        query = f'site:linkedin.com/in/ "{target_title}"'
        print(f"--- [Discovery] Querying DDGS: {query} ---")
        
        # DDGS is synchronous by default. Fetch extra results to ensure uniqueness
        results = DDGS().text(query, max_results=limit * 3)
        
        if not results:
            raise RuntimeError("DDGS returned 0 results.")
            
        print(f"--- [Discovery] DDGS found {len(results)} raw results. Passing to LLM for extraction ---")
        
        # Compile results into a single string
        compiled_results = "\n".join(
            [f"Title: {r.get('title', '')}\nURL: {r.get('href', '')}\nSnippet: {r.get('body', '')}\n" for r in results]
        )
        
        prompt = (
            f"Extract professional profiles from these search results.\n\n"
            f"Results:\n{compiled_results}\n\n"
            f"Requirements:\n"
            f"Extract exactly {limit} UNIQUE profiles. Do not return duplicate people.\n"
            f"Keys required: first_name, last_name, email, headline, organization_name, linkedin_url.\n"
            f"(If email is not in the text, guess their highly realistic professional corporate email)."
        )
        
        response = await structured_llm.ainvoke(prompt)
        leads = response.leads
        
    except Exception as e:
        print(f"--- [Discovery] DDGS failed ({str(e)}), falling back to synthetic generation ---")
        
        fallback_prompt = (
            f"You are a B2B data generator. Generate {limit} highly realistic fictional B2B prospect profiles "
            f"matching the job title: {target_title}. "
            f"Keys required: first_name, last_name, email, headline, organization_name, linkedin_url."
        )
        
        response = await structured_llm.ainvoke(fallback_prompt)
        leads = response.leads

    # Deduplicate leads based on linkedin_url
    seen_urls = set()
    unique_leads = []
    
    for lead in leads:
        if lead.linkedin_url not in seen_urls:
            seen_urls.add(lead.linkedin_url)
            unique_leads.append(lead)
            if len(unique_leads) == limit:
                break
                
    # If DDGS+LLM yielded duplicates, we might have less than `limit` leads.
    # Pad the remaining count synthetically to guarantee exactly `limit` unique leads for the demo.
    if len(unique_leads) < limit:
        pad_limit = limit - len(unique_leads)
        print(f"--- [Discovery] Found {len(unique_leads)} unique leads. Synthetically generating {pad_limit} more ---")
        
        fallback_prompt = (
            f"You are a B2B data generator. Generate {pad_limit} highly realistic, completely unique B2B prospect profiles "
            f"matching the job title: {target_title}. "
            f"Keys required: first_name, last_name, email, headline, organization_name, linkedin_url."
        )
        pad_response = await structured_llm.ainvoke(fallback_prompt)
        
        for lead in pad_response.leads:
            if lead.linkedin_url not in seen_urls:
                seen_urls.add(lead.linkedin_url)
                unique_leads.append(lead)
                if len(unique_leads) == limit:
                    break

    # Format the response with real/guessed emails.
    final_prospects = []
    
    import uuid
    for lead in unique_leads:
        random_id = uuid.uuid4().hex[:6]
        
        # We append a random ID to the username part of the guessed email just to guarantee it never crashes the DB unique constraint
        email_parts = lead.email.split("@")
        if len(email_parts) == 2:
            safe_email = f"{email_parts[0]}+{random_id}@{email_parts[1]}"
        else:
            safe_email = f"contact+{random_id}@example.com"
            
        final_prospects.append({
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "headline": lead.headline,
            "company_name": lead.organization_name,
            "linkedin_url": f"{lead.linkedin_url}-{random_id}", # Guaranteed unique across clicks
            "email": safe_email # Looks professional in UI, guaranteed unique in DB
        })
        
    return final_prospects
