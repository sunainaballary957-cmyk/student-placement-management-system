from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, DateTime, Table, Enum, Text
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from database import Base


class ProficiencyLevel(str, enum.Enum):
    beginner = "Beginner"
    intermediate = "Intermediate"
    advanced = "Advanced"


class ApplicationStage(str, enum.Enum):
    applied = "Applied"
    shortlisted = "Shortlisted"
    interview = "Interview"
    offer = "Offer"
    rejected = "Rejected"


class Skill(Base):
    __tablename__ = "skills"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), unique=True, nullable=False)

    student_links = relationship("StudentSkill", back_populates="skill")


class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(200), nullable=False)
    branch = Column(String(80), default="")
    batch_year = Column(Integer, default=0)
    phone = Column(String(20), default="")
    photo_url = Column(String(300), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    skills = relationship("StudentSkill", back_populates="student", cascade="all, delete-orphan")
    cgpa_records = relationship("CGPARecord", back_populates="student", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="student", cascade="all, delete-orphan")

    @property
    def overall_cgpa(self):
        if not self.cgpa_records:
            return 0.0
        return round(sum(r.cgpa for r in self.cgpa_records) / len(self.cgpa_records), 2)


class StudentSkill(Base):
    __tablename__ = "student_skills"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)
    level = Column(Enum(ProficiencyLevel), default=ProficiencyLevel.beginner)

    student = relationship("Student", back_populates="skills")
    skill = relationship("Skill", back_populates="student_links")


class CGPARecord(Base):
    __tablename__ = "cgpa_records"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    semester = Column(Integer, nullable=False)
    cgpa = Column(Float, nullable=False)

    student = relationship("Student", back_populates="cgpa_records")


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    role = Column(String(150), default="")
    package_ctc = Column(Float, default=0.0)  # in LPA
    min_cgpa = Column(Float, default=0.0)
    eligible_branches = Column(String(300), default="")  # comma separated, empty = all
    description = Column(Text, default="")
    drive_date = Column(DateTime, default=datetime.utcnow)

    required_skills = relationship("CompanySkillRequirement", back_populates="company", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="company", cascade="all, delete-orphan")

    @property
    def required_skills_list(self):
        """Flattened list of Skill objects (rather than the join-table rows)."""
        return [req.skill for req in self.required_skills]


class CompanySkillRequirement(Base):
    __tablename__ = "company_skill_requirements"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id"), nullable=False)

    company = relationship("Company", back_populates="required_skills")
    skill = relationship("Skill")


class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    stage = Column(Enum(ApplicationStage), default=ApplicationStage.applied)
    applied_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="applications")
    company = relationship("Company", back_populates="applications")


class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    name = Column(String(120), default="Admin")
