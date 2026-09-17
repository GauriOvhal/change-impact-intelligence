"""
main.py
-------
FastAPI layer for Change Impact Intelligence.

Run with:
    uvicorn main:app --reload --port 8000

Endpoints
---------
GET    /api/projects
POST   /api/projects
GET    /api/users
POST   /api/users
GET    /api/revisions            ?project_id=  (optional filter)
POST   /api/revisions
GET    /api/revisions/{id}
PATCH  /api/revisions/{id}/status
GET    /api/revisions/{id}/ripple
POST   /api/simulate
GET    /api/dashboard            ?project_id=  (optional filter)
"""

import json
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from database import init_db, db_cursor
import engines

app = FastAPI(title="Change Impact Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# ---------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------
class ProjectIn(BaseModel):
    name: str
    client: Optional[str] = None
    budget: Optional[int] = 0
    deadline: Optional[str] = None  # ISO date string, e.g. "2026-12-30"


class UserIn(BaseModel):
    name: str
    role: str = "Project Manager"


class RevisionIn(BaseModel):
    project_id: Optional[int] = 1
    created_by: Optional[int] = None
    title: str
    description: str
    category: Optional[str] = None
    priority: str = "Medium"


class SimulateOption(BaseModel):
    title: str
    description: str
    priority: str = "Medium"


class SimulateIn(BaseModel):
    options: List[SimulateOption]


class StatusIn(BaseModel):
    status: str  # "Pending Approval" | "Approved" | "Rejected"


# ---------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------
@app.get("/api/projects")
def list_projects():
    with db_cursor() as cur:
        cur.execute("SELECT * FROM Projects ORDER BY id DESC")
        return [dict(r) for r in cur.fetchall()]


@app.post("/api/projects")
def create_project(payload: ProjectIn):
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO Projects (name, client, budget, deadline) VALUES (?,?,?,?)",
            (payload.name, payload.client, payload.budget or 0, payload.deadline),
        )
        return {
            "id": cur.lastrowid,
            "name": payload.name,
            "client": payload.client,
            "budget": payload.budget or 0,
            "deadline": payload.deadline,
        }


# ---------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------
@app.get("/api/users")
def list_users():
    with db_cursor() as cur:
        cur.execute("SELECT * FROM Users ORDER BY id ASC")
        return [dict(r) for r in cur.fetchall()]


@app.post("/api/users")
def create_user(payload: UserIn):
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO Users (name, role) VALUES (?, ?)", (payload.name, payload.role)
        )
        return {"id": cur.lastrowid, "name": payload.name, "role": payload.role}


# ---------------------------------------------------------------------
# Revisions
# ---------------------------------------------------------------------
@app.get("/api/revisions")
def list_revisions(project_id: Optional[int] = None):
    with db_cursor() as cur:
        if project_id:
            cur.execute(
                "SELECT Revisions.*, Users.name AS created_by_name, Users.role AS created_by_role "
                "FROM Revisions LEFT JOIN Users ON Revisions.created_by = Users.id "
                "WHERE project_id = ? ORDER BY Revisions.id DESC",
                (project_id,),
            )
        else:
            cur.execute(
                "SELECT Revisions.*, Users.name AS created_by_name, Users.role AS created_by_role "
                "FROM Revisions LEFT JOIN Users ON Revisions.created_by = Users.id "
                "ORDER BY Revisions.id DESC"
            )
        return [dict(r) for r in cur.fetchall()]


@app.post("/api/revisions")
def create_revision(payload: RevisionIn):
    result = engines.run_full_analysis(payload.title, payload.description, payload.priority)
    rule = result.pop("_rule")
    ripple_chain = result.pop("ripple_chain")

    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO Revisions (
                project_id, created_by, title, description, category, priority,
                ai_category, affected_departments, affected_stakeholders, impact_summary,
                material_cost, labor_cost, total_cost,
                procurement_delay, installation_delay, total_delay,
                risk_score, risk_level
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                payload.project_id,
                payload.created_by,
                payload.title,
                payload.description,
                payload.category or result["category"],
                payload.priority,
                result["category"],
                ",".join(result["affected_departments"]),
                ",".join(result["affected_stakeholders"]),
                result["impact_summary"],
                result["material_cost"],
                result["labor_cost"],
                result["total_cost"],
                result["procurement_delay"],
                result["installation_delay"],
                result["total_delay"],
                result["risk_score"],
                result["risk_level"],
            ),
        )
        revision_id = cur.lastrowid

        report = {**result, "ripple_chain": ripple_chain}
        cur.execute(
            "INSERT INTO ImpactReports (revision_id, report_json) VALUES (?,?)",
            (revision_id, json.dumps(report)),
        )

    return {"id": revision_id, **result, "ripple_chain": ripple_chain}


