# 🎯 PyProspector

> B2B lead prospecting tool via **Google Maps** — built with Python, Playwright and Streamlit.

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-FF4B4B?logo=streamlit&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-1.40%2B-45ba4b?logo=playwright&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What is it?

**PyProspector** automates the search for businesses on Google Maps and extracts structured data to build qualified lead lists. Ideal for:

- Web design agencies prospecting SMBs **without a digital presence**
- SEO and paid traffic freelancers looking for new clients
- Digital marketing consultants doing outbound B2B prospecting
- Sales teams conducting local market research

---

## Features

| Feature | Detail |
|---|---|
| 🔍 **Smart search** | Searches `{niche} {city}` on Google Maps |
| 🛡️ **Anti-detection** | Playwright + `playwright-stealth` (headless + WebDriver patches) |
| 📊 **Fitness score** | Formula that prioritises businesses without a website with high ratings |
| 📋 **Interactive table** | `st.dataframe` with configured columns and progress bar |
| 📥 **Excel export** | Formatted `.xlsx`: blue header, no-website rows highlighted in green |
| 📄 **TSV export** | Tab-separated text compatible with Excel, Google Sheets, etc. |

---

## Data extracted per lead

| Field | Description |
|---|---|
| `name` | Business name |
| `category` | Business category (e.g. Dentist, Restaurant) |
| `address` | Full address |
| `phone` | Contact phone number |
| `website` | Website URL (if available) |
| `has_website` | `True` / `False` |
| `rating` | Average star rating (0–5) |
| `reviews` | Number of reviews |
| `score` | Fitness score for web dev services (see formula below) |

### Score Formula

```
score_base  = (rating × 10) × (number_of_reviews / 100)
score_final = score_base × 2.5   →  NO website  🔥
score_final = score_base           →  has website
```

Leads **without a website** with a high volume of reviews and a good rating appear at the top — these are established businesses with a digital gap, the best candidates for website creation and digital marketing services.

---

## Prerequisites

- **Python 3.11+** — [python.org](https://www.python.org/downloads/)
- **Git** (optional, to clone the repository)
- Internet connection

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/seu-usuario/pyprospector.git
cd pyprospector
```

### 2. Create and activate the virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install the Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install the Playwright Chromium browser

```bash
playwright install chromium
```

> This command downloads the Chromium binary used by the scraper (~150 MB).

---

## How to use

### Start the web interface

```bash
streamlit run app.py
```

The browser will open automatically at `http://localhost:8501`.

### Step-by-step guide

1. **Niche / Segment** — type the business type (e.g. `dentists`, `dental clinics`, `lawyers`)
2. **City / Country** — enter the location (e.g. `São Paulo, Brasil`, `Lisbon, Portugal`)
3. **Max. results** — adjust the slider (5–100, default: 50)
4. **Minimum rating** — filter by average stars (0 = no filter)
5. Click **🚀 Prospect Leads** and wait

> Scraping takes between **1–5 minutes** depending on the number of results and connection speed.

---

## Project structure

```
pyprospector/
├── app.py            # Main application (Streamlit + scraping + export)
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

---

## Dependencies

| Library | Min. version | Purpose |
|---|---|---|
| `streamlit` | 1.32 | Web interface |
| `playwright` | 1.40 | Browser automation |
| `playwright-stealth` | 1.0.6 | Anti-detection patches |
| `pandas` | 2.1 | Data manipulation |
| `openpyxl` | 3.1.2 | Excel export |

---

## Troubleshooting

**`ModuleNotFoundError: playwright_stealth`**
```bash
pip install playwright-stealth
```

**No results found**
- Check the spelling of the niche and city
- Lower the minimum rating to `0`
- Google Maps may have temporarily throttled requests — wait and try again

**`playwright install` failed**
```bash
playwright install chromium --with-deps
```

**Permission error on Windows (Activate.ps1)**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Legal Notice

> ⚠️ This project is provided **for educational and ethical automation purposes only**.
> Using scrapers may violate the [Google Maps Terms of Service](https://maps.google.com/help/terms_maps/).
> Use it responsibly, respect `robots.txt` and the platform's acceptable use policies.
> The author takes no responsibility for misuse of this tool.

---

## License

[MIT](LICENSE) © 2026
