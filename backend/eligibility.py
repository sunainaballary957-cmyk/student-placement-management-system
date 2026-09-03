"""
The eligibility engine.

Given a student and a company, this works out not just a yes/no answer but
*why* -- which is the feature that makes this project different from a
plain CRUD placement tracker. It checks CGPA, branch, and required skills,
and returns human-readable reasons plus the exact list of missing skills
so the frontend can render a "skill gap" recommendation.
"""
from typing import List
import models


def check_eligibility(student: models.Student, company: models.Company):
    reasons: List[str] = []
    missing_skills: List[str] = []

    # 1. CGPA check
    overall = student.overall_cgpa
    if overall < company.min_cgpa:
        shortfall = round(company.min_cgpa - overall, 2)
        reasons.append(f"CGPA short by {shortfall} (need {company.min_cgpa}, have {overall})")

    # 2. Branch check
    if company.eligible_branches.strip():
        allowed = {b.strip().lower() for b in company.eligible_branches.split(",") if b.strip()}
        if student.branch.strip().lower() not in allowed:
            reasons.append(f"Branch '{student.branch}' not eligible (allowed: {company.eligible_branches})")

    # 3. Skill check
    student_skill_names = {link.skill.name.lower() for link in student.skills}
    required_skill_names = [req.skill.name for req in company.required_skills]
    for req_name in required_skill_names:
        if req_name.lower() not in student_skill_names:
            missing_skills.append(req_name)

    if missing_skills:
        reasons.append(f"Missing skills: {', '.join(missing_skills)}")

    eligible = len(reasons) == 0
    return eligible, reasons, missing_skills
