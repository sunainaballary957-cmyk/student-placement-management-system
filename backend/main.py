from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os

import models
import schemas
from database import engine, get_db, Base
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_student, get_current_admin
)
from eligibility import check_eligibility

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Student Placement Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


# ============================================================
# AUTH
# ============================================================
@app.post("/auth/register", response_model=schemas.StudentOut)
def register(payload: schemas.StudentRegister, db: Session = Depends(get_db)):
    existing = db.query(models.Student).filter(models.Student.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    student = models.Student(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        branch=payload.branch or "",
        batch_year=payload.batch_year or 0,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@app.post("/auth/login", response_model=schemas.Token)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    # Try student first
    student = db.query(models.Student).filter(models.Student.email == payload.email).first()
    if student and verify_password(payload.password, student.hashed_password):
        token = create_access_token({"sub": str(student.id), "role": "student"})
        return {"access_token": token, "role": "student"}

    # Then admin
    admin = db.query(models.Admin).filter(models.Admin.email == payload.email).first()
    if admin and verify_password(payload.password, admin.hashed_password):
        token = create_access_token({"sub": str(admin.id), "role": "admin"})
        return {"access_token": token, "role": "admin"}

    raise HTTPException(status_code=401, detail="Invalid email or password")


# ============================================================
# STUDENT PROFILE
# ============================================================
@app.get("/students/me", response_model=schemas.StudentOut)
def get_my_profile(current: models.Student = Depends(get_current_student)):
    return current


@app.put("/students/me", response_model=schemas.StudentOut)
def update_my_profile(
    payload: schemas.StudentProfileUpdate,
    current: models.Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(current, field, value)
    db.commit()
    db.refresh(current)
    return current


@app.post("/students/me/skills", response_model=schemas.StudentSkillOut)
def add_my_skill(
    payload: schemas.StudentSkillIn,
    current: models.Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    skill = db.query(models.Skill).filter(models.Skill.name.ilike(payload.skill_name)).first()
    if not skill:
        skill = models.Skill(name=payload.skill_name.strip())
        db.add(skill)
        db.commit()
        db.refresh(skill)

    existing = db.query(models.StudentSkill).filter(
        models.StudentSkill.student_id == current.id,
        models.StudentSkill.skill_id == skill.id,
    ).first()
    if existing:
        existing.level = payload.level
        db.commit()
        db.refresh(existing)
        return existing

    link = models.StudentSkill(student_id=current.id, skill_id=skill.id, level=payload.level)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@app.delete("/students/me/skills/{skill_link_id}")
def remove_my_skill(
    skill_link_id: int,
    current: models.Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    link = db.query(models.StudentSkill).filter(
        models.StudentSkill.id == skill_link_id,
        models.StudentSkill.student_id == current.id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Skill not found on profile")
    db.delete(link)
    db.commit()
    return {"detail": "removed"}


@app.post("/students/me/cgpa", response_model=schemas.CGPAOut)
def add_or_update_cgpa(
    payload: schemas.CGPAIn,
    current: models.Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    record = db.query(models.CGPARecord).filter(
        models.CGPARecord.student_id == current.id,
        models.CGPARecord.semester == payload.semester,
    ).first()
    if record:
        record.cgpa = payload.cgpa
    else:
        record = models.CGPARecord(student_id=current.id, semester=payload.semester, cgpa=payload.cgpa)
        db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/skills/suggestions", response_model=List[schemas.SkillOut])
def skill_suggestions(db: Session = Depends(get_db)):
    return db.query(models.Skill).order_by(models.Skill.name).all()


# ============================================================
# COMPANIES + ELIGIBILITY (student-facing)
# ============================================================
@app.get("/companies", response_model=List[schemas.CompanyOut])
def list_companies(db: Session = Depends(get_db)):
    return db.query(models.Company).order_by(models.Company.drive_date.desc()).all()


@app.get("/companies/eligibility", response_model=List[schemas.EligibilityResult])
def my_eligibility(
    current: models.Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    companies = db.query(models.Company).all()
    results = []
    for company in companies:
        eligible, reasons, missing = check_eligibility(current, company)
        results.append(schemas.EligibilityResult(
            company=company, eligible=eligible, reasons=reasons, missing_skills=missing
        ))
    return results


# ============================================================
# APPLICATIONS
# ============================================================
@app.post("/applications/{company_id}", response_model=schemas.ApplicationOut)
def apply_to_company(
    company_id: int,
    current: models.Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    eligible, reasons, _ = check_eligibility(current, company)
    if not eligible:
        raise HTTPException(status_code=400, detail=f"Not eligible: {'; '.join(reasons)}")

    existing = db.query(models.Application).filter(
        models.Application.student_id == current.id,
        models.Application.company_id == company_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already applied to this company")

    application = models.Application(student_id=current.id, company_id=company_id)
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@app.get("/applications/me", response_model=List[schemas.ApplicationOut])
def my_applications(
    current: models.Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    return db.query(models.Application).filter(models.Application.student_id == current.id).all()


@app.put("/applications/{application_id}/stage", response_model=schemas.ApplicationOut)
def update_application_stage(
    application_id: int,
    payload: schemas.ApplicationStageUpdate,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    application = db.query(models.Application).filter(models.Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    application.stage = payload.stage
    db.commit()
    db.refresh(application)
    return application


# ============================================================
# ADMIN
# ============================================================
@app.post("/admin/companies", response_model=schemas.CompanyOut)
def create_company(
    payload: schemas.CompanyIn,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    company = models.Company(
        name=payload.name, role=payload.role, package_ctc=payload.package_ctc,
        min_cgpa=payload.min_cgpa, eligible_branches=payload.eligible_branches,
        description=payload.description,
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    for skill_name in payload.required_skill_names:
        skill = db.query(models.Skill).filter(models.Skill.name.ilike(skill_name)).first()
        if not skill:
            skill = models.Skill(name=skill_name.strip())
            db.add(skill)
            db.commit()
            db.refresh(skill)
        db.add(models.CompanySkillRequirement(company_id=company.id, skill_id=skill.id))
    db.commit()
    db.refresh(company)
    return company


@app.post("/admin/students", response_model=schemas.StudentOut)
def create_student(
    payload: schemas.AdminStudentIn,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    existing = db.query(models.Student).filter(models.Student.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    student = models.Student(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        branch=payload.branch,
        batch_year=payload.batch_year,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@app.delete("/admin/companies/{company_id}")
def delete_company(
    company_id: int,
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()
    return {"detail": "deleted"}


@app.get("/admin/students", response_model=List[schemas.StudentOut])
def list_students(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return db.query(models.Student).all()


@app.get("/admin/analytics", response_model=schemas.AnalyticsOut)
def analytics(
    admin: models.Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    students = db.query(models.Student).all()
    companies = db.query(models.Company).all()
    applications = db.query(models.Application).all()

    placed_student_ids = {a.student_id for a in applications if a.stage == models.ApplicationStage.offer}
    total_students = len(students)
    total_placed = len(placed_student_ids)
    placement_pct = round((total_placed / total_students) * 100, 1) if total_students else 0.0

    branch_map = {}
    for s in students:
        b = s.branch or "Unspecified"
        branch_map.setdefault(b, {"placed": 0, "total": 0})
        branch_map[b]["total"] += 1
        if s.id in placed_student_ids:
            branch_map[b]["placed"] += 1
    branch_stats = [schemas.BranchStat(branch=b, placed=v["placed"], total=v["total"]) for b, v in branch_map.items()]

    package_distribution = [c.package_ctc for c in companies]

    return schemas.AnalyticsOut(
        total_students=total_students,
        total_companies=len(companies),
        total_placed=total_placed,
        placement_percentage=placement_pct,
        branch_stats=branch_stats,
        package_distribution=package_distribution,
    )


# ============================================================
# STATIC FRONTEND
# ============================================================
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/{page_name}.html")
def serve_page(page_name: str):
    path = os.path.join(FRONTEND_DIR, f"{page_name}.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Page not found")
