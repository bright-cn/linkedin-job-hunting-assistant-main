<p align="center">
  <a href="https://www.bright.cn/">
    <img src="https://mintlify.s3.us-west-1.amazonaws.com/brightdata/logo/light.svg" width="300" alt="Bright Data 标志">
  </a>
</p>

# LinkedIn 求职 AI 助手 🤖💼

**使用 [Bright Data Scraper API](https://www.bright.cn/products/web-scraper) 与 OpenAI 评分自动化你的 LinkedIn 职位搜索与排序！为你的个人资料轻松发现、评分并审阅最佳职位匹配。**

<div align="center">
  <img src="https://img.shields.io/badge/python-3.8+-blue"/>
  <img src="https://img.shields.io/badge/License-MIT-blue"/>
</div>

---

## 功能特性 🚀

- **自动化 LinkedIn 职位抓取**：使用 [Bright Data 的 LinkedIn Job Listings API](https://docs.brightdata.com/api-reference/web-scraper-api/social-media-apis/linkedin) 收集相关职位信息。
- **AI 驱动职位评分**：借助 OpenAI 对职位进行 0–100 分评分，依据你的个人资料与偏好为每个职位打分。
- **批处理能力**：通过分批次请求与评分，高效处理大规模职位数据集。
- **可自定义搜索条件**：在易编辑的 JSON 配置中调整职位搜索参数与排除列表。
- **可读性强的 CSV 输出**：导出包含 AI 评分与评论的结果，便于审阅与分享。
- **快速洞察**：通过简短的 AI 评论一眼查看最匹配的职位。

---

## 前置条件 🛠️

- Python 3.8+ 🐍
- [Bright Data API token](https://docs.brightdata.com/api-reference/authentication#how-do-i-generate-a-new-api-key%3F) 🔑
- OpenAI API key 🔑

---

## 安装 ⚙️

1. 克隆此仓库：

```bash
git clone https://github.com/bright-cn/linkedin-job-hunting-assistant
cd linkedin-job-hunting-assistant
```

2. 安装依赖：

```
pip install -r requirements.txt
```

3. 在项目根目录创建 `.env`，填入你的 API 密钥：

```
OPENAI_API_KEY=your_openai_api_key
BRIGHT_DATA_API_KEY=your_bright_data_api_key
```

---

## 配置 📝

在项目根目录创建 `config.json`，根据你的偏好填写字段。

例如：

```json
{
  "location": "New York, NY",
  "keyword": "Data Scientist",
  "country": "US",
  "time_range": "past week",
  "experience_level": "senior",
  "remote": "yes",
  "jobs_to_not_include": ["intern", "entry level", "recruiter"],
  "profile_summary": "Senior Data Scientist with strong background in machine learning, seeking impactful projects.",
  "desired_job_summary": "A leadership or senior IC role in data science working on production models."
}
```

_可按需调整或新增其他字段（例如 `company`、`location_radius`、`job_type`）。_

在 [LinkedIn Job Listings API 文档](https://docs.brightdata.com/api-reference/web-scraper-api/social-media-apis/linkedin#discover-by-keyword) 中查看支持的配置字段。然后，记得加入以下字段：

- `profile_summary`：用几句话描述你的职业经历、技能与目标。
- `desired_job_summary`：用几句话描述你期望的职位。

以上两个字段有助于 OpenAI 评分流程为选定职位分配更合适的分数。

---

## 使用 ▶️

在终端运行职位助手：

```
python assistant.py --config_file config.json --jobs_number 25 --batch_size 5 --output_csv jobs_scored.csv
```

**参数说明：**

- `--config_file`：配置 JSON 路径（默认：`config.json`）
- `--jobs_number`：抓取职位数量（默认：`20`）
- `--batch_size`：每次评分的职位数量（默认：`5`）
- `--output_csv`：结果输出文件名（默认：`jobs_scored.csv`）

---

## 输出 📤

所有职位记录会按 AI 匹配分数排序，并附带评论，导出到你指定的 CSV 文件（例如 `jobs_scored.csv`）。

<img src="https://media.brightdata.com/2025/08/image-157.png" alt="最终输出">

---

## 高级配置 🧑‍💻

- **提示工程（Prompt Engineering）**：在 `score_jobs_batch()` 函数中微调 OpenAI 的评分提示。

---

## 故障排除与提示 💡

- 确保 `.env` 中的 API 密钥正确无误。
- 确保在 `config.json` 中设置了你的偏好项。
- 代码中已配置 [Bright Data LinkedIn 数据集](https://www.bright.cn/products/datasets/linkedin) 的 ID 与 discover 模式。除非非常了解，否则不要修改 API 集成代码！
- 遵守 API 速率限制。
- 若出现校验错误，请检查你的配置文件是否符合 Pydantic 模型所需字段。

---

**祝你求职顺利！🚀**
