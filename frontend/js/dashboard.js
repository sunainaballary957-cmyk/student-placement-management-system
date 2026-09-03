requireAuth("student");

const STAGES = ["Applied", "Shortlisted", "Interview", "Offer", "Rejected"];
let currentStudent = null;
let allSkillSuggestions = [];

// ---------- Navigation ----------
document.querySelectorAll(".nav-item").forEach(item => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(i => i.classList.remove("active"));
    item.classList.add("active");
    document.querySelectorAll("main > section").forEach(s => s.classList.add("hidden"));
    document.getElementById(`section-${item.dataset.section}`).classList.remove("hidden");
  });
});

// ---------- Load everything ----------
async function loadProfile() {
  currentStudent = await api("/students/me");
  document.getElementById("sidebarName").textContent = currentStudent.name;
  document.getElementById("sidebarBranch").textContent = currentStudent.branch || "No branch set";
  document.getElementById("avatarInitials").textContent = initials(currentStudent.name);
  document.getElementById("overviewName").textContent = currentStudent.name.split(" ")[0];

  document.getElementById("pName").value = currentStudent.name;
  document.getElementById("pEmail").value = currentStudent.email;
  document.getElementById("pBranch").value = currentStudent.branch || "Computer Science";
  document.getElementById("pYear").value = currentStudent.batch_year || "";
  document.getElementById("pPhone").value = currentStudent.phone || "";

  document.getElementById("statCgpa").textContent = currentStudent.overall_cgpa.toFixed(2);
  document.getElementById("statSkills").textContent = currentStudent.skills.length;

  renderSkillChips();
  renderCgpa();
}

document.getElementById("profileForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/students/me", {
      method: "PUT",
      body: {
        name: document.getElementById("pName").value,
        branch: document.getElementById("pBranch").value,
        batch_year: parseInt(document.getElementById("pYear").value, 10) || 0,
        phone: document.getElementById("pPhone").value,
      },
    });
    toast("Profile updated");
    loadProfile();
  } catch (err) { toast(err.message, "error"); }
});

// ---------- Skills ----------
function renderSkillChips() {
  const wrap = document.getElementById("skillChips");
  wrap.innerHTML = "";
  if (!currentStudent.skills.length) {
    wrap.innerHTML = `<span style="color:var(--text-muted); font-size:0.86rem;">No skills added yet — add your first one above.</span>`;
    return;
  }
  currentStudent.skills.forEach(s => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.innerHTML = `${s.skill.name} <span class="level">· ${s.level}</span> <button title="Remove">×</button>`;
    chip.querySelector("button").onclick = async () => {
      try {
        await api(`/students/me/skills/${s.id}`, { method: "DELETE" });
        toast("Skill removed");
        await loadProfile();
      } catch (err) { toast(err.message, "error"); }
    };
    wrap.appendChild(chip);
  });
}

document.getElementById("addSkillBtn").addEventListener("click", async () => {
  const name = document.getElementById("skillNameInput").value.trim();
  const level = document.getElementById("skillLevelInput").value;
  if (!name) return;
  try {
    await api("/students/me/skills", { method: "POST", body: { skill_name: name, level } });
    document.getElementById("skillNameInput").value = "";
    toast(`Added ${name}`);
    await loadProfile();
  } catch (err) { toast(err.message, "error"); }
});

async function loadSkillSuggestions() {
  allSkillSuggestions = await api("/skills/suggestions");
  const list = document.getElementById("skillSuggestions");
  list.innerHTML = allSkillSuggestions.map(s => `<option value="${s.name}"></option>`).join("");
}

// ---------- CGPA ----------
function renderCgpa() {
  document.getElementById("cgpaOverall").textContent = currentStudent.overall_cgpa.toFixed(2) + " / 10";
  const bars = document.getElementById("cgpaBars");
  bars.innerHTML = "";
  const records = [...currentStudent.cgpa_records].sort((a, b) => a.semester - b.semester);
  if (!records.length) {
    bars.innerHTML = `<p style="color:var(--text-muted); font-size:0.86rem;">No semester records yet.</p>`;
    return;
  }
  records.forEach(r => {
    const row = document.createElement("div");
    row.style.marginBottom = "12px";
    row.innerHTML = `
      <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:4px;">
        <span>Semester ${r.semester}</span><span class="mono">${r.cgpa.toFixed(2)}</span>
      </div>
      <div class="progress-bar"><div class="progress-bar-fill" style="width:${(r.cgpa / 10) * 100}%;"></div></div>`;
    bars.appendChild(row);
  });
}

document.getElementById("cgpaForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/students/me/cgpa", {
      method: "POST",
      body: {
        semester: parseInt(document.getElementById("cgpaSemester").value, 10),
        cgpa: parseFloat(document.getElementById("cgpaValue").value),
      },
    });
    toast("CGPA saved");
    document.getElementById("cgpaForm").reset();
    await loadProfile();
  } catch (err) { toast(err.message, "error"); }
});

