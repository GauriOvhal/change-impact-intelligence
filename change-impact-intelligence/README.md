# Change Impact Intelligence

AI-Powered Revision Impact Analysis for AEC Projects

## Overview

Change Impact Intelligence is a decision-support platform designed for Architecture, Engineering, and Construction (AEC) projects.

The platform helps project teams understand the impact of design revisions before approval by predicting cost implications, schedule delays, project risks, and downstream effects across stakeholders and dependencies.

---

## Problem Statement

In AEC projects, even small changes can trigger significant consequences across budgets, timelines, vendors, procurement, and project teams.

These impacts are often discovered too late, resulting in:

- Cost overruns
- Schedule delays
- Coordination failures
- Increased rework
- Reduced project visibility

Teams need a way to evaluate revision impacts before implementation.

---

## Solution

Change Impact Intelligence analyzes project revisions and provides:

- Cost Impact Analysis
- Timeline Impact Analysis
- Risk Assessment
- Ripple Effect Visualization
- What-If Scenario Comparison
- Executive Dashboard Insights

This enables teams to make informed decisions before approving project changes.

---

## Key Features

### Change Request Center

Create and manage revision requests for projects.

### Impact Analysis Engine

Analyze revision details and identify potential project impacts.

### Cost Impact Calculator

Estimate the financial impact of project changes.

### Timeline Impact Analyzer

Predict delays resulting from revisions.

### Risk Assessment Engine

Classify revisions as Low, Medium, or High Risk.

### Ripple Effect Visualization

Visualize how a revision affects project dependencies and workflows.

### What-If Simulator

Compare alternative decisions before approval.

### Executive Dashboard

Monitor revisions, cost impacts, delays, and project metrics.

---

## System Workflow

```text
Create Revision
       ↓
Impact Analysis
       ↓
Cost Prediction
       ↓
Timeline Prediction
       ↓
Risk Assessment
       ↓
Ripple Effect Visualization
       ↓
Decision Support
```

---

## Technology Stack

### Frontend

- HTML5
- CSS3
- JavaScript

### Backend

- Python
- FastAPI

### Database

- SQLite

### Visualization

- Chart.js

---

## System Architecture

```text
Frontend (HTML/CSS/JS)
            ↓
        FastAPI
            ↓
        SQLite
            ↓
 Impact Analysis Engine
```

---

## Project Structure

```text
change-impact-intelligence/
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── backend/
│   ├── main.py
│   ├── engines.py
│   ├── database.py
│   └── requirements.txt
│
└── README.md
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/change-impact-intelligence.git
```

Move into the project folder:

```bash
cd change-impact-intelligence
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Run the application:

```bash
uvicorn backend.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

---

## Future Enhancements

- BIM Integration
- ERP Integration
- Vendor Analytics
- Predictive Project Intelligence
- AI Recommendation Engine
- Multi-Project Impact Forecasting

---

## Hackathon Submission

**Challenge:** AS-01 – Kill the Coordination Black Hole

**Project:** Change Impact Intelligence

**Category:** Project Change Intelligence & Decision Support

---

## Team

ArchScale Intern Technology Hackathon Submission

---

## License

This project is developed for educational and hackathon purposes.