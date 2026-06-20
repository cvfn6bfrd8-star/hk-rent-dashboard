# Hong Kong Rental Market Dashboard 🏠

An interactive data visualization dashboard analyzing the Hong Kong rental property market.

**🔗 Live Demo:** *(add your deployment URL here)*

---

## Overview

This project scrapes **4,455 real rental listings** from 28Hse.com across **82 districts** in Hong Kong Island, Kowloon, and New Territories. The data is cleaned, analyzed, and presented through an interactive web dashboard built with ECharts.

### What It Shows

| Feature | Description |
|---------|-------------|
| **District Comparison** | Bar chart comparing median rents across districts, filterable by region |
| **Price Distribution** | Min/median/max rent ranges by region |
| **Layout Analysis** | Room type distribution (studio / 1BR / 2BR / 3BR+) |
| **Price per sqft** | Unit price comparison across regions |
| **Floor Level Trends** | How floor height affects rent prices |
| **Data Table** | Sortable table with all district-level statistics |

---

## Tech Stack

- **Data Collection:** Python (Requests, BeautifulSoup)
- **Data Processing:** Pandas (Python)
- **Visualization:** ECharts.js
- **Deployment:** Static HTML (Vercel / GitHub Pages)

---

## Project Structure

```
hk-rent-dashboard/
├── index.html              ← Main dashboard page (deploy this)
├── scraper.py              ← 28Hse web scraper
├── vercel.json             ← Vercel deployment config
├── data/
│   ├── raw/                ← Scraped CSV data
│   └── processed/          ← Cleaned JSON for dashboard
├── scripts/
│   └── clean_data.py       ← Data cleaning pipeline
├── templates/
│   └── index.html          ← Source template
└── static/
```

---

## How to Run Locally

Simply open `index.html` in your browser. No server required — the data is embedded in the page.

To re-scrape fresh data:

```bash
python3 scraper.py
python3 scripts/clean_data.py
```

---

## Key Findings

- **Hong Kong Island** is the most expensive region with a median rent of **$18,800/mo**
- **Kowloon** and **New Territories** are more affordable at **$18,000/mo** and **$17,000/mo** respectively
- **2-bedroom** apartments are the most common listing type (31.7% of all listings)
- The dataset covers **82 distinct districts** across all three regions

---

## What I Learned

- Web scraping with polite crawling (rate limiting, error handling)
- Chinese text cleaning and classification (district → region mapping, layout extraction)
- Building interactive dashboards with ECharts.js
- Deploying static sites to Vercel

---

*Data sourced from 28Hse.com. Scraped June 2026.*
