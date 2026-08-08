"""Background Task Worker - executes search, scoring, background check, and contact research tasks.

Supports both synchronous execution and Celery-based async execution.
For development, uses direct async execution.
For production, integrates with Celery + Redis.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session as async_session_factory
from app.models.company import Company
from app.models.contact import Contact
from app.models.project import Project
from app.models.task import SearchTask
from app.services.google_search import search_google, build_search_queries
from app.services.scorer import score_company
from app.services.website_scraper import scrape_website, generate_background_report
from app.services.contact_research import research_contacts
from app.services.whatsapp_sniffer import sniff_whatsapp_from_text

logger = logging.getLogger(__name__)


class TaskWorker:
    """Background task executor for the B2B growth pipeline."""

    async def execute_search_task(self, task_id: str) -> dict:
        """Execute a search task: search -> create companies -> score.

        Args:
            task_id: The SearchTask ID

        Returns:
            {"companies_found": int, "companies_created": int, "status": str}
        """
        async with async_session_factory() as db:
            # Load task
            task = await db.get(SearchTask, task_id)
            if not task:
                return {"error": "Task not found", "status": "failed"}

            # Update task status
            task.status = "running"
            task.started_at = datetime.utcnow()
            await db.commit()

            try:
                # Load project
                project = await db.get(Project, task.project_id)
                if not project:
                    raise ValueError(f"Project {task.project_id} not found")

                # Build search queries from project config
                product_keywords = project.product_name_en.split(",") if project.product_name_en else []
                if project.product_name:
                    product_keywords.extend(project.product_name.split(","))
                product_keywords = [k.strip() for k in product_keywords if k.strip()]

                queries = build_search_queries(
                    product_keywords=product_keywords,
                    customer_types=project.priority_customer_types,
                    region_keywords=project.target_markets,
                )

                # Limit queries based on task config
                max_queries = task.max_queries or 20
                queries = queries[:max_queries]

                companies_found = 0
                companies_created = 0

                # Execute searches
                for query in queries:
                    try:
                        results = await search_google(query, num_results=10)
                        for result in results:
                            companies_found += 1
                            # Try to create company from search result
                            created = await self._create_company_from_result(
                                db, result, query, project, task
                            )
                            if created:
                                companies_created += 1
                    except Exception as e:
                        logger.warning(f"Search error for query '{query}': {e}")
                        continue

                # Update task
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                task.result_summary = {
                    "queries_executed": len(queries),
                    "companies_found": companies_found,
                    "companies_created": companies_created,
                }

                # Update project last_run_at
                project.last_run_at = datetime.utcnow()
                await db.commit()

                return {
                    "companies_found": companies_found,
                    "companies_created": companies_created,
                    "status": "completed"
                }

            except Exception as e:
                task.status = "failed"
                task.error_message = str(e)
                await db.commit()
                logger.error(f"Task {task_id} failed: {e}")
                return {"error": str(e), "status": "failed"}

    async def _create_company_from_result(
        self, db: AsyncSession, result: dict, query: str,
        project: Project, task: SearchTask
    ) -> bool:
        """Try to create a company record from a search result.

        Returns True if a new company was created.
        """
        url = result.get("link", "")
        title = result.get("title", "")
        snippet = result.get("snippet", "")

        # Extract company name from title (before first separator)
        company_name = title.split(" - ")[0].split(" | ")[0].split(" – ")[0].strip()
        if not company_name or len(company_name) < 3:
            return False

        # Extract domain
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc.replace("www.", "")
        except Exception:
            return False

        # Skip known non-company domains
        skip_domains = [
            "google.com", "facebook.com", "linkedin.com", "twitter.com",
            "youtube.com", "instagram.com", "wikipedia.org", "amazon.com",
            "alibaba.com", "aliexpress.com", "reddit.com"
        ]
        if domain in skip_domains:
            return False

        # Dedup check
        existing = await db.execute(
            select(Company).where(
                Company.project_id == project.id,
                Company.website.like(f"%{domain}%")
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            return False

        # Also check by name
        existing_name = await db.execute(
            select(Company).where(
                Company.project_id == project.id,
                Company.company_name == company_name
            ).limit(1)
        )
        if existing_name.scalar_one_or_none():
            return False

        # WhatsApp sniffing
        wa_groups, wa_numbers = sniff_whatsapp_from_text(snippet)

        # Create company
        company = Company(
            project_id=project.id,
            company_name=company_name,
            website=url,
            main_business=snippet[:500] if snippet else None,
            discovery_path="Google Search",
            source_keywords=query,
            source_url_1=url,
            collected_at=datetime.utcnow(),
            whatsapp_numbers=wa_numbers if wa_numbers else None,
            whatsapp_group_links=wa_groups if wa_groups else None,
            review_status="pending",
        )
        db.add(company)
        await db.commit()
        return True

    async def execute_background_check(self, company_id: str) -> dict:
        """Execute background check for a company.

        Args:
            company_id: Company ID

        Returns:
            Background check report dict
        """
        async with async_session_factory() as db:
            company = await db.get(Company, company_id)
            if not company:
                return {"error": "Company not found"}

            if not company.website:
                return {"error": "No website URL for background check"}

            # Scrape website
            scrape_result = await scrape_website(company.website)

            # Generate report
            report = generate_background_report(scrape_result)

            # Update company
            company.background_report = report
            if scrape_result.get("whatsapp_numbers"):
                existing = company.whatsapp_numbers or []
                company.whatsapp_numbers = list(set(existing + scrape_result["whatsapp_numbers"]))
            if scrape_result.get("whatsapp_group_links"):
                existing = company.whatsapp_group_links or []
                company.whatsapp_group_links = list(set(existing + scrape_result["whatsapp_group_links"]))

            # Update business info from scrape if available
            if scrape_result.get("business_scope") and not company.main_business:
                company.main_business = scrape_result["business_scope"]
            if scrape_result.get("product_lines") and not company.related_products:
                company.related_products = ", ".join(scrape_result["product_lines"][:10])

            await db.commit()

            return report

    async def execute_contact_research(self, company_id: str) -> dict:
        """Execute contact research for a company.

        Args:
            company_id: Company ID

        Returns:
            {"contacts_found": int, "contacts": list}
        """
        async with async_session_factory() as db:
            company = await db.get(Company, company_id)
            if not company:
                return {"error": "Company not found"}

            if company.grade not in ["A", "B"]:
                return {"error": "Contact research only for A/B grade companies"}

            # Research contacts
            contacts = await research_contacts(
                company_name=company.company_name,
                website=company.website or "",
                country=company.country or "",
                project_id=company.project_id,
            )

            # Save contacts to database
            saved_count = 0
            for contact_data in contacts:
                # Dedup check
                if contact_data.get("full_name"):
                    existing = await db.execute(
                        select(Contact).where(
                            Contact.company_id == company_id,
                            Contact.full_name == contact_data["full_name"]
                        ).limit(1)
                    )
                    if existing.scalar_one_or_none():
                        continue

                contact = Contact(
                    company_id=company_id,
                    project_id=company.project_id,
                    company_name=company.company_name,
                    full_name=contact_data.get("full_name"),
                    job_title=contact_data.get("job_title"),
                    decision_role=contact_data.get("decision_role"),
                    contact_grade=contact_data.get("contact_grade", "BRONZE"),
                    personal_email=contact_data.get("personal_email"),
                    email_status=contact_data.get("email_status"),
                    company_email=contact_data.get("company_email"),
                    personal_phone=contact_data.get("personal_phone"),
                    linkedin_personal=contact_data.get("linkedin_personal"),
                    identity_source_url=contact_data.get("identity_source_url"),
                    contact_source_url=contact_data.get("contact_source_url"),
                    employment_status="active",
                    research_notes=contact_data.get("research_notes"),
                    review_status="pending",
                )
                db.add(contact)
                saved_count += 1

            await db.commit()

            return {
                "contacts_found": len(contacts),
                "contacts_saved": saved_count,
            }

    async def execute_batch_scoring(self, project_id: str) -> dict:
        """Score all unscored companies in a project.

        Args:
            project_id: Project ID

        Returns:
            {"scored": int, "grade_distribution": dict}
        """
        async with async_session_factory() as db:
            # Load project for scoring template
            project = await db.get(Project, project_id)
            if not project:
                return {"error": "Project not found"}

            # Get unscored companies
            result = await db.execute(
                select(Company).where(
                    Company.project_id == project_id,
                    Company.grade.is_(None)
                )
            )
            companies = result.scalars().all()

            scored = 0
            grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "excluded": 0}

            for company in companies:
                score_result = score_company(company, project.scoring_template)
                company.score = score_result["total"]
                company.score_details = score_result["details"]
                company.grade = score_result["grade"]
                if score_result.get("exclusion_reason"):
                    company.items_to_verify = score_result["exclusion_reason"]
                scored += 1
                grade_dist[score_result["grade"]] = grade_dist.get(score_result["grade"], 0) + 1

            await db.commit()

            return {"scored": scored, "grade_distribution": grade_dist}


# Singleton worker instance
task_worker = TaskWorker()
