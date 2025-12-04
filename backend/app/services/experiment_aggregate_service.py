"""
Experiment aggregate results calculation service
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.experiment import ExperimentResult, ExperimentAggregateResult
from app.models.evaluator import EvaluatorVersion
import statistics


class AggregatorType:
    AVERAGE = "average"
    SUM = "sum"
    MAX = "max"
    MIN = "min"
    DISTRIBUTION = "distribution"


class AggregatorResult:
    def __init__(self, aggregator_type: str, data: Any):
        self.aggregator_type = aggregator_type
        self.data = data


class StatAggregator:
    """Unified aggregator for statistical operations (average, sum, max, min)"""
    
    @staticmethod
    def aggregate(scores: List[float], aggregator_type: str) -> AggregatorResult:
        """Aggregate scores using the specified operation"""
        if not scores:
            default_value = 0.0 if aggregator_type != AggregatorType.SUM else 0.0
            return AggregatorResult(aggregator_type, {"value": default_value, "count": 0})
        
        if aggregator_type == AggregatorType.AVERAGE:
            value = statistics.mean(scores)
        elif aggregator_type == AggregatorType.SUM:
            value = sum(scores)
        elif aggregator_type == AggregatorType.MAX:
            value = max(scores)
        elif aggregator_type == AggregatorType.MIN:
            value = min(scores)
        else:
            raise ValueError(f"Unsupported aggregator type: {aggregator_type}")
        
        return AggregatorResult(aggregator_type, {"value": value, "count": len(scores)})


# Backward compatibility aliases
class AverageAggregator:
    @staticmethod
    def aggregate(scores: List[float]) -> AggregatorResult:
        return StatAggregator.aggregate(scores, AggregatorType.AVERAGE)


class SumAggregator:
    @staticmethod
    def aggregate(scores: List[float]) -> AggregatorResult:
        return StatAggregator.aggregate(scores, AggregatorType.SUM)


class MaxAggregator:
    @staticmethod
    def aggregate(scores: List[float]) -> AggregatorResult:
        return StatAggregator.aggregate(scores, AggregatorType.MAX)


class MinAggregator:
    @staticmethod
    def aggregate(scores: List[float]) -> AggregatorResult:
        return StatAggregator.aggregate(scores, AggregatorType.MIN)


class DistributionAggregator:
    """Calculate score distribution with fixed three bins: 0-0.50, 0.51-0.80, 0.81-1.00"""
    
    @staticmethod
    def aggregate(scores: List[float]) -> AggregatorResult:
        if not scores:
            return AggregatorResult(
                AggregatorType.DISTRIBUTION,
                {"distribution_items": [], "bins": 3}
            )
        
        # Fixed three bins: 0-0.50, 0.51-0.80, 0.81-1.00
        bin_counts = [0, 0, 0]  # [0-0.50, 0.51-0.80, 0.81-1.00]
        total = len(scores)
        
        for score in scores:
            if score is None:
                continue
            # Clamp score to [0, 1] range
            score = max(0.0, min(1.0, float(score)))
            
            if score <= 0.50:
                bin_counts[0] += 1
            elif score <= 0.80:
                bin_counts[1] += 1
            else:  # score >= 0.81
                bin_counts[2] += 1
        
        # Build distribution items with fixed ranges
        distribution_items = [
            {
                "score_range": "0.00-0.50",
                "count": bin_counts[0],
                "percentage": round((bin_counts[0] / total * 100) if total > 0 else 0.0, 2)
            },
            {
                "score_range": "0.51-0.80",
                "count": bin_counts[1],
                "percentage": round((bin_counts[1] / total * 100) if total > 0 else 0.0, 2)
            },
            {
                "score_range": "0.81-1.00",
                "count": bin_counts[2],
                "percentage": round((bin_counts[2] / total * 100) if total > 0 else 0.0, 2)
            }
        ]
        
        return AggregatorResult(
            AggregatorType.DISTRIBUTION,
            {
                "distribution_items": distribution_items,
                "bins": 3
            }
        )


class ExperimentAggregateService:
    """Service for calculating experiment aggregate results"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_evaluator_aggregate(
        self,
        experiment_id: int,
        evaluator_version_id: int,
        run_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate aggregate results for a specific evaluator in an experiment
        
        Returns:
            Dict containing aggregate results with all aggregator types
        """
        # Get all results for this evaluator
        query = self.db.query(ExperimentResult).filter(
            ExperimentResult.experiment_id == experiment_id,
            ExperimentResult.evaluator_version_id == evaluator_version_id,
            ExperimentResult.score.isnot(None)  # Only include results with scores
        )
        
        if run_id:
            query = query.filter(ExperimentResult.run_id == run_id)
        
        results = query.all()
        scores = [r.score for r in results if r.score is not None]
        
        if not scores:
            return {
                "evaluator_version_id": evaluator_version_id,
                "aggregator_results": [],
                "average_score": None,
                "total_count": 0
            }
        
        # Calculate all aggregator results
        aggregator_results = []
        stat_types = [AggregatorType.AVERAGE, AggregatorType.SUM, AggregatorType.MAX, AggregatorType.MIN]
        
        for agg_type in stat_types:
            result = StatAggregator.aggregate(scores, agg_type)
            aggregator_results.append({
                "aggregator_type": result.aggregator_type,
                "data": result.data
            })
        
        dist_result = DistributionAggregator.aggregate(scores)
        aggregator_results.append({
            "aggregator_type": dist_result.aggregator_type,
            "data": dist_result.data
        })
        
        avg_result = StatAggregator.aggregate(scores, AggregatorType.AVERAGE)
        
        return {
            "evaluator_version_id": evaluator_version_id,
            "aggregator_results": aggregator_results,
            "average_score": avg_result.data["value"],
            "total_count": len(scores)
        }
    
    def calculate_all_evaluator_aggregates(
        self,
        experiment_id: int,
        run_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate aggregate results for all evaluators in an experiment
        
        Returns:
            List of aggregate results for each evaluator
        """
        # Get unique evaluator version IDs from results
        query = self.db.query(ExperimentResult.evaluator_version_id).filter(
            ExperimentResult.experiment_id == experiment_id,
            ExperimentResult.score.isnot(None)
        ).distinct()
        
        if run_id:
            query = query.filter(ExperimentResult.run_id == run_id)
        
        evaluator_version_ids = [row[0] for row in query.all()]
        
        results = []
        for evaluator_version_id in evaluator_version_ids:
            aggregate = self.calculate_evaluator_aggregate(
                experiment_id,
                evaluator_version_id,
                run_id
            )
            
            # Get evaluator version info
            evaluator_version = self.db.query(EvaluatorVersion).filter(
                EvaluatorVersion.id == evaluator_version_id
            ).first()
            
            if evaluator_version:
                aggregate["name"] = evaluator_version.evaluator.name
                aggregate["version"] = evaluator_version.version
            
            results.append(aggregate)
        
        return results
    
    def save_aggregate_results(
        self,
        experiment_id: int,
        evaluator_version_id: int,
        aggregate_data: Dict[str, Any]
    ) -> ExperimentAggregateResult:
        """Save aggregate results to database"""
        # Check if exists
        existing = self.db.query(ExperimentAggregateResult).filter(
            ExperimentAggregateResult.experiment_id == experiment_id,
            ExperimentAggregateResult.evaluator_version_id == evaluator_version_id
        ).first()
        
        if existing:
            existing.aggregate_data = aggregate_data
            existing.average_score = aggregate_data.get("average_score")
            existing.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            result = ExperimentAggregateResult(
                experiment_id=experiment_id,
                evaluator_version_id=evaluator_version_id,
                aggregate_data=aggregate_data,
                average_score=aggregate_data.get("average_score")
            )
            self.db.add(result)
            self.db.commit()
            self.db.refresh(result)
            return result

