"""
Seed the database with a realistic demo dataset so the app doesn't look
empty during a demo: sample students (with skills + CGPA), companies with
eligibility criteria, a couple of applications, and one admin account.

Run with: python seed.py
"""
import random
from datetime import datetime, timedelta

from database import engine, SessionLocal, Base
import models
from auth import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

print("Clearing existing data...")
for table in [models.Application, models.CompanySkillRequirement, models.Company,
              models.StudentSkill, models.CGPARecord, models.Student,
              models.Skill, models.Admin]:
    db.query(table).delete()
db.commit()

# ---------------- Skills ----------------
skill_names = ["Python", "Java", "SQL", "React", "JavaScript", "C++", "Data Structures",
               "Machine Learning", "Node.js", "AWS", "Git", "HTML/CSS", "Django", "Flask",
               "Docker", "REST APIs"]
skills = {}
for name in skill_names:
    s = models.Skill(name=name)
    db.add(s)
    db.flush()
    skills[name] = s
db.commit()

# ---------------- Admin ----------------
admin = models.Admin(email="admin@campus.edu", hashed_password=hash_password("admin123"), name="Placement Officer")
db.add(admin)
db.commit()
print("Admin login -> email: admin@campus.edu | password: admin123")

# ---------------- Students ----------------
branches = ["Computer Science", "Information Technology", "Electronics", "Mechanical"]
first_names = ["Aarav", "Vihaan", "Diya", "Ananya", "Ishaan", "Kavya", "Rohan", "Sneha",
               "Aditya", "Priya", "Karan", "Meera", "Arjun", "Neha", "Yash", "Riya", "Dev", "Pooja"]
last_names = ["Sharma", "Verma", "Iyer", "Nair", "Gupta", "Reddy", "Singh", "Rao", "Mehta", "Kulkarni"]

students = []
for i in range(18):
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    email = f"student{i+1}@campus.edu"
    student = models.Student(
        name=name,
        email=email,
        hashed_password=hash_password("password123"),
        branch=random.choice(branches),
        batch_year=2026,
        phone=f"9{random.randint(100000000, 999999999)}",
    )
    db.add(student)
    db.flush()

    # CGPA across up to 6 semesters
    base = round(random.uniform(6.0, 9.5), 2)
    for sem in range(1, random.randint(4, 7)):
        drift = round(random.uniform(-0.3, 0.3), 2)
        db.add(models.CGPARecord(student_id=student.id, semester=sem, cgpa=max(5.0, min(10.0, base + drift))))

    # Random skills (generous range so eligibility isn't near-impossible in the demo)
    chosen_skills = random.sample(skill_names, k=random.randint(6, 11))
    for sk in chosen_skills:
        level = random.choice(list(models.ProficiencyLevel))
        db.add(models.StudentSkill(student_id=student.id, skill_id=skills[sk].id, level=level))

    students.append(student)

db.commit()
print(f"Created {len(students)} students. Default password for all: password123")

# ---------------- Companies ----------------
company_defs = [
    {"name": "TechNova Solutions", "role": "Software Engineer", "package_ctc": 12.0,
     "min_cgpa": 7.0, "eligible_branches": "Computer Science,Information Technology",
     "skills": ["Python", "SQL"],
     "description": "Product-based company building cloud-native SaaS tools."},
    {"name": "DataForge Analytics", "role": "Data Analyst", "package_ctc": 9.5,
     "min_cgpa": 6.5, "eligible_branches": "",
     "skills": ["Python", "Machine Learning"],
     "description": "Analytics consultancy working with retail and fintech clients."},
    {"name": "CloudSphere Systems", "role": "Cloud Engineer", "package_ctc": 15.0,
     "min_cgpa": 8.0, "eligible_branches": "Computer Science,Information Technology,Electronics",
     "skills": ["AWS", "Git"],
     "description": "Infrastructure-as-code and DevOps for enterprise clients."},
    {"name": "Pixel & Co", "role": "Frontend Developer", "package_ctc": 8.0,
     "min_cgpa": 6.0, "eligible_branches": "",
     "skills": ["React", "JavaScript"],
     "description": "Digital product studio crafting web experiences."},
    {"name": "CoreLogic Systems", "role": "Backend Developer", "package_ctc": 11.0,
     "min_cgpa": 7.5, "eligible_branches": "Computer Science,Information Technology",
     "skills": ["Java", "SQL"],
     "description": "Enterprise backend systems for the banking sector."},
    {"name": "InnoMech Robotics", "role": "Embedded Systems Engineer", "package_ctc": 10.0,
     "min_cgpa": 7.0, "eligible_branches": "Electronics,Mechanical",
     "skills": ["C++", "Git"],
     "description": "Robotics and automation hardware manufacturer."},
]

companies = []
for i, cdef in enumerate(company_defs):
    company = models.Company(
        name=cdef["name"], role=cdef["role"], package_ctc=cdef["package_ctc"],
        min_cgpa=cdef["min_cgpa"], eligible_branches=cdef["eligible_branches"],
        description=cdef["description"],
        drive_date=datetime.utcnow() + timedelta(days=i * 3),
    )
    db.add(company)
    db.flush()
    for sk in cdef["skills"]:
        db.add(models.CompanySkillRequirement(company_id=company.id, skill_id=skills[sk].id))
    companies.append(company)

db.commit()
print(f"Created {len(companies)} companies.")

# ---------------- Sample applications ----------------
from eligibility import check_eligibility

stages = list(models.ApplicationStage)
applied_count = 0
for student in students:
    eligible_companies = [c for c in companies if check_eligibility(student, c)[0]]
    for company in random.sample(eligible_companies, k=min(len(eligible_companies), random.randint(1, 3))):
        existing = db.query(models.Application).filter(
            models.Application.student_id == student.id,
            models.Application.company_id == company.id,
        ).first()
        if not existing:
            stage = random.choice(stages)
            db.add(models.Application(student_id=student.id, company_id=company.id, stage=stage))
            applied_count += 1

db.commit()
print(f"Created {applied_count} sample applications.")
print("\nSeed complete. Sample login -> student1@campus.edu / password123")
db.close()
