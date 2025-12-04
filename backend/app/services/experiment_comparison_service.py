"""
Experiment comparison service
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.experiment import Experiment, ExperimentResult
from app.models.evaluator import EvaluatorVersion
from app.services.experiment_service import ExperimentService
from app.services.experiment_aggregate_service import ExperimentAggregateService


class ExperimentComparisonService:
    """Service for comparing multiple experiments"""
    
    def __init__(self, db: Session):
        self.db = db
        self.experiment_service = ExperimentService(db)
        self.aggregate_service = ExperimentAggregateService(db)
    
    def compare_experiments(
        self,
        experiment_ids: List[int],
        run_ids: Optional[Dict[int, int]] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple experiments
        
        Args:
            experiment_ids: List of experiment IDs to compare
            run_ids: Optional dict mapping experiment_id to run_id
        
        Returns:
            Comparison results with statistics for each experiment
        """
        if len(experiment_ids) < 2:
            raise ValueError("At least 2 experiments are required for comparison")
        
        comparison_results = {
            "experiments": [],
            "common_evaluators": [],
            "comparison_metrics": {}
        }
        
        # Get experiment details and aggregate results
        experiments_data = []
        all_evaluator_ids = set()
        
        for exp_id in experiment_ids:
            experiment = self.experiment_service.get_experiment(exp_id)
            if not experiment:
                raise ValueError(f"Experiment {exp_id} not found")
            
            run_id = run_ids.get(exp_id) if run_ids else None
            
            # Get statistics
            stats = self.experiment_service.get_experiment_statistics(exp_id, run_id)
            
            # Get aggregate results
            aggregate_results = self.experiment_service.calculate_aggregate_results(
                exp_id, run_id, save=False
            )
            
            # Collect evaluator IDs
            for agg_result in aggregate_results:
                all_evaluator_ids.add(agg_result["evaluator_version_id"])
            
            experiments_data.append({
                "experiment_id": exp_id,
                "experiment_name": experiment.name,
                "run_id": run_id,
                "statistics": stats,
                "aggregate_results": aggregate_results
            })
        
        # Find common evaluators (evaluators present in all experiments)
        common_evaluators = []
        for ev_id in all_evaluator_ids:
            present_in_all = all(
                any(
                    agg["evaluator_version_id"] == ev_id
                    for agg in exp_data["aggregate_results"]
                )
                for exp_data in experiments_data
            )
            if present_in_all:
                # Get evaluator info
                ev_version = self.db.query(EvaluatorVersion).filter(
                    EvaluatorVersion.id == ev_id
                ).first()
                if ev_version:
                    common_evaluators.append({
                        "evaluator_version_id": ev_id,
                        "name": ev_version.evaluator.name,
                        "version": ev_version.version
                    })
        
        # Build comparison metrics for common evaluators
        comparison_metrics = {}
        for ev_info in common_evaluators:
            ev_id = ev_info["evaluator_version_id"]
            metrics = {
                "evaluator": ev_info,
                "experiments": []
            }
            
            for exp_data in experiments_data:
                # Find aggregate result for this evaluator
                agg_result = next(
                    (agg for agg in exp_data["aggregate_results"]
                     if agg["evaluator_version_id"] == ev_id),
                    None
                )
                
                if agg_result:
                    # Extract metrics
                    avg_score = agg_result.get("average_score")
                    total_count = agg_result.get("total_count", 0)
                    
                    # Get max, min, sum from aggregator results
                    max_score = None
                    min_score = None
                    sum_score = None
                    
                    for agg_res in agg_result.get("aggregator_results", []):
                        if agg_res["aggregator_type"] == "max":
                            max_score = agg_res["data"]["value"]
                        elif agg_res["aggregator_type"] == "min":
                            min_score = agg_res["data"]["value"]
                        elif agg_res["aggregator_type"] == "sum":
                            sum_score = agg_res["data"]["value"]
                    
                    metrics["experiments"].append({
                        "experiment_id": exp_data["experiment_id"],
                        "experiment_name": exp_data["experiment_name"],
                        "average_score": avg_score,
                        "max_score": max_score,
                        "min_score": min_score,
                        "sum_score": sum_score,
                        "total_count": total_count
                    })
            
            comparison_metrics[ev_id] = metrics
        
        comparison_results["experiments"] = experiments_data
        comparison_results["common_evaluators"] = common_evaluators
        comparison_results["comparison_metrics"] = comparison_metrics
        
        return comparison_results
    
    def get_comparison_summary(
        self,
        experiment_ids: List[int],
        run_ids: Optional[Dict[int, int]] = None
    ) -> Dict[str, Any]:
        """
        Get a summary comparison of experiments
        
        Returns:
            Summary with key metrics comparison
        """
        comparison = self.compare_experiments(experiment_ids, run_ids)
        
        summary = {
            "experiment_count": len(experiment_ids),
            "common_evaluator_count": len(comparison["common_evaluators"]),
            "experiments": []
        }
        
        for exp_data in comparison["experiments"]:
            stats = exp_data["statistics"]
            summary["experiments"].append({
                "experiment_id": exp_data["experiment_id"],
                "experiment_name": exp_data["experiment_name"],
                "total_count": stats["total_count"],
                "success_count": stats["success_count"],
                "failure_count": stats["failure_count"],
                "success_rate": (
                    (stats["success_count"] / stats["total_count"] * 100)
                    if stats["total_count"] > 0 else 0
                ),
                "average_scores": {}
            })
            
            # Add average scores for each evaluator
            for agg_result in exp_data["aggregate_results"]:
                ev_id = agg_result["evaluator_version_id"]
                avg_score = agg_result.get("average_score")
                if avg_score is not None:
                    summary["experiments"][-1]["average_scores"][str(ev_id)] = avg_score
        
        return summary