// ---------- Companies + eligibility beacons ----------
function beaconFor(result) {
  if (result.eligible) return { cls: "beacon-eligible", label: "Eligible" };
  if (result.missing_skills.length && result.reasons.length === 1) return { cls: "beacon-gap", label: "Skill gap" };
  return { cls: "beacon-ineligible", label: "Not eligible" };
}

let myApplicationsCache = [];

async function loadCompanies() {
  const [eligibility, applications] = await Promise.all([
    api("/companies/eligibility"),
    api("/applications/me"),
  ]);
  myApplicationsCache = applications;
  const appliedIds = new Set(applications.map(a => a.company.id));

  document.getElementById("statEligible").textContent = eligibility.filter(r => r.eligible).length;
  document.getElementById("statApplications").textContent = applications.length;

  const list = document.getElementById("companiesList");
  list.innerHTML = "";
  eligibility.forEach(result => {
    const b = beaconFor(result);
    const alreadyApplied = appliedIds.has(result.company.id);
    const card = document.createElement("div");
    card.className = "card company-card";
    card.innerHTML = `
      <div class="company-card-top">
        <div>
          <div class="company-name">${result.company.name}</div>
          <div class="company-role">${result.company.role}</div>
        </div>
        <div class="beacon ${b.cls}"><span class="dot"></span>${b.label}</div>
      </div>
      <div class="company-package">₹${result.company.package_ctc} LPA <span style="color:var(--text-muted); font-family:var(--font-body); font-size:0.78rem;"> · min CGPA ${result.company.min_cgpa}</span></div>
      <p style="font-size:0.85rem;">${result.company.description || ""}</p>
      <div class="skill-tag-row">
        ${result.company.required_skills.map(s => `<span class="skill-tag ${result.missing_skills.includes(s.name) ? "missing" : ""}">${s.name}</span>`).join("")}
      </div>
      ${result.reasons.length ? `<ul class="reason-list">${result.reasons.map(r => `<li>${r}</li>`).join("")}</ul>` : ""}
      <button class="btn ${alreadyApplied ? "btn-secondary" : "btn-primary"} btn-sm" ${(!result.eligible || alreadyApplied) ? "disabled" : ""} data-id="${result.company.id}">
        ${alreadyApplied ? "Already applied" : "Apply now"}
      </button>
    `;
    if (result.eligible && !alreadyApplied) {
      card.querySelector("button").addEventListener("click", async (e) => {
        try {
          await api(`/applications/${result.company.id}`, { method: "POST" });
          toast(`Applied to ${result.company.name}`);
          await loadCompanies();
          await renderApplications();
        } catch (err) { toast(err.message, "error"); }
      });
    }
    list.appendChild(card);
  });
}

// ---------- Applications ----------
function stepIndex(stage) {
  if (stage === "Rejected") return -1;
  return STAGES.indexOf(stage);
}

function renderStepper(stage) {
  const stages = ["Applied", "Shortlisted", "Interview", "Offer"];
  const rejected = stage === "Rejected";
  const currentIdx = rejected ? stages.length : stages.indexOf(stage);
  return `<div class="stepper">${stages.map((s, i) => {
    let cls = "";
    if (rejected) cls = i === 0 ? "done rejected" : "";
    else if (i < currentIdx) cls = "done";
    else if (i === currentIdx) cls = "current";
    return `<div class="step ${cls}"><div class="step-line"></div><div class="step-dot">${i + 1}</div><div class="step-label">${s}</div></div>`;
  }).join("")}</div>${rejected ? `<div style="text-align:center;"><span class="beacon beacon-ineligible"><span class="dot"></span>Rejected</span></div>` : ""}`;
}

async function renderApplications() {
  const applications = myApplicationsCache.length ? myApplicationsCache : await api("/applications/me");
  const list = document.getElementById("applicationsList");
  const overviewTimeline = document.getElementById("overviewTimeline");
  list.innerHTML = "";

  if (!applications.length) {
    list.innerHTML = `<div class="card empty-state">You haven't applied anywhere yet — head to the Companies tab and apply where you're eligible.</div>`;
    overviewTimeline.innerHTML = `<div class="empty-state">No applications yet. Your pipeline will appear here.</div>`;
    return;
  }

  applications.forEach(a => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <div class="company-name">${a.company.name}</div>
        <span class="eyebrow">${new Date(a.applied_at).toLocaleDateString()}</span>
      </div>
      ${renderStepper(a.stage)}
    `;
    list.appendChild(card);
  });

  // Overview timeline = most recent 3
  overviewTimeline.innerHTML = applications.slice(0, 3).map(a => `
    <div style="margin-bottom:18px;">
      <div style="font-size:0.88rem; font-weight:600; margin-bottom:6px;">${a.company.name}</div>
      ${renderStepper(a.stage)}
    </div>`).join("");
}

// ---------- Boot ----------
(async function init() {
  try {
    await loadProfile();
    await loadSkillSuggestions();
    await renderApplications();
    await loadCompanies();
  } catch (err) {
    toast(err.message, "error");
  }
})();
