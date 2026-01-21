"""
Experiment comparison service
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.experiment import Experiment, ExperimentResult
from app.models.evaluator import EvaluatorVersion
from app.models.evaluator_record import EvaluatorRecord
from app.models.dataset import DatasetItem
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
            "all_evaluators": [],
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
        
        # Build all evaluators list (not just common ones)
        all_evaluators = []
        common_evaluators = []
        
        for ev_id in all_evaluator_ids:
            # Get evaluator info
            ev_version = self.db.query(EvaluatorVersion).filter(
                EvaluatorVersion.id == ev_id
            ).first()
            
            if not ev_version:
                continue
            
            # Check if present in all experiments
            present_in_all = all(
                any(
                    agg["evaluator_version_id"] == ev_id
                    for agg in exp_data["aggregate_results"]
                )
                for exp_data in experiments_data
            )
            
            evaluator_info = {
                "evaluator_version_id": ev_id,
                "name": ev_version.evaluator.name,
                "version": ev_version.version,
                "is_common": present_in_all
            }
            
            all_evaluators.append(evaluator_info)
            if present_in_all:
                common_evaluators.append(evaluator_info)
        
        # Build comparison metrics for ALL evaluators (not just common ones)
        comparison_metrics = {}
        for ev_info in all_evaluators:
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
        comparison_results["all_evaluators"] = all_evaluators
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
    
    def get_comparison_details(
        self,
        experiment_ids: List[int],
        run_ids: Optional[Dict[int, int]] = None
    ) -> Dict[str, Any]:
        """
        Get detailed comparison data aligned by dataset_item_id
        
        Returns:
            Comparison details with aligned results for each dataset item
        """
        if len(experiment_ids) < 2:
            raise ValueError("At least 2 experiments are required for comparison")
        
        # Get results for all experiments
        all_results = {}
        experiments_info = {}
        
        for exp_id in experiment_ids:
            experiment = self.experiment_service.get_experiment(exp_id)
            if not experiment:
                raise ValueError(f"Experiment {exp_id} not found")
            
            run_id = run_ids.get(exp_id) if run_ids else None
            results = self.experiment_service.get_results(exp_id, run_id=run_id)
            
            experiments_info[exp_id] = {
                "experiment_id": exp_id,
                "experiment_name": experiment.name,
                "run_id": run_id
            }
            
            # Group results by dataset_item_id
            for result in results:
                item_id = result.dataset_item_id
                if item_id not in all_results:
                    all_results[item_id] = {}
                
                # Get evaluator info
                evaluator_version = self.db.query(EvaluatorVersion).filter(
                    EvaluatorVersion.id == result.evaluator_version_id
                ).first()
                
                evaluator_name = evaluator_version.evaluator.name if evaluator_version else "Unknown"
                
                # Get token usage from evaluator records
                evaluator_record = self.db.query(EvaluatorRecord).filter(
                    EvaluatorRecord.experiment_id == exp_id,
                    EvaluatorRecord.dataset_item_id == item_id,
                    EvaluatorRecord.evaluator_version_id == result.evaluator_version_id
                ).first()
                
                input_tokens = 0
                output_tokens = 0
                if evaluator_record and evaluator_record.output_data:
                    evaluator_usage = evaluator_record.output_data.get("evaluator_usage", {})
                    if isinstance(evaluator_usage, dict):
                        input_tokens = evaluator_usage.get("input_tokens", 0) or 0
                        output_tokens = evaluator_usage.get("output_tokens", 0) or 0
                
                if exp_id not in all_results[item_id]:
                    all_results[item_id][exp_id] = []
                
                all_results[item_id][exp_id].append({
                    "experiment_id": exp_id,
                    "experiment_name": experiment.name,
                    "evaluator_version_id": result.evaluator_version_id,
                    "evaluator_name": evaluator_name,
                    "score": result.score,
                    "reason": result.reason,
                    "actual_output": result.actual_output,
                    "execution_time_ms": result.execution_time_ms,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "status": "success" if result.score is not None and result.error_message is None else "failed",
                    "error_message": result.error_message
                })
        
        # Get dataset items to extract input and reference_output
        dataset_item_ids = list(all_results.keys())
        dataset_items = {}
        if dataset_item_ids:
            items = self.db.query(DatasetItem).filter(
                DatasetItem.id.in_(dataset_item_ids)
            ).all()
            dataset_items = {item.id: item for item in items}
        
        # Build aligned comparison data
        comparison_details = []
        for item_id in sorted(dataset_item_ids):
            item = dataset_items.get(item_id)
            
            # Extract input and reference_output from dataset item
            input_text = ""
            reference_output = ""
            if item and item.data_content:
                data_content = item.data_content
                if isinstance(data_content, dict):
                    input_text = str(data_content.get("input", ""))
                    reference_output = str(
                        data_content.get("reference_output") or 
                        data_content.get("answer") or 
                        ""
                    )
                    
                    # Try turns format if simple format didn't work
                    if ("turns" in data_content) and (not input_text or not reference_output):
                        turns = data_content.get("turns", [])
                        if turns and len(turns) > 0:
                            turn = turns[0]
                            field_data_list = turn.get("field_data_list", [])
                            for field_data in field_data_list:
                                field_key = field_data.get("key", "")
                                field_name = field_data.get("name", "")
                                field_content = field_data.get("content", {})
                                field_text = field_content.get("text", "") if isinstance(field_content, dict) else str(field_content)
                                
                                if not input_text:
                                    if field_key == "input" or field_name == "input":
                                        input_text = str(field_text)
                                
                                if not reference_output:
                                    reference_field_priority = ["reference_output", "answer", "reference"]
                                    for ref_field in reference_field_priority:
                                        if (field_key == ref_field or field_name == ref_field):
                                            reference_output = str(field_text)
                                            break
            
            # Get actual_output (use first result's actual_output as they should be similar)
            actual_output = ""
            if item_id in all_results and all_results[item_id]:
                first_exp_id = list(all_results[item_id].keys())[0]
                if all_results[item_id][first_exp_id]:
                    actual_output = all_results[item_id][first_exp_id][0].get("actual_output", "") or ""
            
            # Build experiments array for this item
            experiments_data = []
            for exp_id in experiment_ids:
                exp_results = all_results[item_id].get(exp_id, [])
                if exp_results:
                    # Use first evaluator result (or combine if multiple)
                    result = exp_results[0]
                    experiments_data.append({
                        "experiment_id": exp_id,
                        "experiment_name": result["experiment_name"],
                        "response": result["actual_output"] or "",
                        "status": result["status"],
                        "execution_time_ms": result["execution_time_ms"] or 0,
                        "input_tokens": result["input_tokens"],
                        "output_tokens": result["output_tokens"],
                        "score": result["score"],
                        "evaluator_name": result["evaluator_name"],
                        "error_message": result["error_message"]
                    })
                else:
                    # No result for this experiment
                    experiments_data.append({
                        "experiment_id": exp_id,
                        "experiment_name": experiments_info[exp_id]["experiment_name"],
                        "response": "",
                        "status": "pending",
                        "execution_time_ms": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "score": None,
                        "evaluator_name": None,
                        "error_message": None
                    })
            
            comparison_details.append({
                "dataset_item_id": item_id,
                "input": input_text,
                "reference_output": reference_output,
                "actual_output": actual_output,
                "experiments": experiments_data
            })
        
        return {
            "experiments": [experiments_info[exp_id] for exp_id in experiment_ids],
            "details": comparison_details,
            "total": len(comparison_details)
        }
    
    def get_comparison_metrics(
        self,
        experiment_ids: List[int],
        run_ids: Optional[Dict[int, int]] = None
    ) -> Dict[str, Any]:
        """
        Get comparison metrics including evaluator scores and runtime metrics
        
        Returns:
            Comparison metrics with evaluator scores and runtime statistics
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if len(experiment_ids) < 2:
            raise ValueError("At least 2 experiments are required for comparison")
        
        # Get aggregate results (evaluator scores)
        comparison = self.compare_experiments(experiment_ids, run_ids)
        
        # Get runtime metrics for each experiment
        runtime_metrics = {}
        for exp_id in experiment_ids:
            try:
                experiment = self.experiment_service.get_experiment(exp_id)
                if not experiment:
                    logger.warning(f"Experiment {exp_id} not found, using default values")
                    # Create default values even if experiment doesn't exist
                    runtime_metrics[exp_id] = {
                        "experiment_id": exp_id,
                        "experiment_name": f"实验{exp_id}",
                        "total_latency_ms": 0,
                        "average_latency_ms": 0,
                        "max_latency_ms": 0,
                        "min_latency_ms": 0,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                        "result_count": 0
                    }
                    continue
                
                run_id = run_ids.get(exp_id) if run_ids else None
                
                # Get statistics and results with error handling
                try:
                    stats = self.experiment_service.get_experiment_statistics(exp_id, run_id)
                except Exception as e:
                    logger.error(f"Failed to get statistics for experiment {exp_id}: {e}", exc_info=True)
                    stats = {"token_usage": {}}
                
                # Get results for calculating latency
                try:
                    results = self.experiment_service.get_results(exp_id, run_id=run_id)
                except Exception as e:
                    logger.error(f"Failed to get results for experiment {exp_id}: {e}", exc_info=True)
                    results = []
                
                # Calculate latency metrics
                if results:
                    latencies = [r.execution_time_ms for r in results if r.execution_time_ms is not None]
                    if latencies:
                        total_latency = sum(latencies)
                        average_latency = total_latency / len(latencies)
                        max_latency = max(latencies)
                        min_latency = min(latencies)
                    else:
                        total_latency = 0
                        average_latency = 0
                        max_latency = 0
                        min_latency = 0
                else:
                    total_latency = 0
                    average_latency = 0
                    max_latency = 0
                    min_latency = 0
                    logger.warning(f"Experiment {exp_id} has no results")
                
                # Get token usage from statistics
                token_usage = stats.get("token_usage", {})
                input_tokens = token_usage.get("input_tokens", 0) or 0
                output_tokens = token_usage.get("output_tokens", 0) or 0
                total_tokens = input_tokens + output_tokens
                
                # Calculate average tokens per result (for aggregation)
                result_count = len(results) if results else 1
                avg_input_tokens = input_tokens / result_count if result_count > 0 else 0
                avg_output_tokens = output_tokens / result_count if result_count > 0 else 0
                avg_total_tokens = total_tokens / result_count if result_count > 0 else 0
                
                runtime_metrics[exp_id] = {
                    "experiment_id": exp_id,
                    "experiment_name": experiment.name,
                    "total_latency_ms": total_latency,
                    "average_latency_ms": average_latency,
                    "max_latency_ms": max_latency,
                    "min_latency_ms": min_latency,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "avg_input_tokens": avg_input_tokens,
                    "avg_output_tokens": avg_output_tokens,
                    "avg_total_tokens": avg_total_tokens,
                    "result_count": result_count
                }
            except Exception as e:
                logger.error(f"Failed to get metrics for experiment {exp_id}: {e}", exc_info=True)
                # Create default values even on error
                runtime_metrics[exp_id] = {
                    "experiment_id": exp_id,
                    "experiment_name": f"实验{exp_id}",
                    "total_latency_ms": 0,
                    "average_latency_ms": 0,
                    "max_latency_ms": 0,
                    "min_latency_ms": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "avg_input_tokens": 0,
                    "avg_output_tokens": 0,
                    "avg_total_tokens": 0,
                    "result_count": 0
                }
        
        # Build runtime metrics response with aggregation values
        # Ensure all experiment_ids are included, even if they're not in runtime_metrics
        def build_experiment_metric(exp_id, value_key, avg_key=None, max_key=None, min_key=None):
            """Helper to build experiment metric with aggregation values"""
            if exp_id in runtime_metrics:
                metric_data = runtime_metrics[exp_id]
                result = {
                    "experiment_id": exp_id,
                    "experiment_name": metric_data["experiment_name"],
                    "value": metric_data.get(value_key, 0)  # Total value
                }
                # Add aggregation values if keys are provided
                if avg_key:
                    result["avg_value"] = metric_data.get(avg_key, 0)
                if max_key:
                    result["max_value"] = metric_data.get(max_key, 0)
                if min_key:
                    result["min_value"] = metric_data.get(min_key, 0)
                return result
            else:
                # Fallback: should not happen, but handle gracefully
                return {
                    "experiment_id": exp_id,
                    "experiment_name": f"实验{exp_id}",
                    "value": 0,
                    "avg_value": 0,
                    "max_value": 0,
                    "min_value": 0
                }
        
        return {
            "evaluator_scores": {
                "common_evaluators": comparison["common_evaluators"],
                "all_evaluators": comparison.get("all_evaluators", comparison["common_evaluators"]),
                "comparison_metrics": comparison["comparison_metrics"]
            },
            "runtime_metrics": {
                "total_latency": {
                    "metric_name": "Total Latency",
                    "unit": "ms",
                    "experiments": [
                        build_experiment_metric(
                            exp_id,
                            "total_latency_ms",
                            avg_key="average_latency_ms",
                            max_key="max_latency_ms",
                            min_key="min_latency_ms"
                        )
                        for exp_id in experiment_ids
                    ]
                },
                "input_tokens": {
                    "metric_name": "Input Tokens",
                    "unit": "tokens",
                    "experiments": [
                        build_experiment_metric(
                            exp_id,
                            "input_tokens",
                            avg_key="avg_input_tokens"
                        )
                        for exp_id in experiment_ids
                    ]
                },
                "output_tokens": {
                    "metric_name": "Output Tokens",
                    "unit": "tokens",
                    "experiments": [
                        build_experiment_metric(
                            exp_id,
                            "output_tokens",
                            avg_key="avg_output_tokens"
                        )
                        for exp_id in experiment_ids
                    ]
                },
                "total_tokens": {
                    "metric_name": "Total Tokens",
                    "unit": "tokens",
                    "experiments": [
                        build_experiment_metric(
                            exp_id,
                            "total_tokens",
                            avg_key="avg_total_tokens"
                        )
                        for exp_id in experiment_ids
                    ]
                }
            }
        }

