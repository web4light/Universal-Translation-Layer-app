"""
====================================================================
 Strands Good Neighbor Agent Server (FastAPI + WebMCP Bridge)
 AWS Hackathon 'Agents for Humans' (Good Neighbor Track)
 Port: 8089
====================================================================
"""

import os
import sys
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import Good Neighbor Agenta
from strands_good_neighbor_agent import GoodNeighborAgent

app = FastAPI(
    title="Strands Good Neighbor Sovereign Agent API",
    description="Decentralized accessibility agent for deaf & blind humans powered by AWS Strands Agents SDK & Ada/SPARK",
    version="1.0.0"
)

# CORS povolení pro lokální frontend a Web Studio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = GoodNeighborAgent()

class AssistRequest(BaseModel):
    query: str = Field(..., example="Přelož větu do znakové řeči a popiš scénu.")
    user_role: str = Field(default="deaf_blind_beneficiary")
    dialect: str = Field(default="CZ_ZNAK")

class AssistResponse(BaseModel):
    status: str
    mode: str
    response: str
    steps: dict

@app.get("/")
def read_root():
    return {
        "agent": "Strands Good Neighbor Sovereign Agent",
        "hackathon": "AWS Hackathon 'Agents for Humans' (Devpost 2026)",
        "track": "Good Neighbor Agents",
        "sdk": "AWS Strands Agents SDK (strands-agents 1.55.1)",
        "mode": agent.mode,
        "tools_count": len(agent.tools),
        "status": "ONLINE_HEALTHY"
    }

@app.get("/tools")
def get_tools():
    """Vrací specifikaci registrovaných nástrojů Strands SDK."""
    tools_info = []
    for t in agent.tools:
        tools_info.append({
            "name": getattr(t, "tool_name", t.__name__),
            "spec": getattr(t, "tool_spec", {})
        })
    return {"tools": tools_info}

@app.post("/assist", response_model=AssistResponse)
def run_assistant(req: AssistRequest):
    """Zpracuje asistenční požadavek přes Strands Good Neighbor Agenta."""
    try:
        pipeline_res = agent.execute_sovereign_pipeline(req.query)
        return {
            "status": "SUCCESS",
            "mode": pipeline_res.get("mode", "SOVEREIGN"),
            "response": pipeline_res.get("response", ""),
            "steps": pipeline_res.get("steps", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8089))
    print(f"[*] Spouštím Strands Good Neighbor Agent Server na portu {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
