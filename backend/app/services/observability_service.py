"""
Observability service
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from app.models.trace import Trace, Span
from app.infra.tracer.span import Span as TracerSpan


class ObservabilityService:
    def __init__(self, db: Session):
        self.db = db

    # Trace management
    def create_trace(self, trace_data: Dict[str, Any]) -> Trace:
        """Create a trace from OTLP data"""
        trace = Trace(
            trace_id=trace_data.get("trace_id"),
            service_name=trace_data.get("service_name"),
            operation_name=trace_data.get("operation_name"),
            start_time=trace_data.get("start_time", datetime.utcnow()),
            end_time=trace_data.get("end_time"),
            duration_ms=trace_data.get("duration_ms"),
            status_code=trace_data.get("status_code"),
            attributes=trace_data.get("attributes"),
        )
        self.db.add(trace)
        self.db.commit()
        self.db.refresh(trace)
        return trace

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get trace by trace_id"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"[ObservabilityService] get_trace called with trace_id: '{trace_id}' (type: {type(trace_id).__name__}, length: {len(trace_id) if trace_id else 0})")
        
        # Ensure trace_id is a string
        if not isinstance(trace_id, str):
            trace_id = str(trace_id)
            logger.debug(f"[ObservabilityService] Converted trace_id to string: '{trace_id}'")
        
        trace = self.db.query(Trace).filter(Trace.trace_id == trace_id).first()
        
        if trace:
            logger.debug(f"[ObservabilityService] Found trace: id={trace.id}, trace_id='{trace.trace_id}', service_name='{trace.service_name}'")
        else:
            # Log all trace_ids in database for debugging (limit to 10 to avoid performance issues)
            sample_traces = self.db.query(Trace.trace_id).limit(10).all()
            logger.debug(f"[ObservabilityService] Trace not found. Sample trace_ids in database: {[t[0] for t in sample_traces]}")
        
        return trace

    def list_traces(
        self,
        service_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Trace], int]:
        """List traces with filters and pagination"""
        query = self.db.query(Trace)
        
        if service_name:
            query = query.filter(Trace.service_name == service_name)
        
        if start_time:
            query = query.filter(Trace.start_time >= start_time)
        
        if end_time:
            query = query.filter(Trace.start_time <= end_time)
        
        total = query.count()
        traces = query.order_by(Trace.start_time.desc()).offset(skip).limit(limit).all()
        return traces, total

    # Span management
    def create_span(self, span_data: Dict[str, Any]) -> Span:
        """Create a span from OTLP data"""
        span = Span(
            trace_id=span_data.get("trace_id"),
            span_id=span_data.get("span_id"),
            parent_span_id=span_data.get("parent_span_id"),
            name=span_data.get("name"),
            kind=span_data.get("kind"),
            start_time=span_data.get("start_time", datetime.utcnow()),
            end_time=span_data.get("end_time"),
            duration_ms=span_data.get("duration_ms"),
            status_code=span_data.get("status_code"),
            status_message=span_data.get("status_message"),
            attributes=span_data.get("attributes"),
            events=span_data.get("events"),
            links=span_data.get("links"),
        )
        self.db.add(span)
        self.db.commit()
        self.db.refresh(span)
        return span

    def get_span(self, span_id: str) -> Optional[Span]:
        """Get span by span_id"""
        return self.db.query(Span).filter(Span.span_id == span_id).first()

    def list_spans(self, trace_id: str) -> List[Span]:
        """List all spans for a trace"""
        return self.db.query(Span).filter(Span.trace_id == trace_id).order_by(Span.start_time).all()

    def get_trace_with_spans(self, trace_id: str) -> Dict[str, Any]:
        """Get trace with all its spans"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug(f"[ObservabilityService] get_trace_with_spans called with trace_id: {trace_id} (type: {type(trace_id).__name__})")
        
        trace = self.get_trace(trace_id)
        if not trace:
            logger.warning(f"[ObservabilityService] Trace {trace_id} not found in database")
            # Return empty structure instead of None to avoid 404
            return {
                "trace": None,
                "spans": [],
            }
        
        logger.debug(f"[ObservabilityService] Found trace {trace_id}, querying spans...")
        spans = self.list_spans(trace_id)
        logger.debug(f"[ObservabilityService] Found {len(spans)} spans for trace {trace_id}")
        
        return {
            "trace": trace,
            "spans": spans,
        }
    
    # Batch operations
    def batch_create_traces(self, traces_data: List[Dict[str, Any]]) -> List[Trace]:
        """Batch create traces"""
        traces = []
        for trace_data in traces_data:
            trace = Trace(
                trace_id=trace_data.get("trace_id"),
                service_name=trace_data.get("service_name"),
                operation_name=trace_data.get("operation_name"),
                start_time=trace_data.get("start_time", datetime.utcnow()),
                end_time=trace_data.get("end_time"),
                duration_ms=trace_data.get("duration_ms"),
                status_code=trace_data.get("status_code"),
                attributes=trace_data.get("attributes"),
            )
            traces.append(trace)
            self.db.add(trace)
        
        self.db.commit()
        for trace in traces:
            self.db.refresh(trace)
        return traces
    
    def batch_create_spans(self, spans_data: List[Dict[str, Any]]) -> List[Span]:
        """Batch create spans with individual error handling"""
        import logging
        logger = logging.getLogger(__name__)
        
        spans = []
        successful_spans = []
        failed_spans = []
        
        # Check for duplicate span_ids before attempting to save
        span_ids = [span_data.get("span_id") for span_data in spans_data if span_data.get("span_id")]
        duplicate_span_ids = [span_id for span_id in span_ids if span_ids.count(span_id) > 1]
        if duplicate_span_ids:
            logger.error(f"[ObservabilityService] Found duplicate span_ids: {set(duplicate_span_ids)}")
            raise ValueError(f"Duplicate span_ids found: {set(duplicate_span_ids)}")
        
        # Check for existing span_ids in database
        existing_span_ids = set()
        if span_ids:
            existing = self.db.query(Span.span_id).filter(Span.span_id.in_(span_ids)).all()
            existing_span_ids = {row[0] for row in existing}
            if existing_span_ids:
                logger.warning(f"[ObservabilityService] Found {len(existing_span_ids)} existing span_ids in database: {existing_span_ids}")
        
        logger.info(f"[ObservabilityService] Processing {len(spans_data)} spans for batch creation")
        
        # Process each span individually to catch errors
        for idx, span_data in enumerate(spans_data):
            span_id = span_data.get("span_id")
            span_name = span_data.get("name", "unknown")
            
            try:
                # Skip if span_id already exists
                if span_id in existing_span_ids:
                    logger.warning(f"[ObservabilityService] Span {idx} ({span_name}, span_id={span_id}) already exists, skipping")
                    # Try to fetch existing span
                    existing_span = self.db.query(Span).filter(Span.span_id == span_id).first()
                    if existing_span:
                        successful_spans.append(existing_span)
                    continue
                
                # Validate required fields
                if not span_id:
                    logger.error(f"[ObservabilityService] Span {idx} ({span_name}) missing span_id, skipping")
                    failed_spans.append({"index": idx, "name": span_name, "error": "Missing span_id"})
                    continue
                
                if not span_data.get("trace_id"):
                    logger.error(f"[ObservabilityService] Span {idx} ({span_name}, span_id={span_id}) missing trace_id, skipping")
                    failed_spans.append({"index": idx, "name": span_name, "span_id": span_id, "error": "Missing trace_id"})
                    continue
                
                # Create span object
                span = Span(
                    trace_id=span_data.get("trace_id"),
                    span_id=span_id,
                    parent_span_id=span_data.get("parent_span_id"),
                    name=span_name,
                    kind=span_data.get("kind"),
                    start_time=span_data.get("start_time", datetime.utcnow()),
                    end_time=span_data.get("end_time"),
                    duration_ms=span_data.get("duration_ms"),
                    status_code=span_data.get("status_code"),
                    status_message=span_data.get("status_message"),
                    attributes=span_data.get("attributes"),
                    events=span_data.get("events"),
                    links=span_data.get("links"),
                )
                
                # Add to session
                self.db.add(span)
                spans.append(span)
                logger.debug(f"[ObservabilityService] Added span {idx} to session: name={span_name}, span_id={span_id}, parent_span_id={span_data.get('parent_span_id')}")
                
            except Exception as e:
                logger.error(f"[ObservabilityService] Error creating span {idx} ({span_name}, span_id={span_id}): {str(e)}", exc_info=True)
                failed_spans.append({"index": idx, "name": span_name, "span_id": span_id, "error": str(e)})
        
        # Commit all spans at once
        if spans:
            try:
                logger.info(f"[ObservabilityService] Committing {len(spans)} spans to database")
                self.db.commit()
                logger.info(f"[ObservabilityService] Successfully committed {len(spans)} spans")
                
                # Refresh spans to get database-generated fields
                for span in spans:
                    try:
                        self.db.refresh(span)
                        successful_spans.append(span)
                    except Exception as e:
                        logger.error(f"[ObservabilityService] Error refreshing span {span.span_id}: {str(e)}", exc_info=True)
                        failed_spans.append({"span_id": span.span_id, "error": f"Refresh error: {str(e)}"})
            except Exception as e:
                logger.error(f"[ObservabilityService] Error committing spans: {str(e)}", exc_info=True)
                self.db.rollback()
                raise
        
        # Log summary
        logger.info(f"[ObservabilityService] Batch create summary: {len(successful_spans)} successful, {len(failed_spans)} failed")
        if failed_spans:
            logger.warning(f"[ObservabilityService] Failed spans details: {failed_spans}")
        
        return successful_spans
    
    # Experiment-related queries
    def get_traces_by_experiment_id(self, experiment_id: int, run_id: Optional[int] = None) -> List[Trace]:
        """Get all traces for an experiment"""
        from app.models.experiment import ExperimentResult
        
        # Get unique trace IDs from experiment results
        query = self.db.query(ExperimentResult.trace_id).filter(
            ExperimentResult.experiment_id == experiment_id,
            ExperimentResult.trace_id.isnot(None)
        )
        
        if run_id:
            query = query.filter(ExperimentResult.run_id == run_id)
        
        trace_ids = [tid[0] for tid in query.distinct().all() if tid[0]]
        
        if not trace_ids:
            return []
        
        return self.db.query(Trace).filter(Trace.trace_id.in_(trace_ids)).order_by(Trace.start_time.desc()).all()
    
    def get_traces_by_run_id(self, run_id: int) -> List[Trace]:
        """Get all traces for a specific run"""
        from app.models.experiment import ExperimentResult
        
        trace_ids = self.db.query(ExperimentResult.trace_id).filter(
            ExperimentResult.run_id == run_id,
            ExperimentResult.trace_id.isnot(None)
        ).distinct().all()
        
        if not trace_ids:
            return []
        
        trace_id_list = [tid[0] for tid in trace_ids]
        return self.db.query(Trace).filter(Trace.trace_id.in_(trace_id_list)).order_by(Trace.start_time.desc()).all()
    
    def save_tracer_span(self, span: TracerSpan) -> Span:
        """Save a tracer span to database"""
        span_dict = span.to_dict()
        return self.create_span(span_dict)
    
    def save_span(self, span: TracerSpan) -> Span:
        """
        Save a single span to database (used by DatabaseTracer).
        This follows coze-loop's pattern where each span is saved individually.
        
        Args:
            span: TracerSpan to save
            
        Returns:
            Saved Span model instance
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Check if span already exists (avoid duplicate save)
        existing_span = self.get_span(span.span_id)
        if existing_span:
            logger.debug(f"[ObservabilityService] Span {span.span_id} already exists, skipping save")
            return existing_span
        
        # Determine if this is root span (parent_span_id is None or empty)
        is_root_span = not span.parent_span_id or span.parent_span_id == ""
        
        # Ensure trace exists (create if this is root span)
        trace = self.get_trace(span.trace_id)
        if not trace:
            if is_root_span:
                # Create trace from root span
                trace_data = {
                    "trace_id": span.trace_id,
                    "service_name": "experiment",
                    "operation_name": span.name,
                    "start_time": span.start_time,
                    "end_time": span.end_time,
                    "duration_ms": span.duration_ms,
                    "status_code": span.status_code,
                    "attributes": span.attributes,
                }
                trace = self.create_trace(trace_data)
                logger.info(f"[ObservabilityService] Created trace {span.trace_id} from root span {span.span_id}")
            else:
                # Child span but trace doesn't exist - this shouldn't happen
                # But we'll create trace anyway to avoid data loss
                logger.warning(f"[ObservabilityService] Child span {span.span_id} saved but trace {span.trace_id} doesn't exist, creating trace")
                trace_data = {
                    "trace_id": span.trace_id,
                    "service_name": "experiment",
                    "operation_name": f"experiment_trace_{span.trace_id[:8]}",
                    "start_time": span.start_time,
                    "end_time": span.end_time,
                    "duration_ms": span.duration_ms,
                    "status_code": span.status_code,
                    "attributes": span.attributes,
                }
                trace = self.create_trace(trace_data)
        
        # Save span with error handling for unique constraint
        try:
            span_data = span.to_dict()
            span_data["trace_id"] = span.trace_id
            logger.info(f"[ObservabilityService] 🔄 Attempting to save span: span_id={span.span_id}, name={span.name}, trace_id={span.trace_id}, parent_span_id={span.parent_span_id}")
            logger.info(f"[ObservabilityService]   - span_data keys: {list(span_data.keys())}")
            
            saved_span = self.create_span(span_data)
            
            # Verify span was actually saved to database
            if saved_span:
                logger.info(f"[ObservabilityService] ✅ Span created via create_span: span_id={saved_span.span_id}, db_id={saved_span.id if hasattr(saved_span, 'id') else 'N/A'}")
                
                # Double-check by querying database
                verified_span = self.get_span(span.span_id)
                if verified_span:
                    logger.info(f"[ObservabilityService] ✅ VERIFIED: Span {span.span_id} exists in database (db_id={verified_span.id if hasattr(verified_span, 'id') else 'N/A'})")
                else:
                    logger.error(f"[ObservabilityService] ❌ CRITICAL: Span {span.span_id} was created but NOT found in database!")
                
                logger.info(f"[ObservabilityService] ✅ Successfully saved span {span.span_id} (name={span.name}, parent={span.parent_span_id}, is_root={is_root_span})")
                return saved_span
            else:
                logger.error(f"[ObservabilityService] ❌ CRITICAL: create_span returned None! span_id={span.span_id}")
                return None
                
        except Exception as e:
            # Check if it's a unique constraint violation
            error_str = str(e).lower()
            if "unique" in error_str or "duplicate" in error_str:
                logger.warning(f"[ObservabilityService] ⚠️ Span {span.span_id} already exists (unique constraint), fetching existing")
                existing = self.get_span(span.span_id)
                if existing:
                    logger.info(f"[ObservabilityService] ✅ Found existing span {span.span_id} in database (db_id={existing.id if hasattr(existing, 'id') else 'N/A'})")
                    return existing
                else:
                    logger.error(f"[ObservabilityService] ❌ CRITICAL: Unique constraint error but span {span.span_id} not found in database!")
            # Re-raise if it's a different error
            logger.error(f"[ObservabilityService] ❌ ERROR saving span {span.span_id}: {str(e)}", exc_info=True)
            logger.error(f"[ObservabilityService]   - Exception type: {type(e).__name__}")
            logger.error(f"[ObservabilityService]   - Exception args: {e.args}")
            raise
    
    def save_trace_and_spans(self, trace_data: Dict[str, Any], spans: List[TracerSpan]) -> Trace:
        """Save a trace and its spans to database"""
        import logging
        logger = logging.getLogger(__name__)
        
        trace_id = trace_data.get('trace_id')
        logger.info(f"[ObservabilityService] ========== Saving trace {trace_id} with {len(spans)} spans ==========")
        
        # Validate spans list
        if not spans:
            logger.warning(f"[ObservabilityService] No spans provided for trace {trace_id}")
        else:
            # Log all spans before processing
            logger.info(f"[ObservabilityService] Spans to save:")
            for idx, span in enumerate(spans):
                logger.info(f"[ObservabilityService]   Span {idx}: name='{span.name}', span_id='{span.span_id}', parent_span_id='{span.parent_span_id}', finished={getattr(span, '_is_finished', 'unknown')}")
            
            # Check for duplicate span_ids in the list
            span_ids = [getattr(span, 'span_id', None) for span in spans]
            unique_span_ids = set(span_ids)
            if len(span_ids) != len(unique_span_ids):
                duplicates = [span_id for span_id in span_ids if span_ids.count(span_id) > 1]
                logger.error(f"[ObservabilityService] Found duplicate span_ids in spans list: {set(duplicates)}")
                for idx, span in enumerate(spans):
                    if span.span_id in duplicates:
                        logger.error(f"[ObservabilityService]   Duplicate span at index {idx}: name='{span.name}', span_id='{span.span_id}'")
        
        # Create trace
        try:
            trace = self.create_trace(trace_data)
            logger.info(f"[ObservabilityService] Created trace: {trace.trace_id}")
        except Exception as e:
            logger.error(f"[ObservabilityService] Error creating trace {trace_id}: {str(e)}", exc_info=True)
            raise
        
        # Create spans
        span_data_list = []
        for idx, span in enumerate(spans):
            try:
                # Validate span before converting
                if not hasattr(span, 'span_id') or not span.span_id:
                    logger.error(f"[ObservabilityService] Span {idx} ({getattr(span, 'name', 'unknown')}) missing span_id, skipping")
                    continue
                
                if not hasattr(span, 'to_dict'):
                    logger.error(f"[ObservabilityService] Span {idx} ({getattr(span, 'name', 'unknown')}) missing to_dict method, skipping")
                    continue
                
                span_dict = span.to_dict()
                span_dict["trace_id"] = trace.trace_id
                span_data_list.append(span_dict)
                logger.debug(f"[ObservabilityService] Prepared span {idx}: name={span.name}, span_id={span.span_id}, parent_span_id={span.parent_span_id}")
            except Exception as e:
                logger.error(f"[ObservabilityService] Error preparing span {idx} ({getattr(span, 'name', 'unknown')}): {str(e)}", exc_info=True)
        
        if span_data_list:
            logger.info(f"[ObservabilityService] Batch creating {len(span_data_list)} spans (from {len(spans)} input spans)")
            try:
                saved_spans = self.batch_create_spans(span_data_list)
                logger.info(f"[ObservabilityService] Successfully saved {len(saved_spans)} spans for trace {trace_id}")
                
                # Verify saved spans
                if len(saved_spans) != len(span_data_list):
                    logger.warning(f"[ObservabilityService] Span count mismatch: expected {len(span_data_list)}, saved {len(saved_spans)}")
                
                # Query database to verify spans were saved
                saved_span_ids = [span.span_id for span in saved_spans]
                db_spans = self.db.query(Span).filter(Span.trace_id == trace_id).all()
                logger.info(f"[ObservabilityService] Verified: {len(db_spans)} spans found in database for trace {trace_id}")
                for db_span in db_spans:
                    logger.debug(f"[ObservabilityService]   DB span: name='{db_span.name}', span_id='{db_span.span_id}', parent_span_id='{db_span.parent_span_id}'")
            except Exception as e:
                logger.error(f"[ObservabilityService] Error batch creating spans: {str(e)}", exc_info=True)
                raise
        else:
            logger.warning(f"[ObservabilityService] No spans to save for trace {trace_id} (all spans failed preparation)")
        
        logger.info(f"[ObservabilityService] ========== Completed saving trace {trace_id} ==========")
        return trace
    
    # Span tree building
    def build_span_tree(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Build a tree structure from spans"""
        spans = self.list_spans(trace_id)
        if not spans:
            return None
        
        # Create a map of span_id -> span
        span_map = {span.span_id: span for span in spans}
        
        # Find root spans (spans without parent)
        root_spans = [span for span in spans if not span.parent_span_id or span.parent_span_id not in span_map]
        
        def build_tree(span: Span) -> Dict[str, Any]:
            """Recursively build tree for a span"""
            children = [s for s in spans if s.parent_span_id == span.span_id]
            return {
                "span": span,
                "children": [build_tree(child) for child in children],
            }
        
        # Build tree for each root span
        trees = [build_tree(root) for root in root_spans]
        
        return {
            "trace_id": trace_id,
            "trees": trees,
            "spans": spans,
        }
    
    def get_trace_tree(self, trace_id: str) -> Dict[str, Any]:
        """Get trace with span tree structure"""
        trace = self.get_trace(trace_id)
        if not trace:
            # Return empty structure instead of None to avoid 404
            return {
                "trace": None,
                "trees": [],
                "spans": [],
            }
        
        tree = self.build_span_tree(trace_id)
        if not tree:
            return {
                "trace": trace,
                "trees": [],
                "spans": [],
            }
        
        return {
            "trace": trace,
            "trees": tree["trees"],
            "spans": tree["spans"],
        }