@app.get("/api/revisions/{revision_id}")
def get_revision(revision_id: int):
    with db_cursor() as cur:
        cur.execute(
            "SELECT Revisions.*, Users.name AS created_by_name, Users.role AS created_by_role "
            "FROM Revisions LEFT JOIN Users ON Revisions.created_by = Users.id "
            "WHERE Revisions.id = ?",
            (revision_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Revision not found")
        return dict(row)


@app.patch("/api/revisions/{revision_id}/status")
def update_status(revision_id: int, payload: StatusIn):
    valid = {"Pending Approval", "Approved", "Rejected"}
    if payload.status not in valid:
        raise HTTPException(400, f"status must be one of {valid}")
    with db_cursor() as cur:
        cur.execute("SELECT id FROM Revisions WHERE id = ?", (revision_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Revision not found")
        cur.execute(
            "UPDATE Revisions SET status = ? WHERE id = ?", (payload.status, revision_id)
        )
    return {"id": revision_id, "status": payload.status}


@app.get("/api/revisions/{revision_id}/ripple")
def get_ripple(revision_id: int):
    with db_cursor() as cur:
        cur.execute("SELECT * FROM Revisions WHERE id = ?", (revision_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Revision not found")
        rule = engines._match_rule(f"{row['title']} {row['description']}")
        chain = engines.build_ripple(row["title"], rule)
        graph = engines.build_ripple_graph(row, rule)
        return {"revision_id": revision_id, "chain": chain, "graph": graph}


# ---------------------------------------------------------------------
# What-If Simulator - does NOT save anything, just runs the engines
# ---------------------------------------------------------------------
@app.post("/api/simulate")
def simulate(payload: SimulateIn):
    results = []
    for opt in payload.options:
        r = engines.run_full_analysis(opt.title, opt.description, opt.priority)
        r.pop("_rule", None)
        results.append({"title": opt.title, **r})
    return {"options": results}


# ---------------------------------------------------------------------
# Executive Dashboard
# ---------------------------------------------------------------------
@app.get("/api/dashboard")
def dashboard(project_id: Optional[int] = None):
    where = "WHERE project_id = ?" if project_id else ""
    params = (project_id,) if project_id else ()

    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM Projects")
        total_projects = cur.fetchone()["c"]

        cur.execute(f"SELECT COUNT(*) AS c FROM Revisions {where}", params)
        total_revisions = cur.fetchone()["c"]

        cur.execute(f"SELECT COALESCE(SUM(total_cost),0) AS s FROM Revisions {where}", params)
        total_cost = cur.fetchone()["s"]

        cur.execute(f"SELECT COALESCE(SUM(total_delay),0) AS s FROM Revisions {where}", params)
        total_delay = cur.fetchone()["s"]

        risk_where = (where + " AND risk_level = 'High'") if where else "WHERE risk_level = 'High'"
        cur.execute(f"SELECT COUNT(*) AS c FROM Revisions {risk_where}", params)
        high_risk = cur.fetchone()["c"]

        pending_where = (
            (where + " AND status = 'Pending Approval'")
            if where
            else "WHERE status = 'Pending Approval'"
        )
        cur.execute(f"SELECT COUNT(*) AS c FROM Revisions {pending_where}", params)
        pending = cur.fetchone()["c"]

        cur.execute(
            f"SELECT title, risk_score FROM Revisions {where} ORDER BY risk_score DESC LIMIT 1",
            params,
        )
        top = cur.fetchone()
        highest_risk_revision = dict(top) if top else None

        cur.execute(
            f"SELECT category, COUNT(*) AS c FROM Revisions {where} GROUP BY category", params
        )
        by_category = [dict(r) for r in cur.fetchall()]

        cur.execute(
            f"SELECT risk_level, COUNT(*) AS c FROM Revisions {where} GROUP BY risk_level", params
        )
        by_risk = [dict(r) for r in cur.fetchall()]

        cur.execute(
            f"SELECT id, title, total_cost, total_delay, risk_score, risk_level, status, created_at "
            f"FROM Revisions {where} ORDER BY id DESC LIMIT 10",
            params,
        )
        recent = [dict(r) for r in cur.fetchall()]

        # Revision trend: how many revisions (and how much cost) landed per day
        cur.execute(
            f"SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS count, "
            f"COALESCE(SUM(total_cost),0) AS cost "
            f"FROM Revisions {where} GROUP BY day ORDER BY day",
            params,
        )
        revision_trend = [dict(r) for r in cur.fetchall()]

        # Top requester: who is raising the most revisions
        req_where = "WHERE Revisions.project_id = ?" if project_id else ""
        cur.execute(
            f"SELECT Users.name AS name, COUNT(*) AS c FROM Revisions "
            f"JOIN Users ON Revisions.created_by = Users.id {req_where} "
            f"GROUP BY Users.id ORDER BY c DESC LIMIT 1",
            params,
        )
        top_req = cur.fetchone()
        top_requester = dict(top_req) if top_req else None

        # Active project meta (client, budget, deadline) + budget utilisation
        active_project = None
        if project_id:
            cur.execute("SELECT * FROM Projects WHERE id = ?", (project_id,))
            proj = cur.fetchone()
            if proj:
                proj = dict(proj)
                budget = proj.get("budget") or 0
                budget_used_pct = round((total_cost / budget) * 100, 1) if budget else None
                days_left = None
                if proj.get("deadline"):
                    try:
                        from datetime import date
                        d = date.fromisoformat(proj["deadline"])
                        days_left = (d - date.today()).days
                    except ValueError:
                        days_left = None
                active_project = {
                    **proj,
                    "budget_used_pct": budget_used_pct,
                    "days_left": days_left,
                }

    return {
        "active_project": active_project,
        "total_projects": total_projects,
        "total_revisions": total_revisions,
        "total_cost": total_cost,
        "total_delay": total_delay,
        "revision_trend": revision_trend,
        "high_risk_changes": high_risk,
        "pending_approvals": pending,
        "highest_risk_revision": highest_risk_revision,
        "top_requester": top_requester,
        "revisions_by_category": by_category,
        "revisions_by_risk": by_risk,
        "recent_revisions": recent,
    }


# ---------------------------------------------------------------------
# Serve the frontend (so the whole app can run from one process/port)
# ---------------------------------------------------------------------
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
