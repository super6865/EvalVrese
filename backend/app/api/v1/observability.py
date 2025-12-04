"""
Observability API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.core.database import get_db
from app.services.observability_service import ObservabilityService
from app.services.dataset_service import DatasetService
from app.utils.api_decorators import handle_api_errors, handle_not_found

router = APIRouter()


# Request models
class TraceCreateFromData(BaseModel):
    dataset_name: str
    trace_ids: list[str]
    field_mapping: dict  # Map trace/span fields to dataset fields


# Trace endpoints
@router.get("/traces")
async def list_traces(
    service_name: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List traces with filters"""
    service = ObservabilityService(db)
    traces, total = service.list_traces(
        service_name=service_name,
        start_time=start_time,
        end_time=end_time,
        skip=skip,
        limit=limit,
    )
    return {"traces": traces, "total": total}


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str, db: Session = Depends(get_db)):
    """Get trace by ID with spans"""
    service = ObservabilityService(db)
    return service.get_trace_with_spans(trace_id)

@router.get("/traces/{trace_id}/detail")
async def get_trace_detail(trace_id: str, db: Session = Depends(get_db)):
    """Get trace detail with span tree"""
    service = ObservabilityService(db)
    return service.get_trace_tree(trace_id)


@router.get("/traces/{trace_id}/spans")
async def list_spans(trace_id: str, db: Session = Depends(get_db)):
    """List all spans for a trace"""
    service = ObservabilityService(db)
    spans = service.list_spans(trace_id)
    return {"spans": spans, "total": len(spans)}


@router.get("/spans/{span_id}")
@handle_not_found("Span not found")
async def get_span(span_id: str, db: Session = Depends(get_db)):
    """Get span by ID"""
    service = ObservabilityService(db)
    return service.get_span(span_id)


# OTLP endpoints
@router.post("/otlp/v1/traces")
async def receive_otlp_traces(request: Request, db: Session = Depends(get_db)):
    """
    Receive OTLP traces (simplified implementation)
    In production, you would use opentelemetry-exporter-otlp-proto-http
    """
    try:
        # Parse OTLP JSON format (simplified)
        data = await request.json()
        service = ObservabilityService(db)
        
        # Process traces from OTLP format
        # This is a simplified version - in production, use proper OTLP parser
        resource_spans = data.get("resourceSpans", [])
        
        created_traces = []
        for resource_span in resource_spans:
            resource = resource_span.get("resource", {})
            service_name = resource.get("attributes", {}).get("service.name", "unknown")
            
            scope_spans = resource_span.get("scopeSpans", [])
            for scope_span in scope_spans:
                spans_data = scope_span.get("spans", [])
                
                # Group spans by trace_id
                traces_map = {}
                for span_data in spans_data:
                    trace_id = span_data.get("traceId", "")
                    if trace_id not in traces_map:
                        traces_map[trace_id] = {
                            "trace_id": trace_id,
                            "service_name": service_name,
                            "spans": [],
                        }
                    traces_map[trace_id]["spans"].append(span_data)
                
                # Create traces and spans
                for trace_id, trace_info in traces_map.items():
                    spans = trace_info["spans"]
                    if not spans:
                        continue
                    
                    # Calculate trace start/end time
                    start_times = [s.get("startTimeUnixNano", 0) for s in spans]
                    end_times = [s.get("endTimeUnixNano", 0) for s in spans if s.get("endTimeUnixNano")]
                    
                    start_time = datetime.fromtimestamp(min(start_times) / 1e9) if start_times else datetime.utcnow()
                    end_time = datetime.fromtimestamp(max(end_times) / 1e9) if end_times else None
                    duration_ms = ((max(end_times) - min(start_times)) / 1e6) if end_times and start_times else None
                    
                    # Create trace
                    trace = service.create_trace({
                        "trace_id": trace_id,
                        "service_name": service_name,
                        "operation_name": spans[0].get("name", ""),
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration_ms": duration_ms,
                    })
                    created_traces.append(trace)
                    
                    # Create spans
                    for span_data in spans:
                        span_start = datetime.fromtimestamp(span_data.get("startTimeUnixNano", 0) / 1e9)
                        span_end = None
                        if span_data.get("endTimeUnixNano"):
                            span_end = datetime.fromtimestamp(span_data.get("endTimeUnixNano") / 1e9)
                        
                        span = service.create_span({
                            "trace_id": trace_id,
                            "span_id": span_data.get("spanId", ""),
                            "parent_span_id": span_data.get("parentSpanId"),
                            "name": span_data.get("name", ""),
                            "kind": span_data.get("kind"),
                            "start_time": span_start,
                            "end_time": span_end,
                            "duration_ms": (span_data.get("endTimeUnixNano", 0) - span_data.get("startTimeUnixNano", 0)) / 1e6 if span_data.get("endTimeUnixNano") else None,
                            "status_code": span_data.get("status", {}).get("code"),
                            "status_message": span_data.get("status", {}).get("message"),
                            "attributes": span_data.get("attributes", []),
                            "events": span_data.get("events", []),
                            "links": span_data.get("links", []),
                        })
        
        return {"message": "Traces received", "count": len(created_traces)}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing OTLP data: {str(e)}")


# Create dataset from traces
@router.post("/traces/create-dataset")
async def create_dataset_from_traces(data: TraceCreateFromData, db: Session = Depends(get_db)):
    """Create a dataset from trace data"""
    service = ObservabilityService(db)
    dataset_service = DatasetService(db)
    
    # Get traces
    traces = []
    for trace_id in data.trace_ids:
        trace = service.get_trace(trace_id)
        if trace:
            traces.append(trace)
    
    if not traces:
        raise HTTPException(status_code=404, detail="No traces found")
    
    # Create dataset
    dataset = dataset_service.create_dataset(
        name=data.dataset_name,
        description=f"Dataset created from {len(traces)} traces",
    )
    
    # Create schema (simplified - you'd define proper schema based on field_mapping)
    field_definitions = [
        {"key": "input", "name": "Input", "type": "text"},
        {"key": "reference_output", "name": "Reference Output", "type": "text"},
    ]
    
    schema = dataset_service.create_schema(
        dataset_id=dataset.id,
        name="default",
        field_definitions=field_definitions,
    )
    
    # Create version
    version = dataset_service.create_version(
        dataset_id=dataset.id,
        version="v1.0",
        schema_id=schema.id,
    )
    
    # Create items from traces
    items = []
    for trace in traces:
        # Extract data based on field_mapping
        # This is simplified - in production, you'd properly map trace/span data
        input_data = trace.attributes.get(data.field_mapping.get("input", "input"), "") if trace.attributes else ""
        reference_output = trace.attributes.get(data.field_mapping.get("reference_output", "reference_output"), "") if trace.attributes else ""
        
        item = dataset_service.create_item(
            dataset_id=dataset.id,
            version_id=version.id,
            data_content={
                "input": str(input_data),
                "reference_output": str(reference_output),
            },
        )
        items.append(item)
    
    return {
        "dataset_id": dataset.id,
        "version_id": version.id,
        "items_count": len(items),
    }
