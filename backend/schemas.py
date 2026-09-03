from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from models import ProficiencyLevel, ApplicationStage


# ---------- Auth ----------
class StudentRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    branch: Optional[str] = ""
    batch_year: Optional[int] = 0


class AdminStudentIn(BaseModel):
    name: str
    email: EmailStr
    branch: str = ""
    batch_year: int = 0
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


# ---------- Student ----------
class StudentProfileUpdate(BaseModel):
    name: Optional[str] = None
    branch: Optional[str] = None
    batch_year: Optional[int] = None
    phone: Optional[str] = None
    photo_url: Optional[str] = None


class SkillOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class StudentSkillIn(BaseModel):
    skill_name: str
    level: ProficiencyLevel = ProficiencyLevel.beginner


class StudentSkillOut(BaseModel):
    id: int
    skill: SkillOut
    level: ProficiencyLevel

    class Config:
        from_attributes = True


class CGPAIn(BaseModel):
    semester: int
    cgpa: float


class CGPAOut(BaseModel):
    id: int
    semester: int
    cgpa: float

    class Config:
        from_attributes = True


class StudentOut(BaseModel):
    id: int
    name: str
    email: str
    branch: str
    batch_year: int
    phone: str
    photo_url: str
    overall_cgpa: float
    skills: List[StudentSkillOut] = []
    cgpa_records: List[CGPAOut] = []

    class Config:
        from_attributes = True


# ---------- Company ----------
class CompanyIn(BaseModel):
    name: str
    role: str = ""
    package_ctc: float = 0.0
    min_cgpa: float = 0.0
    eligible_branches: str = ""  # comma-separated, blank = all branches
    description: str = ""
    required_skill_names: List[str] = []


class CompanyOut(BaseModel):
    id: int
    name: str
    role: str
    package_ctc: float
    min_cgpa: float
    eligible_branches: str
    description: str
    required_skills: List[SkillOut] = Field(default=[], validation_alias="required_skills_list")

    class Config:
        from_attributes = True
        populate_by_name = True


class EligibilityResult(BaseModel):
    company: CompanyOut
    eligible: bool
    reasons: List[str] = []
    missing_skills: List[str] = []


# ---------- Applications ----------
class ApplicationOut(BaseModel):
    id: int
    company: CompanyOut
    stage: ApplicationStage
    applied_at: datetime

    class Config:
        from_attributes = True


class ApplicationStageUpdate(BaseModel):
    stage: ApplicationStage


# ---------- Admin analytics ----------
class BranchStat(BaseModel):
    branch: str
    placed: int
    total: int


class AnalyticsOut(BaseModel):
    total_students: int
    total_companies: int
    total_placed: int
    placement_percentage: float
    branch_stats: List[BranchStat]
    package_distribution: List[float]
