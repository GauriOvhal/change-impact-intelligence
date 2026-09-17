"""
engines.py
----------
All the "intelligence" for Change Impact Intelligence lives here:

  1. analyze_change()   -> AI Change Analyzer (category, departments,
                            stakeholders, impact summary)
  2. calculate_cost()   -> Cost Impact Calculator
  3. calculate_timeline()-> Timeline Impact Analyzer
  4. calculate_risk()   -> Risk Assessment Engine
  5. build_ripple()     -> Ripple Effect chain for the graph page

Everything works fully offline with a rule-based model, so the app
runs with zero API keys. If a GEMINI_API_KEY environment variable is
set, analyze_change() will additionally ask Gemini for a sharper,
natural-language impact summary and merge it in - see call_gemini().
"""

import os
import re
import json
import urllib.request

# ---------------------------------------------------------------------
# 1. Category rules - keyword -> (category, departments, base cost, base delay)
# ---------------------------------------------------------------------
CATEGORY_RULES = [
    {
        "keywords": ["floor", "marble", "tile", "granite", "flooring", "skirting"],
        "category": "Material Change",
        "departments": ["Procurement", "Vendor", "Site Team"],
        "base_material_cost": 55000,
        "base_labor_cost": 15000,
        "base_procurement_delay": 3,
        "base_installation_delay": 2,
        "dependency_weight": 2,
    },
    {
        "keywords": ["wall", "partition", "layout", "demolish", "knock down", "column"],
        "category": "Structural Change",
        "departments": ["Civil", "Electrical", "Design", "Structural Engineer"],
        "base_material_cost": 40000,
        "base_labor_cost": 35000,
        "base_procurement_delay": 2,
        "base_installation_delay": 6,
        "dependency_weight": 4,
    },
    {
        "keywords": ["ceiling", "false ceiling", "pop", "gypsum", "cove lighting"],
        "category": "Finishing Change",
        "departments": ["Civil", "Electrical", "Interior Team"],
        "base_material_cost": 30000,
        "base_labor_cost": 20000,
        "base_procurement_delay": 2,
        "base_installation_delay": 3,
        "dependency_weight": 3,
    },
    {
        "keywords": ["plumb", "pipe", "bathroom", "washroom", "sanitary", "faucet"],
        "category": "Plumbing Change",
        "departments": ["Plumbing", "Civil", "Vendor"],
        "base_material_cost": 25000,
        "base_labor_cost": 18000,
        "base_procurement_delay": 2,
        "base_installation_delay": 3,
        "dependency_weight": 3,
    },
    {
        "keywords": ["electric", "wiring", "socket", "mcb", "switchboard", "light point"],
        "category": "Electrical Change",
        "departments": ["Electrical", "Safety", "Site Team"],
        "base_material_cost": 15000,
        "base_labor_cost": 12000,
        "base_procurement_delay": 1,
        "base_installation_delay": 2,
        "dependency_weight": 2,
    },
    {
        "keywords": ["paint", "colour", "color", "finish", "texture"],
        "category": "Aesthetic Change",
        "departments": ["Interior Team", "Vendor"],
        "base_material_cost": 12000,
        "base_labor_cost": 8000,
        "base_procurement_delay": 1,
        "base_installation_delay": 1,
        "dependency_weight": 1,
    },
]

DEFAULT_RULE = {
    "category": "General Change",
    "departments": ["Site Team", "Project Manager"],
    "base_material_cost": 10000,
    "base_labor_cost": 8000,
    "base_procurement_delay": 1,
    "base_installation_delay": 1,
    "dependency_weight": 1,
}

PRIORITY_MULTIPLIER = {"Low": 0.8, "Medium": 1.0, "High": 1.35, "Urgent": 1.6}

PREMIUM_WORDS = ["italian", "premium", "custom", "imported", "designer", "luxury"]
BUDGET_WORDS = ["standard", "budget", "basic", "local"]


