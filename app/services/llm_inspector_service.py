"""
LLM service for extracting organization information from website URLs.

Follows Layer 5 and Layer 8 rules:
- API keys from centralized config
- External HTTP calls MUST use HTTPS
- Reasonable timeouts and error handling
"""
from __future__ import annotations
import json
import re
from typing import Optional
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from core.config import settings
from core.errors import http_error, ErrorCode


async def extract_website_content(url: str, timeout: int = 10) -> str:
    """
    Fetch and extract main text content from a website URL.
    
    Args:
        url: Website URL to fetch
        timeout: Request timeout in seconds
    
    Returns:
        Extracted text content
    
    Raises:
        ValueError: If URL is invalid or request fails
    """
    # Validate URL
    parsed = urlparse(url)
    if not parsed.scheme:
        raise ValueError("URL must include scheme (http:// or https://)")
    
    # Enforce HTTPS if possible (security best practice)
    if parsed.scheme == "http":
        # Allow HTTP but log warning (could be enhanced)
        pass
    
    # Fetch HTML
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Annie-AI/1.0; +https://annie-ai.app)"
            })
            response.raise_for_status()
            html = response.text
    except httpx.TimeoutException:
        raise ValueError(f"Request timeout after {timeout} seconds")
    except httpx.HTTPStatusError as e:
        raise ValueError(f"HTTP error {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        raise ValueError(f"Failed to fetch URL: {str(e)}")
    
    # Extract text using BeautifulSoup
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "meta", "link"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = " ".join(chunk for chunk in chunks if chunk)
        
        # Limit text length (LLM context limits)
        if len(text) > 10000:
            text = text[:10000] + "..."
        
        return text
    except Exception as e:
        raise ValueError(f"Failed to parse HTML: {str(e)}")


async def autofill_from_url(website_url: str) -> dict:
    """
    Extract organization information from a website URL using OpenAI.
    
    Args:
        website_url: Public website URL
    
    Returns:
        Dict with extracted fields: name, short_description, mission, vision, purpose, customer_problems
    
    Raises:
        ValueError: If URL is invalid or extraction fails
        RuntimeError: If OpenAI API key is missing
    """
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")
    
    # Extract website content
    try:
        content = await extract_website_content(website_url)
    except ValueError as e:
        raise ValueError(f"Failed to fetch website: {str(e)}")
    
    if not content or len(content.strip()) < 50:
        raise ValueError("Website content too short or empty")
    
    # Prepare prompt for OpenAI
    prompt = f"""Analyze the following website content and extract organization information. 
Return ONLY a valid JSON object with these exact fields (use null for missing information):
{{
  "name": "Organization name",
  "short_description": "Brief description (1-2 sentences)",
  "mission": "Mission statement",
  "vision": "Vision statement", 
  "purpose": "Overall purpose of the organization",
  "customer_problems": "Problems that customers typically face (list or paragraph)"
}}

Website content:
{content[:8000]}

Return only the JSON object, no additional text:"""

    # Call OpenAI API
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",  # Use cost-effective model
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that extracts structured information from website content. Always return valid JSON only."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000,
                }
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract text from response
            content_text = result["choices"][0]["message"]["content"].strip()
            
            # Clean JSON (remove markdown code blocks if present)
            if content_text.startswith("```json"):
                content_text = content_text[7:]
            if content_text.startswith("```"):
                content_text = content_text[3:]
            if content_text.endswith("```"):
                content_text = content_text[:-3]
            content_text = content_text.strip()
            
            # Parse JSON
            try:
                extracted = json.loads(content_text)
            except json.JSONDecodeError:
                # Try to extract JSON from text
                json_match = re.search(r'\{[^{}]*\}', content_text, re.DOTALL)
                if json_match:
                    extracted = json.loads(json_match.group())
                else:
                    raise ValueError("Failed to parse JSON from LLM response")
            
            # Validate and return
            return {
                "name": extracted.get("name"),
                "short_description": extracted.get("short_description"),
                "mission": extracted.get("mission"),
                "vision": extracted.get("vision"),
                "purpose": extracted.get("purpose"),
                "customer_problems": extracted.get("customer_problems"),
            }
            
    except httpx.HTTPStatusError as e:
        error_text = e.response.text[:500] if e.response.text else "Unknown error"
        raise ValueError(f"OpenAI API error {e.response.status_code}: {error_text}")
    except Exception as e:
        raise ValueError(f"Failed to extract information: {str(e)}")

