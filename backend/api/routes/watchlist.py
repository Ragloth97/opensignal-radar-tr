"""
Takip Listesi API — TRENG & İRDA için izlenen şirketler.
"""
import csv
import io
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.db.database import get_db
from backend.db.models import WatchListCompany

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


# ─── Şemalar ─────────────────────────────────────────────────────────────────

class CompanyCreate(BaseModel):
    name: str
    aliases: Optional[List[str]] = []
    sector: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[str] = "medium"
    owner_company: Optional[str] = "both"


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    aliases: Optional[List[str]] = None
    sector: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[str] = None
    owner_company: Optional[str] = None
    is_active: Optional[bool] = None


def _normalize_name(name: str) -> str:
    """Şirket adını normalize et: küçük harf, boşluk temizle, yaygın kısaltmaları kaldır."""
    name = name.strip()
    # AŞ, Ltd, Inc vb kısaltmaları koru ama boşlukları normalize et
    import re
    name = re.sub(r'\s+', ' ', name)
    return name


def _serialize(c: WatchListCompany) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "raw_name": c.raw_name,
        "aliases": c.aliases or [],
        "sector": c.sector,
        "location": c.location,
        "notes": c.notes,
        "priority": c.priority,
        "owner_company": c.owner_company,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("")
def list_companies(
    owner: Optional[str] = None,
    priority: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    q = db.query(WatchListCompany)
    if active_only:
        q = q.filter(WatchListCompany.is_active == True)
    if owner and owner != "all":
        q = q.filter(WatchListCompany.owner_company.in_([owner, "both"]))
    if priority:
        q = q.filter(WatchListCompany.priority == priority)
    companies = q.order_by(
        WatchListCompany.priority.desc(),
        WatchListCompany.name
    ).all()
    return {"companies": [_serialize(c) for c in companies], "total": len(companies)}


@router.post("")
def add_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    name = _normalize_name(payload.name)
    # Duplicate check
    existing = db.query(WatchListCompany).filter(
        WatchListCompany.name.ilike(f"%{name}%")
    ).first()
    if existing:
        raise HTTPException(400, f"'{name}' zaten listede mevcut.")

    company = WatchListCompany(
        name=name,
        raw_name=payload.name,
        aliases=payload.aliases or [],
        sector=payload.sector,
        location=payload.location,
        notes=payload.notes,
        priority=payload.priority or "medium",
        owner_company=payload.owner_company or "both",
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return _serialize(company)


@router.patch("/{company_id}")
def update_company(
    company_id: int,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
):
    company = db.query(WatchListCompany).get(company_id)
    if not company:
        raise HTTPException(404, "Şirket bulunamadı.")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(company, field, val)
    company.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(company)
    return _serialize(company)


@router.delete("/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(WatchListCompany).get(company_id)
    if not company:
        raise HTTPException(404, "Şirket bulunamadı.")
    db.delete(company)
    db.commit()
    return {"success": True}


@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """CSV veya XLSX dosyasından toplu şirket yükle."""
    content = await file.read()
    filename = file.filename.lower() if file.filename else ""

    rows = []

    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
            ws = wb.active
            headers = [str(c.value).strip().lower() if c.value else "" for c in next(ws.iter_rows())]
            for row in ws.iter_rows(min_row=2, values_only=True):
                rows.append(dict(zip(headers, [str(v).strip() if v is not None else "" for v in row])))
        except Exception as e:
            raise HTTPException(400, f"XLSX okunamadı: {e}")

    else:
        # CSV
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        reader = csv.DictReader(io.StringIO(text))
        rows = [{k.strip().lower(): (v.strip() if v else "") for k, v in row.items()} for row in reader]

    added = 0
    skipped = 0
    errors = []

    for row in rows:
        name = row.get("company_name") or row.get("name") or row.get("şirket") or ""
        if not name:
            skipped += 1
            continue
        name = _normalize_name(name)

        # Alias listesi
        aliases_raw = row.get("brand_aliases") or row.get("aliases") or ""
        aliases = [a.strip() for a in aliases_raw.split("|") if a.strip()] if aliases_raw else []

        owner = (row.get("owner_company") or "both").lower().strip()
        if owner not in ("treng", "irda", "both"):
            owner = "both"

        priority = (row.get("priority") or "medium").lower().strip()
        if priority not in ("high", "medium", "low"):
            priority = "medium"

        # Duplicate check
        existing = db.query(WatchListCompany).filter(
            WatchListCompany.name.ilike(name)
        ).first()
        if existing:
            skipped += 1
            continue

        try:
            company = WatchListCompany(
                name=name,
                raw_name=row.get("company_name") or name,
                aliases=aliases,
                sector=row.get("sector") or None,
                location=row.get("location") or None,
                notes=row.get("notes") or None,
                priority=priority,
                owner_company=owner,
            )
            db.add(company)
            added += 1
        except Exception as e:
            errors.append(str(e))

    db.commit()
    return {
        "success": True,
        "added": added,
        "skipped": skipped,
        "errors": errors[:5],
    }


@router.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    """Takip listesini CSV olarak indir."""
    from fastapi.responses import StreamingResponse
    companies = db.query(WatchListCompany).filter(WatchListCompany.is_active == True).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["company_name", "brand_aliases", "sector", "location", "notes", "priority", "owner_company"])
    for c in companies:
        writer.writerow([
            c.name,
            "|".join(c.aliases) if c.aliases else "",
            c.sector or "",
            c.location or "",
            c.notes or "",
            c.priority or "medium",
            c.owner_company or "both",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=takip_listesi.csv"}
    )
