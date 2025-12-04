"""
Experiment result service - handles experiment result queries and statistics
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.experiment import Experiment, ExperimentResult
from app.services.experiment_aggregate_service import ExperimentAggregateService


class ExperimentResultService:
    """Service for querying and processing experiment results"""
    
    def __init__(self, db: Session):
        self.db = db
        self.aggregate_service = ExperimentAggregateService(db)
    
    def get_results(self, experiment_id: int, run_id: Optional[int] = None) -> List[ExperimentResult]:
        """Get experiment results"""
        query = self.db.query(ExperimentResult).filter(
            ExperimentResult.experiment_id == experiment_id
        )
        if run_id:
            query = query.filter(ExperimentResult.run_id == run_id)
        return query.all()
    
    def calculate_aggregate_results(
        self,
        experiment_id: int,
        run_id: Optional[int] = None,
        save: bool = True
    ) -> List[Dict[str, Any]]:
        """Calculate and optionally save aggregate results"""
        results = self.aggregate_service.calculate_all_evaluator_aggregates(
            experiment_id,
            run_id
        )
        
        if save:
            for result in results:
                evaluator_version_id = result["evaluator_version_id"]
                self.aggregate_service.save_aggregate_results(
                    experiment_id,
                    evaluator_version_id,
                    result
                )
        
        return results
    
    def get_experiment_statistics(
        self,
        experiment_id: int,
        run_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get experiment statistics"""
        from app.models.evaluator_record import EvaluatorRecord
        import json
        import logging
        
        logger = logging.getLogger(__name__)
        
        experiment = self.db.query(Experiment).filter(Experiment.id == experiment_id).first()
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        results = self.get_results(experiment_id, run_id)
        
        total_count = len(results)
        success_count = len([r for r in results if r.score is not None])
        failure_count = total_count - success_count
        pending_count = len([r for r in results if r.score is None and not r.error_message])
        
        aggregate_results = self.calculate_aggregate_results(experiment_id, run_id, save=False)
        
        evaluator_records_query = self.db.query(EvaluatorRecord).filter(
            EvaluatorRecord.experiment_id == experiment_id
        )
        if run_id:
            evaluator_records_query = evaluator_records_query.filter(
                EvaluatorRecord.experiment_run_id == run_id
            )
        evaluator_records = evaluator_records_query.all()
        
        total_input_tokens = 0
        total_output_tokens = 0
        
        for record in evaluator_records:
            output_data = record.output_data or {}
            evaluator_usage = output_data.get("evaluator_usage", {})
            
            if isinstance(evaluator_usage, dict):
                input_tokens = evaluator_usage.get("input_tokens", 0)
                output_tokens = evaluator_usage.get("output_tokens", 0)
                
                if isinstance(input_tokens, (int, float)) and input_tokens:
                    total_input_tokens += int(input_tokens)
                if isinstance(output_tokens, (int, float)) and output_tokens:
                    total_output_tokens += int(output_tokens)
        
        token_usage = {
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens
        }
        
        return {
            "experiment_id": experiment_id,
            "total_count": total_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "pending_count": pending_count,
            "evaluator_aggregate_results": aggregate_results,
            "token_usage": token_usage
        }

