requireAuth("admin");

document.querySelectorAll(".nav-item").forEach(item => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(i => i.classList.remove("active"));
    item.classList.add("active");
    document.querySelectorAll("main > section").forEach(s => s.classList.add("hidden"));
    const section = document.getElementById(`section-${item.dataset.section}`);
    section.classList.remove("hidden");
    section.classList.remove("section-enter");
    requestAnimationFrame(() => section.classList.add("section-enter"));
  });
});

const CHART_COLORS = {
  brand: "#6d7cff",
  green: "#3ddc97",
  amber: "#f5b942",
  red: "#f2607a",
  grid: "rgba(255,255,255,0.09)",
  text: "#9aa7b8",
};

function prepareCanvas(canvas) {
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 400;
  const height = canvas.clientHeight || 220;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  const context = canvas.getContext("2d");
  context.scale(ratio, ratio);
  context.font = "12px Inter, sans-serif";
  return { context, width, height };
}

function emptyChart(canvas, message = "No data available") {
  const { context, width, height } = prepareCanvas(canvas);
  context.fillStyle = CHART_COLORS.text;
  context.textAlign = "center";
  context.fillText(message, width / 2, height / 2);
}

function drawBarChart(canvas, stats) {
  if (!stats.length) return emptyChart(canvas);
  const { context, width, height } = prepareCanvas(canvas);
  const left = 42, right = 12, top = 14, bottom = 42;
  const plotHeight = height - top - bottom;
  const max = Math.max(...stats.map(s => s.total), 1);
  const groupWidth = (width - left - right) / stats.length;
  const barWidth = Math.min(24, groupWidth * 0.28);
  context.strokeStyle = CHART_COLORS.grid;
  context.fillStyle = CHART_COLORS.text;
  context.textAlign = "right";
  context.font = "11px Inter, sans-serif";
  for (let tick = 0; tick <= max; tick += Math.max(1, Math.ceil(max / 4))) {
    const y = top + plotHeight - (tick / max) * plotHeight;
    context.beginPath(); context.moveTo(left, y); context.lineTo(width - right, y); context.stroke();
    context.fillText(tick, left - 8, y + 4);
  }
  stats.forEach((stat, index) => {
    const x = left + groupWidth * index + groupWidth / 2;
    const placedHeight = (stat.placed / max) * plotHeight;
    const totalHeight = (stat.total / max) * plotHeight;
    context.fillStyle = "rgba(255,255,255,0.14)";
    context.fillRect(x - barWidth / 2, top + plotHeight - totalHeight, barWidth, totalHeight);
    context.fillStyle = CHART_COLORS.green;
    context.fillRect(x - barWidth / 2, top + plotHeight - placedHeight, barWidth, placedHeight);
    context.fillStyle = CHART_COLORS.text;
    context.textAlign = "center";
    context.fillText(stat.branch.length > 13 ? `${stat.branch.slice(0, 12)}…` : stat.branch, x, height - 15);
  });
}

function drawDoughnutChart(canvas, placed, total) {
  if (!total) return emptyChart(canvas, "No placement data yet");
  const { context, width, height } = prepareCanvas(canvas);
  const centerX = width / 2, centerY = height / 2 - 12, radius = Math.min(width, height) * 0.28;
  const placedAngle = (placed / total) * Math.PI * 2;
  context.lineWidth = 24;
  context.strokeStyle = "rgba(255,255,255,0.12)";
  context.beginPath(); context.arc(centerX, centerY, radius, 0, Math.PI * 2); context.stroke();
  context.strokeStyle = CHART_COLORS.green;
  context.beginPath(); context.arc(centerX, centerY, radius, -Math.PI / 2, -Math.PI / 2 + placedAngle); context.stroke();
  context.fillStyle = CHART_COLORS.text;
  context.textAlign = "center";
  context.font = "700 20px Space Grotesk, sans-serif";
  context.fillText(`${placed}/${total}`, centerX, centerY + 7);
  context.font = "11px Inter, sans-serif";
  context.fillText("placed", centerX, height - 10);
}

function drawLineChart(canvas, values) {
  if (!values.length) return emptyChart(canvas);
  const { context, width, height } = prepareCanvas(canvas);
  const left = 30, right = 14, top = 14, bottom = 28;
  const plotHeight = height - top - bottom;
  const max = Math.max(...values, 1);
  const points = values.map((value, index) => ({
    x: left + (index / Math.max(values.length - 1, 1)) * (width - left - right),
    y: top + plotHeight - (value / max) * plotHeight,
  }));
  context.strokeStyle = CHART_COLORS.grid;
  context.beginPath(); context.moveTo(left, top); context.lineTo(left, top + plotHeight); context.lineTo(width - right, top + plotHeight); context.stroke();
  context.beginPath(); points.forEach((point, index) => index ? context.lineTo(point.x, point.y) : context.moveTo(point.x, point.y)); context.strokeStyle = CHART_COLORS.brand; context.lineWidth = 2; context.stroke();
  context.lineTo(points[points.length - 1].x, top + plotHeight); context.lineTo(points[0].x, top + plotHeight); context.closePath(); context.fillStyle = "rgba(109,124,255,0.15)"; context.fill();
  points.forEach(point => { context.fillStyle = CHART_COLORS.brand; context.beginPath(); context.arc(point.x, point.y, 3.5, 0, Math.PI * 2); context.fill(); });
  context.fillStyle = CHART_COLORS.text; context.font = "11px Inter, sans-serif"; context.textAlign = "center";
  values.forEach((value, index) => context.fillText(`₹${value}L`, points[index].x, height - 9));
}