def _match_rule(text: str):
    text = text.lower()
    for rule in CATEGORY_RULES:
        if any(kw in text for kw in rule["keywords"]):
            return rule
    return DEFAULT_RULE


def _cost_scale(text: str) -> float:
    text = text.lower()
    scale = 1.0
    if any(w in text for w in PREMIUM_WORDS):
        scale += 0.5
    if any(w in text for w in BUDGET_WORDS):
        scale -= 0.3
    return max(scale, 0.4)


# ---------------------------------------------------------------------
# Optional Gemini call - safe no-op if no key is configured
# ---------------------------------------------------------------------
def call_gemini(prompt: str) -> str | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash:generateContent?key={api_key}"
        )
        payload = json.dumps(
            {"contents": [{"parts": [{"text": prompt}]}]}
        ).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        # Never let a network / quota issue break the app - fall back
        # to the rule-based summary instead.
        return None


# ---------------------------------------------------------------------
# 2. AI Change Analyzer
# ---------------------------------------------------------------------
def analyze_change(title: str, description: str):
    rule = _match_rule(f"{title} {description}")
    departments = rule["departments"]
    stakeholders = list(dict.fromkeys(departments + ["Client", "Vendor"]))

    summary = (
        f"This is a {rule['category'].lower()} affecting "
        f"{', '.join(departments)}. Expect vendor coordination and "
        f"a procurement/installation cycle before it can be closed out."
    )

    gemini_summary = call_gemini(
        "In two short sentences, explain the practical impact of this "
        f"construction change request on schedule, cost and coordination: "
        f'"{title}: {description}"'
    )
    if gemini_summary:
        summary = gemini_summary

    return {
        "category": rule["category"],
        "affected_departments": departments,
        "affected_stakeholders": stakeholders,
        "impact_summary": summary,
        "_rule": rule,
    }


# ---------------------------------------------------------------------
# 3. Cost Impact Calculator
# ---------------------------------------------------------------------
def calculate_cost(rule: dict, priority: str, text: str):
    p_mult = PRIORITY_MULTIPLIER.get(priority, 1.0)
    c_scale = _cost_scale(text)

    material_cost = round(rule["base_material_cost"] * p_mult * c_scale)
    labor_cost = round(rule["base_labor_cost"] * p_mult * c_scale)
    total = material_cost + labor_cost

    return {
        "material_cost": material_cost,
        "labor_cost": labor_cost,
        "total_cost": total,
    }


# ---------------------------------------------------------------------
# 4. Timeline Impact Analyzer
# ---------------------------------------------------------------------
def calculate_timeline(rule: dict, priority: str, text: str):
    p_mult = PRIORITY_MULTIPLIER.get(priority, 1.0)
    c_scale = _cost_scale(text)

    procurement_delay = max(1, round(rule["base_procurement_delay"] * p_mult * c_scale))
    installation_delay = max(1, round(rule["base_installation_delay"] * p_mult * c_scale))
    total_delay = procurement_delay + installation_delay

    return {
        "procurement_delay": procurement_delay,
        "installation_delay": installation_delay,
        "total_delay": total_delay,
    }


# ---------------------------------------------------------------------
# 5. Risk Assessment Engine
# ---------------------------------------------------------------------
def calculate_risk(cost: dict, timeline: dict, rule: dict):
    # Normalise each factor to a 0-100 sub-score, then weight them.
    cost_score = min(100, (cost["total_cost"] / 100000) * 100)       # ₹1L = 100
    delay_score = min(100, (timeline["total_delay"] / 10) * 100)      # 10 days = 100
    dependency_score = min(100, rule["dependency_weight"] * 20)       # 5 depts = 100
    vendor_score = 60 if "Vendor" in rule["departments"] else 20

    risk_score = round(
        cost_score * 0.35
        + delay_score * 0.30
        + dependency_score * 0.20
        + vendor_score * 0.15
    )
    risk_score = min(100, max(0, risk_score))

    if risk_score < 40:
        level = "Low"
    elif risk_score < 70:
        level = "Medium"
    else:
        level = "High"

    return {"risk_score": risk_score, "risk_level": level}


