import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from services.openaq_service import OpenAQService
from services.research_service import ResearchService
from services.pollutant_service import PollutantService
from services.geospatial_service import GeospatialService
from services.cause_analysis_service import EnvironmentalCauseAnalysisService
from services.storage_service import StorageService
from models.llm_manager import LLMManager
from mcp_servers.client_manager import MCPClientManager
from agent.orchestrator import ReActAgent
from qa_engine import QAEngine

app = FastAPI(
    title="TerraPulse AIR — Autonomous Air Pollution Intelligence",
    description="Autonomous AI Atmospheric Pollution Investigation & Quality Assurance Platform",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core subsystems
openaq_service = OpenAQService()
research_service = ResearchService()
pollutant_service = PollutantService()
geospatial_service = GeospatialService()
cause_service = EnvironmentalCauseAnalysisService()
storage_service = StorageService()
llm_manager = LLMManager()
mcp_manager = MCPClientManager()
agent = ReActAgent(
    mcp_manager=mcp_manager,
    llm_manager=llm_manager,
    storage_service=storage_service
)
qa_engine = QAEngine()


# ==========================================
# HEALTH & SYSTEM STATUS
# ==========================================
@app.get("/api/health")
def get_health():
    return {
        "status": "healthy",
        "service": "TerraPulse AIR",
        "version": "2.0.0"
    }


@app.get("/api/status")
def get_system_status():
    storage_stat = storage_service.get_status()
    llm_stat = llm_manager.get_status()
    servers = mcp_manager.get_registered_servers()

    return {
        "system": "TerraPulse AIR Operational",
        "llm_providers": llm_stat,
        "persistence": storage_stat,
        "mcp_servers": servers,
        "openaq_configured": bool(openaq_service.api_key),
        "research_provider": "Crossref Works API"
    }


# ==========================================
# MODULE G: AGENT CHAT ENDPOINT
# ==========================================
class AgentChatRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = "default_session"
    provider_preference: Optional[str] = "auto"


@app.get("/api/models")
def get_available_models():
    llm_stat = llm_manager.get_status()
    models = [
        {"id": "auto", "name": "Auto Failover (Gemini / Ollama)", "recommended": True},
        {"id": "gemini", "name": f"Google Gemini Cloud ({llm_stat['gemini']['model'] or 'gemini-3-flash-preview'})", "available": llm_stat["gemini"]["available"]},
        {"id": "ollama", "name": f"Ollama Local ({llm_stat['ollama']['model'] or 'granite4.2:3b'})", "available": llm_stat["ollama"]["available"]}
    ]
    return {
        "active_recommended": llm_stat.get("active_recommended", "auto"),
        "models": models,
        "llm_status": llm_stat
    }


@app.post("/api/agent/chat")
async def chat_with_agent(req: AgentChatRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="User prompt cannot be empty.")

    try:
        # Run agent with chosen provider preference (gemini, ollama, or auto)
        result = await agent.run(req.prompt, provider_preference=req.provider_preference)

        # Save session context
        storage_service.save_session(
            req.session_id or "default_session",
            {"last_prompt": req.prompt, "last_run_id": result.run_id}
        )

        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failure: {str(e)}")


@app.post("/api/agent/chat/stream")
async def chat_with_agent_stream(req: AgentChatRequest):
    """
    Live real-time token and tool execution streaming via Server-Sent Events (SSE).
    Emits tool_start, tool_done, map_update, and token events as they occur.
    """
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="User prompt cannot be empty.")

    async def sse_generator():
        try:
            async for evt in agent.run_stream(req.prompt, provider_preference=req.provider_preference):
                yield f"data: {json.dumps(evt, default=str)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/agent/trace/{run_id}")
