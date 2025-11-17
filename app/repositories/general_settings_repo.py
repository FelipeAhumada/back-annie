"""
Repository for general_settings database operations.

Follows Layer 4 rules:
- All queries MUST be tenant-scoped
- Data access MUST be routed through repository layer
- No raw queries inside API routes
"""
from __future__ import annotations
from typing import Optional
from core.db import get_conn
from core.redis import rds
import json


def get_general_settings(tenant_id: str) -> Optional[dict]:
    """
    Get general settings for a tenant.
    
    Args:
        tenant_id: Tenant identifier
    
    Returns:
        Dict with settings or None if not found
    """
    # Try cache first
    cache_key = f"general_settings:{tenant_id}"
    cached = rds.get(cache_key)
    if cached:
        return json.loads(cached)
    
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT tenant_id, name, logo_url, website_url, short_description,
                   mission, vision, purpose, customer_problems,
                   created_at, updated_at
            FROM general_settings
            WHERE tenant_id = %s
        """, (tenant_id,))
        row = cur.fetchone()
        
        if not row:
            return None
        
        data = {
            "tenant_id": row[0],
            "name": row[1],
            "logo_url": row[2],
            "website_url": row[3],
            "short_description": row[4],
            "mission": row[5],
            "vision": row[6],
            "purpose": row[7],
            "customer_problems": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "updated_at": row[10].isoformat() if row[10] else None,
        }
        
        # Cache for 1 hour
        rds.setex(cache_key, 3600, json.dumps(data))
        return data


def upsert_general_settings(tenant_id: str, data: dict) -> dict:
    """
    Create or update general settings for a tenant.
    
    Args:
        tenant_id: Tenant identifier
        data: Settings data dict (from Pydantic model)
    
    Returns:
        Updated settings dict
    """
    with get_conn() as conn, conn.cursor() as cur:
        # Check if record exists
        cur.execute("SELECT tenant_id FROM general_settings WHERE tenant_id = %s", (tenant_id,))
        exists = cur.fetchone() is not None
        
        if not exists:
            # Create new record
            cur.execute("""
                INSERT INTO general_settings (
                    tenant_id, name, logo_url, website_url, short_description,
                    mission, vision, purpose, customer_problems
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING tenant_id, name, logo_url, website_url, short_description,
                          mission, vision, purpose, customer_problems,
                          created_at, updated_at
            """, (
                tenant_id,
                data.get("name", "Unnamed Organization"),
                data.get("logo_url"),
                data.get("website_url"),
                data.get("short_description"),
                data.get("mission"),
                data.get("vision"),
                data.get("purpose"),
                data.get("customer_problems"),
            ))
        else:
            # Update existing record (partial update - only non-None fields)
            update_fields = []
            update_values = []
            
            for key, value in data.items():
                if value is not None:
                    update_fields.append(f"{key} = %s")
                    update_values.append(value)
            
            if update_fields:
                update_fields.append("updated_at = now()")
                update_values.append(tenant_id)
                
                cur.execute(f"""
                    UPDATE general_settings
                    SET {', '.join(update_fields)}
                    WHERE tenant_id = %s
                    RETURNING tenant_id, name, logo_url, website_url, short_description,
                              mission, vision, purpose, customer_problems,
                              created_at, updated_at
                """, tuple(update_values))
            else:
                # No fields to update, just fetch current
                cur.execute("""
                    SELECT tenant_id, name, logo_url, website_url, short_description,
                           mission, vision, purpose, customer_problems,
                           created_at, updated_at
                    FROM general_settings
                    WHERE tenant_id = %s
                """, (tenant_id,))
        
        row = cur.fetchone()
        conn.commit()
        
        result = {
            "tenant_id": row[0],
            "name": row[1],
            "logo_url": row[2],
            "website_url": row[3],
            "short_description": row[4],
            "mission": row[5],
            "vision": row[6],
            "purpose": row[7],
            "customer_problems": row[8],
            "created_at": row[9].isoformat() if row[9] else None,
            "updated_at": row[10].isoformat() if row[10] else None,
        }
        
        # Invalidate cache
        rds.delete(f"general_settings:{tenant_id}")
        
        return result