async function loadAnalytics() {
  try {
    const data = await api("/admin/analytics");
    document.getElementById("statTotalStudents").textContent = data.total_students;
    document.getElementById("statTotalCompanies").textContent = data.total_companies;
    document.getElementById("statTotalPlaced").textContent = data.total_placed;
    document.getElementById("statPlacementPct").textContent = data.placement_percentage + "%";
    drawBarChart(document.getElementById("branchChart"), data.branch_stats || []);
    drawDoughnutChart(document.getElementById("pieChart"), data.total_placed, data.total_students);
    drawLineChart(document.getElementById("packageChart"), data.package_distribution || []);
  } catch (err) {
    ["statTotalStudents", "statTotalCompanies", "statTotalPlaced", "statPlacementPct"].forEach(id => {
      document.getElementById(id).textContent = "—";
    });
    toast(`Analytics unavailable: ${err.message}`, "error");
  }
}

// ---------- Companies management ----------
async function loadCompaniesAdmin() {
  const companies = await api("/companies");
  const list = document.getElementById("companiesAdminList");
  list.innerHTML = "";
  if (!companies.length) {
    list.innerHTML = `<div class="empty-state">No companies added yet.</div>`;
    return;
  }
  companies.forEach(c => {
    const row = document.createElement("div");
    row.className = "card card-tight";
    row.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:flex-start;">
        <div>
          <div class="company-name">${c.name}</div>
          <div class="company-role">${c.role} · ₹${c.package_ctc} LPA · min CGPA ${c.min_cgpa}</div>
          <div class="skill-tag-row" style="margin-top:8px;">
            ${c.required_skills.map(s => `<span class="skill-tag">${s.name}</span>`).join("")}
          </div>
        </div>
        <button class="btn btn-danger btn-sm" data-id="${c.id}">Remove</button>
      </div>
    `;
    row.querySelector("button").addEventListener("click", async () => {
      try {
        await api(`/admin/companies/${c.id}`, { method: "DELETE" });
        toast(`Removed ${c.name}`);
        loadCompaniesAdmin();
        loadAnalytics();
      } catch (err) { toast(err.message, "error"); }
    });
    list.appendChild(row);
  });
}

document.getElementById("companyForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const skills = document.getElementById("cSkills").value.split(",").map(s => s.trim()).filter(Boolean);
  try {
    await api("/admin/companies", {
      method: "POST",
      body: {
        name: document.getElementById("cName").value,
        role: document.getElementById("cRole").value,
        package_ctc: parseFloat(document.getElementById("cPackage").value) || 0,
        min_cgpa: parseFloat(document.getElementById("cMinCgpa").value) || 0,
        eligible_branches: document.getElementById("cBranches").value,
        description: document.getElementById("cDescription").value,
        required_skill_names: skills,
      },
    });
    toast("Company added");
    document.getElementById("companyForm").reset();
    loadCompaniesAdmin();
    loadAnalytics();
  } catch (err) { toast(err.message, "error"); }
});

document.getElementById("studentForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/admin/students", {
      method: "POST",
      body: {
        name: document.getElementById("sName").value,
        email: document.getElementById("sEmail").value,
        branch: document.getElementById("sBranch").value,
        batch_year: parseInt(document.getElementById("sBatch").value, 10),
        password: document.getElementById("sPassword").value,
      },
    });
    toast("Student added");
    document.getElementById("studentForm").reset();
    loadStudents();
    loadAnalytics();
  } catch (err) { toast(err.message, "error"); }
});

// ---------- Students table ----------
async function loadStudents() {
  const students = await api("/admin/students");
  const tbody = document.getElementById("studentsTableBody");
  tbody.innerHTML = students.length ? students.map(s => `
    <tr>
      <td>${s.name}</td>
      <td>${s.branch}</td>
      <td>${s.batch_year}</td>
      <td class="mono">${s.overall_cgpa.toFixed(2)}</td>
      <td>${s.skills.map(sk => sk.skill.name).join(", ") || "—"}</td>
    </tr>`).join("") : `<tr><td colspan="5"><div class="empty-state">No students yet. Add the first student above.</div></td></tr>`;
}

(async function init() {
  try {
    await loadAnalytics();
    await loadCompaniesAdmin();
    await loadStudents();
  } catch (err) { toast(err.message, "error"); }
})();