def get_agent_trace(run_id: str):
    trace = storage_service.get_agent_trace(run_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace with run ID '{run_id}' not found.")
    return trace


# ==========================================
# MODULE A: AIR POLLUTION DATA (OpenAQ v3)
# ==========================================
@app.get("/api/environmental/locations")
def search_locations(
    query: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: int = 35000,
    iso: Optional[str] = None,
    limit: int = 10
):
    try:
        coords = (latitude, longitude) if (latitude is not None and longitude is not None) else None
        stations = openaq_service.search_locations(
            query=query,
            coordinates=coords,
            radius_meters=radius,
            iso=iso,
            limit=limit
        )
        return [s.model_dump() for s in stations]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/environmental/station/{station_id}")
def get_station_details(station_id: int):
    try:
        st = openaq_service.get_station_details(station_id)
        return st.model_dump()
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/environmental/station/{station_id}/latest")
def get_station_latest(station_id: int):
    try:
        data = openaq_service.get_latest_measurements(station_id)
        return data.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/environmental/sensor/{sensor_id}/hours")
def get_sensor_hours(sensor_id: int, limit: int = 24):
    try:
        history = openaq_service.get_sensor_hourly(sensor_id, limit=limit)
        return [h.model_dump() for h in history]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# MODULE B: SCIENTIFIC RESEARCH ENGINE
# ==========================================
@app.get("/api/research/search")
def search_research(query: str, limit: int = 5):
    try:
        res = research_service.search_publications(query, limit=limit)
        return res.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/research/doi")
def verify_doi(doi: str):
    try:
        paper = research_service.verify_doi(doi)
        if not paper:
            return {"verified": False, "message": f"DOI '{doi}' not found in Crossref registry."}
        return {"verified": True, "paper": paper.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# MODULE C: POLLUTANT INTELLIGENCE
# ==========================================
@app.get("/api/pollutant/{code}")
def get_pollutant(code: str):
    profile = pollutant_service.get_pollutant_profile(code)
    return profile.model_dump()


class PollutantCompareRequest(BaseModel):
    pollutants: List[str]


@app.post("/api/pollutant/compare")
def compare_pollutants(req: PollutantCompareRequest):
    return pollutant_service.compare_pollutants(req.pollutants)


# ==========================================
# MODULE D: ENVIRONMENTAL CAUSE ANALYSIS
# ==========================================
class CauseAnalysisRequest(BaseModel):
    location: Optional[str] = None
    measurements: Optional[List[Dict[str, Any]]] = None
    reported_observations: Optional[List[str]] = None
    meteorological_conditions: Optional[Dict[str, Any]] = None


@app.post("/api/cause-analysis")
def analyze_causes(req: CauseAnalysisRequest):
    res = cause_service.analyze(
        location=req.location,
        measurements=req.measurements,
        reported_observations=req.reported_observations,
        meteorological_conditions=req.meteorological_conditions
    )
    return res.model_dump()


# ==========================================
# MODULE E: GEOSPATIAL
# ==========================================
@app.get("/api/geospatial/geocode")
def geocode_location(location: str):
    try:
        loc = geospatial_service.geocode(location)
        return loc.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/geospatial/reverse")
def reverse_geocode(lat: float, lon: float):
    try:
        desc = geospatial_service.reverse_geocode(lat, lon)
        return {"latitude": lat, "longitude": lon, "display_name": desc}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class BufferRequest(BaseModel):
    latitude: float
    longitude: float
    radius_km: float = 2.0


@app.post("/api/geospatial/buffer")
def create_buffer(req: BufferRequest):
    try:
        buf = geospatial_service.create_investigation_buffer(req.latitude, req.longitude, req.radius_km)
        return buf.model_dump()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/geospatial/sources")
def get_emission_sources(lat: float, lon: float, radius_km: float = 10.0, limit: int = 5):
    try:
        sources = geospatial_service.find_nearby_emission_sources(lat, lon, radius_km, limit)
        return [s.model_dump() for s in sources]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================
# SECTION 4: QA WORKBENCH ENDPOINTS
# ==========================================
class ComponentTestReq(BaseModel):
    component: str
    custom_input: Optional[Dict[str, Any]] = None


@app.post("/api/qa/component/run")
async def run_component_test(req: ComponentTestReq):
    record = await qa_engine.run_component_test(req.component, req.custom_input)
    return record.model_dump()


class IntegrationTestReq(BaseModel):
    scenario_id: str


@app.post("/api/qa/integration/run")
async def run_integration_test(req: IntegrationTestReq):
    record = await qa_engine.run_integration_test(req.scenario_id)
    return record.model_dump()


class AgentTestReq(BaseModel):
    test_case_id: int


@app.post("/api/qa/agent/run")
async def run_agent_test(req: AgentTestReq):
    record = await qa_engine.run_agent_test(req.test_case_id)
    return record.model_dump()


class PromptArenaReq(BaseModel):
    prompt_id: str
    custom_prompt: Optional[str] = None


@app.post("/api/qa/prompt/run")
async def run_prompt_test(req: PromptArenaReq):
    record = await qa_engine.run_prompt_arena(req.prompt_id, req.custom_prompt)
    return record.model_dump()


class PromptBatchReq(BaseModel):
    prompt_ids: List[str]


@app.post("/api/qa/prompt/batch")
async def run_prompt_batch(req: PromptBatchReq):
    results = []
    for pid in req.prompt_ids:
        r = await qa_engine.run_prompt_arena(pid)
        results.append(r.model_dump())
    return results


@app.get("/api/qa/coverage")
def get_qa_coverage():
    return qa_engine.get_coverage_matrix()


@app.post("/api/qa/component/batch")
async def run_component_batch():
    results = await qa_engine.run_all_component_tests()
    return [r.model_dump() for r in results]


@app.post("/api/qa/integration/batch")
async def run_integration_batch():
    results = await qa_engine.run_all_integration_tests()
    return [r.model_dump() for r in results]


@app.post("/api/qa/agent/batch")
async def run_agent_batch():
    results = await qa_engine.run_all_agent_tests()
    return [r.model_dump() for r in results]


@app.post("/api/qa/prompt/batch_all")
async def run_prompt_batch_all():
    results = await qa_engine.run_all_prompt_arena_tests()
    return [r.model_dump() for r in results]


@app.get("/api/qa/audit")
def get_audit():
    audit = qa_engine.run_repository_audit()
    return audit.model_dump()


@app.get("/api/qa/history")
def get_qa_history(tab: Optional[str] = None, limit: int = 100):
    return storage_service.list_test_records(tab=tab, limit=limit)


@app.get("/api/qa/export/json")
def export_qa_json():
    records = storage_service.list_test_records(limit=500)
    audit = qa_engine.run_repository_audit()
    export_payload = {
        "title": "TerraPulse AIR — QA & Verification Workbench Export",
        "exported_at": str(datetime.now()),
        "audit": audit.model_dump(),
        "test_records": records
    }
    return JSONResponse(
        content=export_payload,
        headers={"Content-Disposition": "attachment; filename=terrapulse_qa_report.json"}
    )


@app.get("/api/qa/export/csv")
def export_qa_csv():
    records = storage_service.list_test_records(limit=500)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Test ID", "Tab", "Component / Title", "Status", "Duration (ms)",
        "Timestamp", "Expected Behavior", "Failure Explanation"
    ])
    for r in records:
        writer.writerow([
            r.get("test_id"),
            r.get("tab"),
            r.get("component"),
            r.get("status"),
            r.get("duration_ms") or r.get("execution_duration_ms"),
            r.get("timestamp"),
            r.get("expected_behavior"),
            r.get("failure_explanation") or ""
        ])
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=terrapulse_qa_results.csv"}
    )


