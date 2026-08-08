const API = "";
let currentProjectId = null;
let currentProjectName = "";
let projectsCache = [];

// 全局元数据缓存（国家列表 / 客户类型分层），初始化时拉取一次
let META = { countries: [], customerTiers: {} };

async function loadMeta() {
  try {
    const [countries, tiers] = await Promise.all([
      api("/api/meta/countries"),
      api("/api/meta/customer-tiers"),
    ]);
    META.countries = countries || [];
    META.customerTiers = tiers || {};
  } catch (e) {
    console.warn("加载元数据失败（国家切换器将不可用）", e);
  }
}

// 国家代码 -> 中文/英文名（用于来源追溯展示）
function countryName(code) {
  const c = META.countries.find(x => x.code === (code || "").toUpperCase());
  return c ? `${c.name} (${c.code})` : (code || "-");
}

// 来源类型中文标签
function sourceTypeLabel(t) {
  const map = {
    google: "Google 搜索", bing: "Bing 搜索", linkedin: "LinkedIn 公开页",
    facebook: "Facebook 公开页", directory: "贸易目录", manual: "手动录入",
    website: "官网抓取",
  };
  return map[t] || t || "-";
}

// 规范化发现渠道中文标签（对应后端 5 个固定取值）
function discoveryLabel(t) {
  const map = {
    google_serp: "Google搜索", bing_serp: "Bing搜索", linkedin_public: "LinkedIn公开页",
    facebook_public: "Facebook公开页", company_website: "官网直抓", trade_directory: "贸易目录",
  };
  return map[t] || sourceTypeLabel(t) || t || "-";
}

// ---------- 工具 ----------
async function api(path, options = {}) {
  const resp = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    alert("请求失败: " + (err.detail || resp.statusText));
    throw new Error(err.detail || resp.statusText);
  }
  return resp.json();
}

function gradeBadge(grade) {
  const g = grade || "unscored";
  return `<span class="px-2 py-0.5 rounded text-xs font-semibold grade-${g}">${g}</span>`;
}

function verifBadge(v) {
  if (v === true) return '<span class="text-green-600" title="通过">✓</span>';
  if (v === false) return '<span class="text-red-500" title="未通过">✕</span>';
  return '<span class="text-gray-300" title="未知">·</span>';
}