# ---------------------------------------------------------------------
# 6. Ripple Effect chain builder
# ---------------------------------------------------------------------
def build_ripple(title: str, rule: dict):
    chain = [title]
    category = rule["category"]

    if category == "Material Change":
        chain += ["Vendor Requote", "Material Procurement", "Installation Delay", "Project Completion Shift"]
    elif category == "Structural Change":
        chain += ["Design Review", "Civil Approval", "Electrical Rework", "Timeline Shift"]
    elif category == "Finishing Change":
        chain += ["Design Sign-off", "Material Order", "Ceiling Installation", "Handover Delay"]
    elif category == "Plumbing Change":
        chain += ["Vendor Quote", "Pipe Rerouting", "Civil Patch Work", "Fixture Installation"]
    elif category == "Electrical Change":
        chain += ["Load Recalculation", "Wiring Rework", "Safety Inspection"]
    elif category == "Aesthetic Change":
        chain += ["Sample Approval", "Material Procurement", "Application"]
    else:
        chain += ["Site Assessment", "Resource Allocation", "Execution", "Schedule Update"]

    return chain


# ---------------------------------------------------------------------
# 6b. Ripple Effect - graph structure (for the interactive graph view)
# ---------------------------------------------------------------------
def build_ripple_graph(revision_row, rule: dict):
    """
    Builds a small branching dependency graph instead of a flat chain:

        Revision --> [Department A]  --\
                  --> [Department B]  ---> Cost Impact   --\
                  --> [Department C]  --/                    --> Outcome
                                          Timeline Impact  --/

    Returns {"nodes": [...], "edges": [...]} where each node carries a
    "column" (0-3) so the frontend can lay it out without guessing.
    """
    title = revision_row["title"]
    departments = rule["departments"]
    category = revision_row["category"] or rule["category"]

    outcome_label = {
        "Material Change": "Project Completion Shift",
        "Structural Change": "Timeline Shift",
        "Finishing Change": "Handover Delay",
        "Plumbing Change": "Fixture Installation Delay",
        "Electrical Change": "Safety Sign-off Delay",
        "Aesthetic Change": "Finish Approval Delay",
    }.get(category, "Schedule Update")

    nodes = [
        {"id": "origin", "label": title, "type": "origin", "column": 0}
    ]
    edges = []

    for i, dept in enumerate(departments):
        node_id = f"dept-{i}"
        nodes.append({"id": node_id, "label": dept, "type": "department", "column": 1})
        edges.append({"from": "origin", "to": node_id})
        edges.append({"from": node_id, "to": "cost"})
        edges.append({"from": node_id, "to": "timeline"})

    nodes.append({
        "id": "cost",
        "label": f"Cost Impact: +₹{revision_row['total_cost']:,}",
        "type": "cost",
        "column": 2,
    })
    nodes.append({
        "id": "timeline",
        "label": f"Timeline Impact: +{revision_row['total_delay']} days",
        "type": "timeline",
        "column": 2,
    })
    nodes.append({"id": "outcome", "label": outcome_label, "type": "outcome", "column": 3})
    edges.append({"from": "cost", "to": "outcome"})
    edges.append({"from": "timeline", "to": "outcome"})

    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------
# Convenience: run the full pipeline for one revision in one call
# ---------------------------------------------------------------------
def run_full_analysis(title: str, description: str, priority: str = "Medium"):
    text = f"{title} {description}"
    analysis = analyze_change(title, description)
    rule = analysis.pop("_rule")

    cost = calculate_cost(rule, priority, text)
    timeline = calculate_timeline(rule, priority, text)
    risk = calculate_risk(cost, timeline, rule)
    ripple = build_ripple(title, rule)

    return {**analysis, **cost, **timeline, **risk, "ripple_chain": ripple, "_rule": rule}
