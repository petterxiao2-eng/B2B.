# 跨境B2B客户增长系统 — MVP

## 这套MVP做了什么

一条完整可跑通的主线：
**配置项目和关键词矩阵 → 触发搜索(SerpAPI/Google Dorks) → 自动抓取候选公司官网背调 →
AI结构化提取信息并打分 → Web Dashboard查看A/B/C/D级客户 → 导出Excel/CSV**

四大模块对应关系：
| 你的需求 | 当前实现 |
|---|---|
| Google矩阵搜索 | `app/services/serp_search.py` + 关键词矩阵配置(按国家/产品线) |
| AI自动化官网背调 | `app/services/website_scraper.py` + `app/services/ai_analysis.py` |
| 多维度量化评分 | `app/services/scoring.py`，权重可在Dashboard里按项目调整 |
| 精准决策人追踪 | 仅从公司**官网公开页面**（About/Contact/Team）提取，见下方"范围调整说明" |

## 🚀 最简单的本地运行方式（不需要Docker，不需要装数据库）

```bash
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 SERPAPI_KEY 和 ANTHROPIC_API_KEY（其他保持默认即可）

python run.py
```
会自动打开浏览器 `http://127.0.0.1:8000`。数据存在项目目录下的 `b2b_leads.db` 文件里（SQLite），
删掉这个文件等于清空数据重新开始。适合先在自己电脑上把功能跑通验证效果。

等确认没问题、要长期跑/多人协作/数据量大了，再按下面的Docker方式部署到云服务器，
并把 `.env` 里的 `DATABASE_URL` 换成 PostgreSQL 连接串（一行配置就能切换，代码不用改）。

## ⚠️ 范围调整说明（请务必阅读）

搭建之初和你确认过，这版系统**没有**实现以下三项，原样保留会让你的账号/服务器/公司面临封禁和法律风险，所以我做了替代设计：

1. **LinkedIn/Facebook批量抓取个人信息** → 未实现。这两个平台ToS明确禁止自动化抓取，且有真实的诉讼先例(LinkedIn诉hiQ、Meta多次起诉爬虫公司)。
   替代方案：搜索模块命中LinkedIn/Facebook链接时，只记录链接和标题摘要作为"待人工核实线索"，不会登录或抓取详情。
2. **WhatsApp群链接/号码批量嗅探** → 未实现。批量收集陌生人WhatsApp联系方式用于自动化外联，在多数目标市场（尤其欧盟GDPR辖区）涉嫌未经同意收集个人数据。
   替代方案：系统只从公司官网上**公司自己主动公开**的联系方式（如官网Contact页写的电话/邮箱）里提取。
3. **自动群发** → 未实现。`outreach` 模块只生成草稿，状态停在 `draft`，需要业务员人工审核后自己在邮箱/WhatsApp客户端发送，再回来手动标记 `sent`。

命中 IndiaMart / GlobalSources / Made-in-China / TradeKey / Alibaba 等平台的搜索结果同理：只记录来源链接和摘要，不自动抓取平台内页（这些页面通常在登录墙后，且抓取会违反平台ToS），交给人工登录平台核实。

如果你确实需要平台内部数据（比如海关数据、深度联系人库），正规路径是**采购这些平台的官方API/企业订阅服务**（ImportYeti、Panjiva等都有合规的付费API），我可以帮你把接口接进这套系统里，这也是我在最初方案里提到的"预留接口"。

## 生产环境部署（Docker + PostgreSQL，适合长期挂在服务器上跑）

### 1. 准备账号和密钥
- **SerpAPI**：https://serpapi.com 注册，免费额度约每月100次搜索，够验证MVP。付费套餐按量计费。
- **Anthropic API Key**：https://console.anthropic.com 获取，用于背调信息结构化提取和沟通草稿生成。

### 2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env，填入 SERPAPI_KEY、ANTHROPIC_API_KEY、以及 POSTGRES_PASSWORD（改成强随机密码）
```

### 3. 启动
```bash
docker compose up -d --build
```
首次启动会自动建表（`app/main.py` 里的 `Base.metadata.create_all`）。

### 4. 访问
浏览器打开 `http://你的服务器IP:8000`

