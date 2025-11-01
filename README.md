# 🧾 Funishka Technical Assignment — Submission Report

## 👨‍💻 Author
**Name:** Anurag Singh  
**Date:** November 1, 2025  

---

## 🧠 Objective
The goal of this assignment was to build a **Python command-line tool** that connects to the **Meta (Facebook) Graph API**, fetches **Lead Ads data**, processes and normalizes the information, and exports the new leads in a structured format (JSON/CSV) — while preventing duplicate entries using a local database.

---

## ⚙️ Tech Stack
- **Language:** Python 3.x  
- **APIs:** Meta Graph API v16.0  
- **Database:** SQLite (for duplicate detection)  
- **Environment:** dotenv (.env file for access tokens and form IDs)  
- **Libraries Used:**
  - `requests`
  - `dotenv`
  - `argparse`
  - `sqlite3`
  - `logging`
  - `json` / `csv`

---

## 🧩 Project Structure
```
tech_assignment/
│
├── src/
│   ├── fetcher.py        # Main CLI tool – fetches, normalizes, exports leads
│   ├── utils/
│   │   ├── db.py         # Handles seen leads tracking in SQLite
│   │   └── meta.py       # Helper functions for API requests
│
├── data/
│   └── seen_leads.db     # Stores IDs of already processed leads
│
├── .env                  # Contains META_ACCESS_TOKEN and LEAD_FORM_ID
├── new_leads.json        # Output file (can also generate CSV)
└── README.md             # Submission Report
```

---

## 🚀 How to Run

### 1️⃣ Create and activate virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 3️⃣ Set up environment
Copy `.env.sample` to `.env` and fill in:
```
META_ACCESS_TOKEN=your_long_page_access_token
LEAD_FORM_ID=your_form_id
```

### 4️⃣ Run the script
```bash
python src/fetcher.py --output json
```
or
```bash
python src/fetcher.py --output csv
```

---

## 🧾 Example Output
After running:
```
python src/fetcher.py --output json
```

Console output:
```
[INFO] Fetching: https://graph.facebook.com/v16.0/<form_id>/leads
[INFO] Fetched 1 items
[INFO] Wrote 1 leads to new_leads.json
[INFO] Fetched 1 raw leads, 1 new leads
```

Generated file (`new_leads.json`):
```json
[
  {
    "id": "1234567890",
    "name": "John Doe",
    "email": "johndoe@gmail.com",
    "phone": "+919876543210",
    "created_time": "2025-11-01T10:35:00+0000"
  }
]
```

---

## 🧮 Key Features Implemented
✅ Fetches leads via Meta Graph API  
✅ Reads access tokens securely from `.env`  
✅ Normalizes field data (name, email, phone)  
✅ Stores seen leads in SQLite to prevent duplicates  
✅ Supports JSON and CSV exports  
✅ Clear logging and progress output  
✅ Error handling for invalid tokens or network errors  

---

## 🧠 Learnings
- How to authenticate and interact with Meta Graph API  
- How to manage access tokens and lead form IDs securely  
- How to handle pagination, normalization, and data deduplication  
- Importance of environment isolation and clean CLI design  

---

## 📦 Final Output Files

| File | Description |
|------|--------------|
| `new_leads.json` | Cleaned lead data (new entries only) |
| `data/seen_leads.db` | SQLite DB tracking processed leads |
| `.env` | Stores API credentials and form info |

---