// 取公司主来源链接：优先 company_sources 中真实 URL，其次 company.source_url
function companySourceUrl(c) {
  const fromSources = (c.company_sources || []).find(s => s.source_url && /^https?:\/\//.test(s.source_url));
  return (fromSources && fromSources.source_url) || (c.source_url && /^https?:\/\//.test(c.source_url) ? c.source_url : "");
}
function companySourceLabel(c) {
  const t = c.source_discovered_from || c.source_type || ((c.company_sources || [])[0] || {}).source_type || "";
  return discoveryLabel(t);
}
// 关键词/语言追溯提示
function companyKeywordTip(c) {
  const orig = c.original_keyword || ((c.company_sources || [])[0] || {}).original_keyword || "";
  const trans = c.translated_keyword || ((c.company_sources || [])[0] || {}).translated_keyword || "";
  const lang = c.language || ((c.company_sources || [])[0] || {}).language || "";
  const parts = [];
  if (orig) parts.push(`原始词: ${orig}`);
  if (trans) parts.push(`本地化: ${trans}`);
  if (lang) parts.push(`语言: ${lang}`);
  return parts.join(" · ");
}

// ---------- 项目列表 ----------
async function loadProjects() {
  projectsCache = await api("/api/projects");
  const el = document.getElementById("projectList");
  el.innerHTML = projectsCache.map(p => `
    <div onclick="selectProject(${p.id}, '${p.name.replace(/'/g, "\\'")}')"
         class="p-2 rounded cursor-pointer hover:bg-blue-50 ${p.id === currentProjectId ? 'bg-blue-100 font-semibold' : ''}">
      ${p.name}
      <div class="text-xs text-gray-400">${(p.target_regions || []).join(", ")}</div>
    </div>
  `).join("") || `<div class="text-gray-400 text-xs p-2">暂无项目</div>`;
}

function showNewProjectForm() { document.getElementById("newProjectModal").classList.remove("hidden"); }
function closeNewProjectForm() { document.getElementById("newProjectModal").classList.add("hidden"); }

async function createProject() {
  const name = document.getElementById("npName").value.trim();
  if (!name) { alert("请输入项目名称"); return; }
  const description = document.getElementById("npDesc").value.trim();
  const target_regions = document.getElementById("npRegions").value.split(",").map(s => s.trim()).filter(Boolean);
  await api("/api/projects", { method: "POST", body: JSON.stringify({ name, description, target_regions }) });
  closeNewProjectForm();
  document.getElementById("npName").value = "";
  document.getElementById("npDesc").value = "";
  document.getElementById("npRegions").value = "";
  await loadProjects();
}

async function selectProject(id, name) {
  currentProjectId = id;
  currentProjectName = name;
  await loadProjects();
  renderProjectWorkspace();
}

// ---------- 项目工作区 ----------
function renderProjectWorkspace() {
  const el = document.getElementById("mainContent");
  el.innerHTML = `
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-xl font-bold">${currentProjectName} <span id="companyCount" class="text-sm font-normal text-gray-400"></span></h2>
      <div class="flex gap-2">
        <a href="/api/projects/${currentProjectId}/export/excel" class="px-3 py-1.5 bg-green-600 text-white rounded text-sm">导出Excel</a>
        <a href="/api/projects/${currentProjectId}/export/csv" class="px-3 py-1.5 bg-gray-600 text-white rounded text-sm">导出CSV</a>
      </div>
    </div>
    <div class="flex gap-2 mb-4 border-b">
      <button class="tab-btn px-3 py-2" data-tab="keywords" onclick="switchTab('keywords')">关键词矩阵</button>
      <button class="tab-btn px-3 py-2" data-tab="search" onclick="switchTab('search')">搜索任务</button>
      <button class="tab-btn px-3 py-2" data-tab="tasklog" onclick="switchTab('tasklog')">任务日志</button>
      <button class="tab-btn px-3 py-2 font-semibold border-b-2 border-blue-600" data-tab="companies" onclick="switchTab('companies')">客户清单</button>
      <button class="tab-btn px-3 py-2" data-tab="scoring" onclick="switchTab('scoring')">评分设置</button>
    </div>
    <div id="tabContent"></div>
  `;
  switchTab("companies");
}

function switchTab(tab) {
  document.querySelectorAll(".tab-btn").forEach(b => {
    b.classList.toggle("font-semibold", b.dataset.tab === tab);
    b.classList.toggle("border-b-2", b.dataset.tab === tab);
    b.classList.toggle("border-blue-600", b.dataset.tab === tab);
  });
  if (tab === "keywords") renderKeywordsTab();
  if (tab === "search") renderSearchTab();
  if (tab === "tasklog") renderTaskLogTab();
  if (tab === "companies") renderCompaniesTab();
  if (tab === "scoring") renderScoringTab();
}

// ---------- 关键词矩阵 ----------
async function renderKeywordsTab() {
  const dorks = await api(`/api/projects/${currentProjectId}/keywords/suggested-dorks`);
  const list = await api(`/api/projects/${currentProjectId}/keywords`);

  const countryOptions = (META.countries.length ? META.countries : [{ code: "", name: "（未加载）" }])
    .map(c => `<option value="${c.code}">${c.name} (${c.code})</option>`).join("");
  const tierChecks = Object.entries(META.customerTiers || {}).map(([tier, labels]) =>
    `<label class="inline-flex items-center gap-1 mr-3 text-sm">
       <input type="checkbox" class="kwTier" value="${tier}" checked> ${tier}
       <span class="text-xs text-gray-400">${labels.join("/")}</span>
     </label>`).join("");

  document.getElementById("tabContent").innerHTML = `
    <div class="bg-white rounded p-4 mb-4">
      <h3 class="font-semibold mb-2">新增关键词集</h3>
      <div class="grid grid-cols-2 gap-2 mb-2">
        <select id="kwRegion" class="border rounded p-2">${countryOptions}</select>
        <input id="kwLang" placeholder="语言代码，如 en / ar" class="border rounded p-2" value="en">
      </div>
      <textarea id="kwProducts" placeholder="产品关键词，逗号分隔，如：led floodlight, solar street light" class="border rounded w-full p-2 mb-2"></textarea>
      <input id="kwIndustry" placeholder="行业关键词（可选，逗号分隔，如 lighting, renewable energy）" class="border rounded w-full p-2 mb-2">
      <div class="mb-2">
        <div class="text-xs text-gray-500 mb-1">客户类型分层（默认全选，决定生成的查询覆盖面）：</div>
        <div class="flex flex-wrap gap-1">${tierChecks || '<span class="text-gray-400 text-xs">未加载</span>'}</div>
      </div>
      <div class="mb-2">
        <div class="text-xs text-gray-500 mb-1">推荐Google Dorks限定词（点击加入）：</div>
        <div class="flex flex-wrap gap-1" id="dorkSuggestions">
          ${Object.entries(dorks).flatMap(([cat, arr]) => arr.map(d =>
            `<span onclick="addDork('${d.replace(/'/g, "\\'")}')" class="cursor-pointer bg-gray-100 hover:bg-blue-100 px-2 py-1 rounded text-xs">${d}</span>`
          )).join("")}
        </div>
      </div>
      <textarea id="kwDorks" placeholder="已选定的Dork限定词（每行一个，可手动编辑）" class="border rounded w-full p-2 mb-2" rows="3"></textarea>
      <button onclick="createKeywordSet()" class="bg-blue-600 text-white rounded px-3 py-1.5">保存关键词集</button>
    </div>
    <div class="bg-white rounded p-4">
      <h3 class="font-semibold mb-2">已配置的关键词集</h3>
      <table class="w-full text-sm">
        <thead><tr class="text-left text-gray-500 border-b">
          <th class="py-1">地区</th><th>产品关键词</th><th>客户分层</th><th>行业词</th><th>Dorks</th><th></th>
        </tr></thead>
        <tbody>
          ${list.map(k => `
            <tr class="border-b">
              <td class="py-1">${countryName(k.region_code)}</td>
              <td>${(k.product_keywords || []).join(", ")}</td>
              <td class="text-xs text-gray-500">${(k.customer_type_tiers || []).join(", ") || '全部'}</td>
              <td class="text-xs text-gray-500">${(k.industry_keywords || []).join(", ") || '-'}</td>
              <td class="text-xs text-gray-500">${(k.dork_filters || []).join(" / ") || '-'}</td>
              <td><button onclick="deleteKeywordSet(${k.id})" class="text-red-500 text-xs">删除</button></td>
            </tr>
          `).join("") || `<tr><td colspan="6" class="text-gray-400 py-2">暂无配置</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}

function addDork(d) {
  const ta = document.getElementById("kwDorks");
  ta.value = ta.value ? ta.value + "\n" + d : d;
}

async function createKeywordSet() {
  const region_code = document.getElementById("kwRegion").value.trim();
  const language = document.getElementById("kwLang").value.trim() || "en";
  const product_keywords = document.getElementById("kwProducts").value.split(",").map(s => s.trim()).filter(Boolean);
  const industry_keywords = document.getElementById("kwIndustry").value.split(",").map(s => s.trim()).filter(Boolean);
  const dork_filters = document.getElementById("kwDorks").value.split("\n").map(s => s.trim()).filter(Boolean);
  const customer_type_tiers = Array.from(document.querySelectorAll(".kwTier:checked")).map(c => c.value);
  if (!region_code || product_keywords.length === 0) { alert("请选择地区并填写至少一个产品关键词"); return; }
  await api(`/api/projects/${currentProjectId}/keywords`, {
    method: "POST",
    body: JSON.stringify({
      region_code, product_keywords, dork_filters, language,
      industry_keywords, customer_type_tiers, country_profile: region_code,
    }),
  });
  renderKeywordsTab();
}

async function deleteKeywordSet(id) {
  if (!confirm("确认删除该关键词集？")) return;
  await api(`/api/projects/${currentProjectId}/keywords/${id}`, { method: "DELETE" });
  renderKeywordsTab();
}

// ---------- 搜索任务 ----------
async function renderSearchTab() {
  const keywordSets = await api(`/api/projects/${currentProjectId}/keywords`);
  const tasks = await api(`/api/projects/${currentProjectId}/search`);

  document.getElementById("tabContent").innerHTML = `
    <div class="bg-white rounded p-4 mb-4">
      <h3 class="font-semibold mb-2">手动触发搜索</h3>
      <select id="triggerKeywordSet" class="border rounded p-2 mb-2 w-full">
        <option value="">全部激活的关键词集</option>
        ${keywordSets.map(k => `<option value="${k.id}">${k.region_code} - ${(k.product_keywords||[]).join(",")}</option>`).join("")}
      </select>
      <button onclick="triggerSearch()" class="bg-blue-600 text-white rounded px-4 py-1.5">🔍 立即搜索</button>
      <span class="text-xs text-gray-400 ml-2">任务会在后台运行，包含官网抓取+AI分析，可能需要几分钟</span>
    </div>
    <div class="bg-white rounded p-4 mb-4">
      <h3 class="font-semibold mb-2">独立爬虫（直接输入 URL，真实抓取，不产生搜索查询）</h3>
      <div class="flex gap-2 mb-2">
        <input id="cwUrl" placeholder="公司官网 URL，如 https://example.com" class="border rounded p-2 flex-1">
        <button onclick="crawlWebsite()" class="bg-indigo-600 text-white rounded px-3 py-1.5 whitespace-nowrap">抓取官网</button>
      </div>
      <div class="flex gap-2">
        <input id="cdUrl" placeholder="行业目录列表页 URL，如 https://www.indiamart.com/..." class="border rounded p-2 flex-1">
        <button onclick="crawlDirectory()" class="bg-purple-600 text-white rounded px-3 py-1.5 whitespace-nowrap">抓取目录</button>
      </div>
      <div class="text-xs text-gray-400 mt-1">抓取结果进入「任务日志」并显示漏斗统计；遵守 robots.txt，不登录、不绕过权限，绝不生成假数据。</div>
    </div>
    <div class="bg-white rounded p-4">
      <div class="flex justify-between items-center mb-2">
        <h3 class="font-semibold">任务队列历史</h3>
        <button onclick="renderSearchTab()" class="text-xs text-blue-600">刷新</button>
      </div>
      <table class="w-full text-sm">
        <thead><tr class="text-left text-gray-500 border-b"><th class="py-1">状态</th><th>搜索命中数</th><th>新增客户</th><th>发起时间</th><th>耗时</th><th>备注</th></tr></thead>
        <tbody>
          ${tasks.map(t => `
            <tr class="border-b">
              <td class="py-1">${statusBadge(t.status)}</td>
              <td>${t.results_found}</td>
              <td>${t.new_companies}</td>
              <td class="text-xs">${new Date(t.created_at).toLocaleString()}</td>
              <td class="text-xs">${t.started_at && t.finished_at ? Math.round((new Date(t.finished_at)-new Date(t.started_at))/1000)+'s' : '-'}</td>
              <td class="text-xs text-red-500">${t.error_message ? t.error_message.slice(0,60) : ''}</td>
            </tr>
          `).join("") || `<tr><td colspan="6" class="text-gray-400 py-2">暂无搜索记录</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}

function statusBadge(status) {
  const map = { pending: "bg-gray-200", running: "bg-blue-200", success: "bg-green-200", failed: "bg-red-200" };
  return `<span class="px-2 py-0.5 rounded text-xs ${map[status]||''}">${status}</span>`;
}

async function triggerSearch() {
  const ksId = document.getElementById("triggerKeywordSet").value;
  await api(`/api/projects/${currentProjectId}/search/trigger`, {
    method: "POST",
    body: JSON.stringify({ keyword_set_id: ksId ? parseInt(ksId) : null, max_results_per_query: 20 }),
  });
  alert("搜索任务已提交，正在后台运行，稍后到'搜索任务'标签页查看进度");
  renderSearchTab();
}

async function crawlWebsite() {
  const url = (document.getElementById("cwUrl") || {}).value;
  if (!url || !url.trim()) { alert("请输入公司官网 URL"); return; }
  await api(`/api/projects/${currentProjectId}/search/crawl-website`, {
    method: "POST", body: JSON.stringify({ url: url.trim() }),
  });
  alert("官网抓取任务已提交，遵守 robots.txt 真实抓取，稍后到「任务日志」查看漏斗与结果");
  renderSearchTab();
}

async function crawlDirectory() {
  const url = (document.getElementById("cdUrl") || {}).value;
  if (!url || !url.trim()) { alert("请输入行业目录列表页 URL"); return; }
  await api(`/api/projects/${currentProjectId}/search/crawl-directory`, {
    method: "POST", body: JSON.stringify({ url: url.trim() }),
  });
  alert("目录抓取任务已提交，真实提取公司，稍后到「任务日志」查看漏斗与结果");
  renderSearchTab();
}

// ---------- 任务日志（Search Funnel）----------
function taskTypeLabel(t) {
  const map = { search: "搜索", website: "官网直抓", directory: "目录抓取" };
  return map[t] || t || "-";
}

async function renderTaskLogTab() {
  const tasks = await api(`/api/projects/${currentProjectId}/search`);
  document.getElementById("tabContent").innerHTML = `
    <div class="bg-white rounded p-4">
      <h3 class="font-semibold mb-2">搜索任务日志（Search Funnel）</h3>
      <div class="text-xs text-gray-400 mb-3">漏斗口径：生成查询 → SERP返回 → 去重候选 → 验证通过 → 最终客户</div>
      <table class="w-full text-sm">
        <thead><tr class="text-left text-gray-500 border-b">
          <th class="py-1">类型</th><th>状态</th>
          <th>生成查询</th><th>SERP返回</th><th>去重候选</th><th>验证通过</th><th>最终客户</th>
          <th>耗时</th><th>发起时间</th><th>备注</th>
        </tr></thead>
        <tbody>
          ${tasks.map(t => `
            <tr class="border-b">
              <td class="py-1">${taskTypeLabel(t.task_type)}</td>
              <td>${statusBadge(t.status)}</td>
              <td>${t.queries_generated ?? '-'}</td>
              <td>${t.serp_results ?? '-'}</td>
              <td>${t.dedup_count ?? '-'}</td>
              <td>${t.verified_count ?? '-'}</td>
              <td>${t.real_companies}</td>
              <td class="text-xs">${t.started_at && t.finished_at ? Math.round((new Date(t.finished_at)-new Date(t.started_at))/1000)+'s' : '-'}</td>
              <td class="text-xs">${new Date(t.created_at).toLocaleString()}</td>
              <td class="text-xs text-red-500">${t.error_message ? t.error_message.slice(0,80) : ''}</td>
            </tr>
          `).join("") || `<tr><td colspan="10" class="text-gray-400 py-2">暂无任务记录</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
}

// ---------- 客户清单 ----------
async function renderCompaniesTab() {
  document.getElementById("tabContent").innerHTML = `
    <div class="bg-white rounded p-3 mb-3 flex gap-2 items-center flex-wrap">
      <select id="filterGrade" onchange="renderCompaniesTab()" class="border rounded p-1.5 text-sm">
        <option value="">全部等级</option>
        <option value="A">A级</option><option value="B">B级</option>
        <option value="C">C级</option><option value="D">D级</option>
      </select>
      <input id="filterRegion" placeholder="地区代码筛选" onchange="renderCompaniesTab()" class="border rounded p-1.5 text-sm">
      <button onclick="showManualAddForm()" class="ml-auto bg-gray-700 text-white rounded px-3 py-1.5 text-sm">+ 手动录入线索</button>
    </div>
    <div id="companyListWrap" class="bg-white rounded"><div class="p-4 text-gray-400">加载中...</div></div>
  `;

  const grade = document.getElementById("filterGrade").value;
  const region = document.getElementById("filterRegion").value;
  let url = `/api/projects/${currentProjectId}/companies?`;
  if (grade) url += `grade=${grade}&`;
  if (region) url += `region_code=${region}&`;

  const companies = await api(url);
  const stats = await api(`/api/projects/${currentProjectId}/companies/stats`).catch(() => ({
    real_companies: companies.length, search_hits: 0,
  }));
  const countEl = document.getElementById("companyCount");
  if (countEl) {
    countEl.textContent = `共 ${stats.real_companies} 家客户（真实去重）`;
    countEl.title = `最近一次搜索原始命中 ${stats.search_hits} 条`;
  }
  document.getElementById("companyListWrap").innerHTML = `
    <table class="w-full text-sm">
      <thead><tr class="text-left text-gray-500 border-b bg-gray-50">
        <th class="py-2 px-2">评分/等级</th><th>公司名称</th><th>地区</th><th>联系方式</th><th>官网</th><th>来源</th><th>验证</th><th>社交</th><th>核实状态</th><th></th>
      </tr></thead>
      <tbody>
        ${companies.map(c => {
          const srcUrl = companySourceUrl(c);
          const tip = companyKeywordTip(c);
          return `
          <tr class="border-b hover:bg-gray-50 cursor-pointer" onclick="openCompanyDetail(${c.id})">
            <td class="py-2 px-2">${gradeBadge(c.grade)} <span class="text-xs text-gray-400">${c.score_total}</span></td>
            <td class="font-medium">${c.company_name || '(未命名)'}</td>
            <td>${c.region_code || '-'}</td>
            <td class="text-xs">${c.email || '-'}<br>${c.phone_e164 || c.phone || ''}</td>
            <td class="text-xs text-blue-600 truncate max-w-[150px]">${c.website ? `<a href="${c.website}" target="_blank" onclick="event.stopPropagation()">${new URL(c.website).hostname}</a>` : '-'}</td>
            <td class="text-xs">${srcUrl
              ? `<a href="${srcUrl}" target="_blank" onclick="event.stopPropagation()" class="text-blue-500 underline"${tip ? ` title="${tip}"` : ''}>${companySourceLabel(c)}</a>`
              : `<span title="${tip}">${companySourceLabel(c)}</span>`}</td>
            <td class="text-xs">${verifBadge(c.dns_valid)} ${verifBadge(c.http_status!=null)} ${verifBadge(c.ssl_valid)} ${verifBadge(c.mx_valid)}</td>
            <td class="text-xs">${c.linkedin ? `<a href="${c.linkedin}" target="_blank" onclick="event.stopPropagation()" class="text-blue-500">in</a>` : ''} ${c.facebook ? `<a href="${c.facebook}" target="_blank" onclick="event.stopPropagation()" class="text-blue-500">fb</a>` : ''} ${c.whatsapp ? 'wa' : ''}</td>
            <td class="text-xs text-gray-400">${c.verified_status}</td>
            <td><button onclick="event.stopPropagation(); deleteCompany(${c.id})" class="text-red-400 text-xs">删除</button></td>
          </tr>`;
        }).join("") || `<tr><td colspan="10" class="text-gray-400 p-4 text-center">暂无客户数据，请先配置关键词矩阵并触发搜索</td></tr>`}
      </tbody>
    </table>
  `;
}

async function deleteCompany(id) {
  if (!confirm("确认删除该客户记录？")) return;
  await api(`/api/projects/${currentProjectId}/companies/${id}`, { method: "DELETE" });
  renderCompaniesTab();
}

function showManualAddForm() {
  const name = prompt("公司名称：");
  if (!name) return;
  const website = prompt("官网（可留空）：") || "";
  const email = prompt("邮箱（可留空）：") || "";
  const phone = prompt("电话（可留空）：") || "";
  const region_code = prompt("地区代码（可留空，如 SA）：") || "";
  api(`/api/projects/${currentProjectId}/companies/manual`, {
    method: "POST",
    body: JSON.stringify({ company_name: name, website, email, phone, region_code, source_note: "手动录入" }),
  }).then(() => renderCompaniesTab());
}

// ---------- 客户详情弹窗 ----------
async function openCompanyDetail(id) {
  const c = await api(`/api/projects/${currentProjectId}/companies/${id}`);
  const report = c.background_report || {};
  const modal = document.createElement("div");
  modal.className = "fixed inset-0 bg-black/40 flex items-center justify-center z-50";
  modal.innerHTML = `
    <div class="bg-white rounded-lg p-6 w-[600px] max-h-[85vh] overflow-y-auto">
      <div class="flex justify-between items-start mb-3">
        <div>
          <h2 class="font-bold text-lg">${c.company_name}</h2>
          <div class="text-xs text-gray-400">${c.website || c.source_url}</div>
          ${(c.original_keyword || c.translated_keyword || c.language) ? `
          <div class="text-xs text-gray-400 mt-0.5">
            来源词：${c.original_keyword || '-'}${c.translated_keyword ? ` → ${c.translated_keyword}` : ''}${c.language ? ` ［${c.language}］` : ''}
          </div>` : ''}
        </div>
        <div>${gradeBadge(c.grade)} <span class="text-xs">${c.score_total}分</span></div>
      </div>

      <div class="grid grid-cols-2 gap-3 text-sm mb-3">
        <div><span class="text-gray-400">邮箱：</span>${c.email || '-'} ${c.email_valid===true?'✅':c.email_valid===false?'❌':''}</div>
        <div><span class="text-gray-400">电话：</span>${c.phone_e164 || c.phone || '-'}</div>
        <div><span class="text-gray-400">WhatsApp：</span>${c.whatsapp || '-'}</div>
        <div><span class="text-gray-400">采购可能性：</span>${c.purchase_probability ?? '-'}</div>
        <div><span class="text-gray-400">LinkedIn：</span>${c.linkedin ? `<a class="text-blue-500 underline" href="${c.linkedin}" target="_blank">${new URL(c.linkedin).hostname}</a>` : '-'}</div>
        <div><span class="text-gray-400">Facebook：</span>${c.facebook ? `<a class="text-blue-500 underline" href="${c.facebook}" target="_blank">${new URL(c.facebook).hostname}</a>` : '-'}</div>
        <div><span class="text-gray-400">地址：</span>${c.address || '-'}</div>
        <div><span class="text-gray-400">业务类型：</span>${c.business_type || '-'}</div>
        <div class="col-span-2"><span class="text-gray-400">经营品类：</span>${c.products_summary || '-'}</div>
        <div class="col-span-2"><span class="text-gray-400">真实性验证：</span>
          DNS ${verifBadge(c.dns_valid)} &nbsp;
          HTTP ${c.http_status!=null ? c.http_status : '·'} &nbsp;
          SSL ${verifBadge(c.ssl_valid)} &nbsp;
          MX ${verifBadge(c.mx_valid)}
        </div>
      </div>

      ${report.founded_year || report.main_markets ? `
      <div class="text-sm mb-3 border-t pt-2">
        <div><span class="text-gray-400">成立年份：</span>${report.founded_year || '未通过公开渠道查实'}</div>
        <div><span class="text-gray-400">主要市场：</span>${report.main_markets || '未通过公开渠道查实'}</div>
        <div><span class="text-gray-400">切入点建议：</span>${report.swot_opportunity || '-'}</div>
        <div><span class="text-gray-400">风险提示：</span>${report.risk_flags || '-'}</div>
      </div>` : ''}

      <div class="mb-3 border-t pt-2">
        <div class="text-gray-400 text-sm mb-1">评分明细：</div>
        <div class="flex flex-wrap gap-2 text-xs">
          ${Object.entries(c.score_breakdown || {}).map(([k,v]) => `<span class="bg-gray-100 px-2 py-1 rounded">${k}: ${v}</span>`).join("")}
        </div>
      </div>

      <div class="mb-3 border-t pt-2">
        <div class="text-gray-400 text-sm mb-1">联系人（仅来自公司官网公开信息）：</div>
        ${(c.contacts||[]).map(ct => `<div class="text-sm">${ct.name} - ${ct.title} <span class="text-xs text-gray-400">(${ct.source_note})</span></div>`).join("") || '<div class="text-sm text-gray-400">暂无</div>'}
      </div>

      <div class="mb-3 border-t pt-2">
        <div class="text-gray-400 text-sm mb-1">公开联系方式（逐条可追溯来源页）：</div>
        ${(c.company_contacts||[]).map(cc => {
          const su = cc.source_url && /^https?:\/\//.test(cc.source_url) ? cc.source_url : (cc.source_page || "");
          return `<div class="text-sm">${cc.contact_type}: ${cc.value} ${su ? `<a class="text-blue-500 underline text-xs" href="${su}" target="_blank">来源↗</a>` : ''}</div>`;
        }).join("") || '<div class="text-sm text-gray-400">暂无</div>'}
      </div>

      <div class="mb-3 border-t pt-2">
        <div class="text-gray-400 text-sm mb-1">来源追溯（company_sources，每条线索可点击核实）：</div>
        ${(c.company_sources&&c.company_sources.length) ? c.company_sources.map(s => {
          const su = s.source_url && /^https?:\/\//.test(s.source_url) ? s.source_url : "";
          const kw = [s.original_keyword, s.translated_keyword].filter(Boolean).join(" → ");
          return `<div class="text-xs mb-1">
            <span class="bg-gray-100 px-1.5 py-0.5 rounded">${discoveryLabel(s.source_discovered_from || s.source_type)}</span>
            ${kw ? `<span class="text-gray-500">词: ${kw}${s.language ? ' ［'+s.language+'］' : ''}</span>` : ''}
            ${su ? `<a class="text-blue-500 underline ml-1" href="${su}" target="_blank">来源页↗</a>` : (s.source_keyword ? `<span class="text-gray-400 ml-1">关键词: ${s.source_keyword}</span>` : '')}
          </div>`;
        }).join("") : '<div class="text-sm text-gray-400">暂无</div>'}
      </div>

      <div class="mb-3 border-t pt-2">
        <div class="text-gray-400 text-sm mb-1">抓取过的页面（original_pages，可点击验证）：</div>
        ${(c.original_pages&&c.original_pages.length) ? c.original_pages.map(p => `<div class="text-xs"><a class="text-blue-500 underline" href="${p}" target="_blank">${p}</a></div>`).join("") : '<div class="text-sm text-gray-400">未抓取</div>'}
      </div>

      <div class="border-t pt-3 flex gap-2">
        <button onclick="generateOutreach(${c.id}, 'email')" class="bg-blue-600 text-white rounded px-3 py-1.5 text-sm">生成邮件草稿</button>
        <button onclick="generateOutreach(${c.id}, 'whatsapp')" class="bg-green-600 text-white rounded px-3 py-1.5 text-sm">生成WhatsApp草稿</button>
        <button onclick="this.closest('.fixed').remove()" class="ml-auto border rounded px-3 py-1.5 text-sm">关闭</button>
      </div>
      <div id="outreachResult" class="mt-3"></div>
    </div>
  `;
  document.body.appendChild(modal);
}

async function generateOutreach(companyId, channel) {
  const el = document.getElementById("outreachResult");
  el.innerHTML = `<div class="text-gray-400 text-sm">生成中...</div>`;
  const draft = await api(`/api/companies/${companyId}/outreach/generate`, {
    method: "POST",
    body: JSON.stringify({ company_id: companyId, channel, tone: "professional" }),
  });
  el.innerHTML = `
    <div class="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm">
      <div class="text-xs text-gray-500 mb-1">⚠️ 以下为AI生成草稿，请人工审核修改后再手动发送</div>
      ${draft.subject ? `<div class="font-medium mb-1">主题：${draft.subject}</div>` : ''}
      <div class="whitespace-pre-wrap">${draft.body}</div>
    </div>
  `;
}

// ---------- 评分设置 ----------
async function renderScoringTab() {
  const tpl = await api(`/api/projects/${currentProjectId}/scoring-template`);
  const el = document.getElementById("tabContent");
  el.innerHTML = `
    <div class="bg-white rounded p-4 max-w-lg">
      <h3 class="font-semibold mb-3">评分维度权重（总和建议=100）</h3>
      <div id="weightInputs">
        ${Object.entries(tpl.weights).map(([k,v]) => `
          <div class="flex items-center justify-between mb-2">
            <label class="text-sm">${k}</label>
            <input type="number" data-key="${k}" value="${v}" class="border rounded p-1 w-20 weight-input">
          </div>
        `).join("")}
      </div>
      <h3 class="font-semibold mb-2 mt-4">分级阈值</h3>
      <div id="thresholdInputs">
        ${Object.entries(tpl.grade_thresholds).map(([k,v]) => `
          <div class="flex items-center justify-between mb-2">
            <label class="text-sm">${k}级 ≥</label>
            <input type="number" data-key="${k}" value="${v}" class="border rounded p-1 w-20 threshold-input">
          </div>
        `).join("")}
      </div>
      <button onclick="saveScoringTemplate()" class="bg-blue-600 text-white rounded px-3 py-1.5 mt-2">保存</button>
      <div class="text-xs text-gray-400 mt-2">修改后仅对新搜索到的客户生效，历史客户评分不会自动重算</div>
    </div>
  `;
}

async function saveScoringTemplate() {
  const weights = {};
  document.querySelectorAll(".weight-input").forEach(inp => weights[inp.dataset.key] = parseFloat(inp.value));
  const grade_thresholds = {};
  document.querySelectorAll(".threshold-input").forEach(inp => grade_thresholds[inp.dataset.key] = parseFloat(inp.value));
  await api(`/api/projects/${currentProjectId}/scoring-template`, {
    method: "PUT",
    body: JSON.stringify({ weights, grade_thresholds }),
  });
  alert("已保存");
}

// ---------- 初始化 ----------
loadMeta().then(loadProjects);
