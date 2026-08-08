"""Customs data service - interface for ImportYeti and other customs data sources."""
import httpx
from typing import Optional, List
from app.config import settings


async def query_importyeti(company_name: str) -> dict:
    """Query ImportYeti for customs/import records.

    ImportYeti provides free access to US import records.
    This is a placeholder interface - actual implementation depends on API availability.
    """
    if not settings.importyeti_api_key:
        return {
            "source": "ImportYeti",
            "available": False,
            "message": "ImportYeti API key not configured",
            "records": []
        }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.importyeti.com/v1/companies",
                params={"q": company_name},
                headers={"Authorization": f"Bearer {settings.importyeti_api_key}"},
                timeout=15.0
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "source": "ImportYeti",
                    "available": True,
                    "import_records": len(data.get("records", [])),
                    "top_suppliers": [
                        {"name": s.get("name", ""), "shipments": s.get("count", 0)}
                        for s in data.get("top_suppliers", [])[:5]
                    ],
                    "records": data.get("records", [])[:10]
                }
            else:
                return {
                    "source": "ImportYeti",
                    "available": False,
                    "error": f"API returned {response.status_code}",
                    "records": []
                }
    except httpx.HTTPError as e:
        return {
            "source": "ImportYeti",
            "available": False,
            "error": str(e),
            "records": []
        }


async def query_customs_data(company_name: str, country: Optional[str] = None) -> dict:
    """Unified customs data query interface.

    Extensible to support multiple data sources:
    - ImportYeti (US imports)
    - Panjiva (global trade data)
    - ImportGenius (global trade data)
    """
    results = {
        "company_name": company_name,
        "country": country,
        "sources": []
    }

    # Query ImportYeti
    importyeti_result = await query_importyeti(company_name)
    results["sources"].append(importyeti_result)

    # Aggregate results
    total_records = sum(s.get("import_records", 0) for s in results["sources"] if s.get("available"))
    results["total_import_records"] = total_records

    return results