### 5. 部署到公网服务器
- 推荐配置：2核4G即可跑MVP（腾讯云/阿里云/Vultr等）
- 生产环境务必：
  - 把 `docker-compose.yml` 里数据库的 `ports: 5432:5432` 去掉（不要把数据库直接暴露公网）
  - 在前面挂 Nginx + HTTPS，配置模板见 `deploy/nginx.conf`（文件内有详细步骤注释）：
    ```bash
    apt-get install -y nginx certbot python3-certbot-nginx
    cp deploy/nginx.conf /etc/nginx/sites-available/b2b-leads
    # 编辑该文件，把 your-domain.com 换成你自己的域名
    ln -s /etc/nginx/sites-available/b2b-leads /etc/nginx/sites-enabled/
    nginx -t && systemctl reload nginx
    certbot --nginx -d your-domain.com   # 自动申请免费HTTPS证书
    ```
  - 把 `.env` 里的密码和密钥改成强随机值，不要用示例值
  - `app.add_middleware(CORSMiddleware, allow_origins=["*"])` 改成你的实际域名
  - 配置数据库定时备份，脚本见 `deploy/backup.sh`（自动打包压缩、清理14天前的旧备份，恢复方法写在脚本注释里）：
    ```bash
    chmod +x deploy/backup.sh
    ./deploy/backup.sh   # 先手动跑一次，确认能生成备份文件
    crontab -e
    # 加入这一行，每天凌晨3点自动备份：
    # 0 3 * * * /root/b2b-leads-system/deploy/backup.sh >> /root/backups/backup.log 2>&1
    ```

## 目录结构

```
app/
├── main.py              # FastAPI入口
├── config.py             # 环境变量配置
├── database.py            # SQLAlchemy连接
├── models.py              # 数据模型（项目/关键词/公司/联系人/评分/任务）
├── schemas.py             # API请求/响应结构
├── scheduler.py            # 定时任务（默认每天06:00自动搜索所有激活项目）
├── routers/
│   ├── projects.py         # 项目管理 + 评分模板配置
│   ├── keywords.py         # 关键词矩阵配置 + 推荐Google Dorks
│   ├── search.py           # 搜索任务触发 + 完整pipeline
│   ├── companies.py        # 客户清单查询/筛选/手动录入
│   ├── export.py           # Excel/CSV导出
│   └── outreach.py         # AI沟通草稿生成
├── services/
│   ├── serp_search.py       # SerpAPI + Google Dorks查询构造
│   ├── website_scraper.py    # 官网背调抓取
│   ├── ai_analysis.py       # Claude API结构化提取 + 草稿生成
│   ├── scoring.py           # 多维度加权评分引擎
│   └── normalize.py         # 去重/电话E.164标准化/邮箱校验
├── templates/dashboard.html   # Web Dashboard页面
└── static/app.js          # Dashboard前端逻辑（原生JS，无需构建）
```

## 使用流程

1. 打开Dashboard，点"新建项目"，填项目名和目标地区（如 `SA,AE,UZ`）
2. 切到"关键词矩阵"标签，选地区+填产品关键词+勾选推荐Dorks（或自己写），保存
3. 切到"搜索任务"标签，点"立即搜索"（后台运行，几分钟内完成，可刷新看进度）
4. 切到"客户清单"标签，按等级/地区筛选，点某条记录看完整背调报告
5. 在客户详情里点"生成邮件/WhatsApp草稿"，AI会生成初稿，**你审核修改后自己发送**
6. 用顶部"导出Excel/CSV"批量导出客户清单

## 已知的MVP局限（下一步可以继续加）

- **去重逻辑**目前只按官网域名判定，同公司用了不同域名（如有多个国家站点）会被当成两条记录，可以后续加"公司名称模糊匹配+地址相似度"做二次去重
- **代理池管理**没做（当前直连抓取官网，量大了可能被目标网站限流），后续可接入代理服务商API
- **多用户/权限**没做，目前是单用户系统，团队协作需要加登录和角色权限
- **数据库迁移**用的是启动时`create_all`，后续模型改动频繁后建议换成 `alembic` 做正式migration
- **海关数据接口**预留了设计位置但未实现，等你有ImportYeti等平台的付费账号后我可以帮你接入
- **评分模型**是启发式加权，跑一段时间积累了真实成交数据后，可以考虑升级成基于历史转化率训练的模型

## 关于合规性的一个建议

即使是"官网背调"这部分（完全合规），高频次、大批量地抓取同一批目标网站也可能给对方服务器造成压力、触发对方的防护机制。建议：
- 单个搜索任务的 `max_results_per_query` 保持在20-30左右，不要一次性设置几百
- 定时任务（`scheduler.py`）默认每天跑一次，不建议改成每小时跑
- 已经内置了 `robots.txt` 检查，会跳过明确禁止抓取的网站