# ==========================================
# QA WORKBENCH HTML UI SERVING
# ==========================================
WORKBENCH_HTML_PATH = Path(__file__).resolve().parent / "static" / "workbench.html"

@app.get("/workbench", response_class=HTMLResponse)
@app.get("/qa", response_class=HTMLResponse)
def serve_workbench():
    if not WORKBENCH_HTML_PATH.exists():
        raise HTTPException(status_code=404, detail="QA Workbench HTML file not found.")
    return WORKBENCH_HTML_PATH.read_text(encoding="utf-8")


# Serve frontend static assets if built
FRONTEND_DIST_PATH = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST_PATH.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST_PATH), html=True), name="frontend")
else:
    @app.get("/")
    def index_fallback():
        return HTMLResponse("""
        <html>
            <head><title>TerraPulse AIR</title></head>
            <body style="font-family: sans-serif; padding: 2rem; background: #0f172a; color: #f8fafc;">
                <h1>TerraPulse AIR Platform</h1>
                <p>Backend API is active and healthy.</p>
                <p><a style="color: #38bdf8;" href="/workbench">Launch QA &amp; Verification Workbench</a></p>
                <p><a style="color: #38bdf8;" href="/docs">FastAPI Interactive Swagger Docs</a></p>
            </body>
        </html>
        """)
