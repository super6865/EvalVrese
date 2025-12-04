"""
Experiment result export service
"""
import csv
import io
import os
import tempfile
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.experiment import (
    Experiment, ExperimentResult, ExperimentResultExport, ExportStatus
)
from app.models.dataset import DatasetItem
from app.models.evaluator import EvaluatorVersion
from app.services.experiment_service import ExperimentService


class ExperimentExportService:
    """Service for exporting experiment results to CSV"""
    
    def __init__(self, db: Session):
        self.db = db
        self.experiment_service = ExperimentService(db)
    
    def create_export_task(
        self,
        experiment_id: int,
        created_by: Optional[str] = None
    ) -> ExperimentResultExport:
        """Create a new export task"""
        experiment = self.experiment_service.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        export = ExperimentResultExport(
            experiment_id=experiment_id,
            status=ExportStatus.PENDING.value,  # Use enum value instead of enum object
            created_by=created_by,
        )
        self.db.add(export)
        self.db.commit()
        self.db.refresh(export)
        return export
    
    def get_export(self, export_id: int) -> Optional[ExperimentResultExport]:
        """Get export task by ID"""
        return self.db.query(ExperimentResultExport).filter(
            ExperimentResultExport.id == export_id
        ).first()
    
    def list_exports(
        self,
        experiment_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ExperimentResultExport]:
        """List export tasks for an experiment"""
        return self.db.query(ExperimentResultExport).filter(
            ExperimentResultExport.experiment_id == experiment_id
        ).order_by(ExperimentResultExport.created_at.desc()).offset(skip).limit(limit).all()
    
    def update_export_status(
        self,
        export_id: int,
        status: ExportStatus,
        file_url: Optional[str] = None,
        file_name: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """Update export task status"""
        export = self.get_export(export_id)
        if not export:
            raise ValueError(f"Export {export_id} not found")
        
        # Use enum value instead of enum object to ensure correct database storage
        from app.models.experiment import ExportStatus
        status_value = status.value if isinstance(status, ExportStatus) else status
        export.status = status_value
        if file_url:
            export.file_url = file_url
        if file_name:
            export.file_name = file_name
        if error_message:
            export.error_message = error_message
        
        if status == ExportStatus.RUNNING and not export.started_at:
            export.started_at = datetime.utcnow()
        if status in [ExportStatus.SUCCESS, ExportStatus.FAILED]:
            export.completed_at = datetime.utcnow()
        
        export.updated_at = datetime.utcnow()
        self.db.commit()
    
    def export_experiment_results_csv(
        self,
        experiment_id: int,
        export_id: int,
        run_id: Optional[int] = None
    ) -> str:
        """
        Export experiment results to CSV file
        
        Returns:
            Path to the exported CSV file
        """
        experiment = self.experiment_service.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # Update status to running
        self.update_export_status(export_id, ExportStatus.RUNNING)
        
        try:
            # Get all results
            results = self.experiment_service.get_results(experiment_id, run_id=run_id)
            
            if not results:
                raise ValueError("No results to export")
            
            # Get evaluator versions info
            evaluator_version_ids = set(r.evaluator_version_id for r in results)
            evaluator_versions = {}
            for ev_id in evaluator_version_ids:
                ev = self.db.query(EvaluatorVersion).filter(
                    EvaluatorVersion.id == ev_id
                ).first()
                if ev:
                    evaluator_versions[ev_id] = ev
            
            # Get dataset items
            dataset_item_ids = set(r.dataset_item_id for r in results)
            dataset_items = {}
            for item_id in dataset_item_ids:
                item = self.db.query(DatasetItem).filter(
                    DatasetItem.id == item_id
                ).first()
                if item:
                    dataset_items[item_id] = item
            
            # Build CSV data
            csv_data = self._build_csv_data(
                results,
                evaluator_versions,
                dataset_items
            )
            
            # Create CSV file
            file_path = self._create_csv_file(experiment, export_id, csv_data)
            
            # Update status to success
            file_name = os.path.basename(file_path)
            self.update_export_status(
                export_id,
                ExportStatus.SUCCESS,
                file_url=file_path,  # In production, this would be a URL to object storage
                file_name=file_name
            )
            
            return file_path
            
        except Exception as e:
            # Update status to failed
            self.update_export_status(
                export_id,
                ExportStatus.FAILED,
                error_message=str(e)
            )
            raise
    
    def _build_csv_data(
        self,
        results: List[ExperimentResult],
        evaluator_versions: Dict[int, EvaluatorVersion],
        dataset_items: Dict[int, DatasetItem]
    ) -> List[List[str]]:
        """Build CSV data from results"""
        # Group results by dataset_item_id
        results_by_item = {}
        for result in results:
            item_id = result.dataset_item_id
            if item_id not in results_by_item:
                results_by_item[item_id] = {}
            evaluator_id = result.evaluator_version_id
            if evaluator_id not in results_by_item[item_id]:
                results_by_item[item_id][evaluator_id] = []
            results_by_item[item_id][evaluator_id].append(result)
        
        # Build header
        evaluator_ids = sorted(set(r.evaluator_version_id for r in results))
        header = ["ID", "状态", "数据集项ID"]
        
        # Add dataset fields (simplified - in production, would get from schema)
        header.append("输入")
        header.append("参考输出")
        
        # Add actual output
        header.append("实际输出")
        
        # Add evaluator columns
        for ev_id in evaluator_ids:
            ev = evaluator_versions.get(ev_id)
            ev_name = ev.evaluator.name if ev else f"评估器{ev_id}"
            ev_version = ev.version if ev else "unknown"
            header.append(f"{ev_name}<{ev_version}>_score")
            header.append(f"{ev_name}<{ev_version}>_reason")
        
        # Build rows
        rows = []
        for item_id, evaluator_results in results_by_item.items():
            dataset_item = dataset_items.get(item_id)
            
            # Get input and reference_output from dataset item
            input_data = ""
            reference_output = ""
            if dataset_item and dataset_item.data_content:
                data_content = dataset_item.data_content
                # Extract input
                input_data = str(data_content.get("input", ""))
                
                # Extract reference_output: 优先使用 reference_output，如果不存在则使用 answer（排除 output）
                # Try simple format first
                reference_output = str(
                    data_content.get("reference_output") or 
                    data_content.get("answer") or 
                    ""
                )
                
                # If not found in simple format, try to extract from turns format
                if not reference_output and isinstance(data_content, dict) and "turns" in data_content:
                    turns = data_content.get("turns", [])
                    if turns and len(turns) > 0:
                        turn = turns[0]
                        field_data_list = turn.get("field_data_list", [])
                        # 按优先级顺序匹配参考输出字段（排除 output）
                        reference_field_priority = ["reference_output", "answer", "reference"]
                        for field_data in field_data_list:
                            field_key = field_data.get("key", "")
                            field_name = field_data.get("name", "")
                            field_content = field_data.get("content", {})
                            field_text = field_content.get("text", "") if isinstance(field_content, dict) else str(field_content)
                            
                            for ref_field in reference_field_priority:
                                if (field_key == ref_field or field_name == ref_field or 
                                    field_key.lower() == ref_field.lower()):
                                    reference_output = str(field_text)
                                    break
                            if reference_output:
                                break
            
            # Get actual output (from first result)
            actual_output = ""
            for ev_id in evaluator_ids:
                ev_results = evaluator_results.get(ev_id, [])
                if ev_results and ev_results[0].actual_output:
                    actual_output = ev_results[0].actual_output
                    break
            
            # Build row
            row = [
                str(item_id),
                "Success" if any(r.score is not None for r in results if r.dataset_item_id == item_id) else "Failed",
                str(item_id),
                input_data,
                reference_output,
                actual_output,
            ]
            
            # Add evaluator scores and reasons
            for ev_id in evaluator_ids:
                ev_results = evaluator_results.get(ev_id, [])
                if ev_results:
                    result = ev_results[0]  # Take first result
                    score = str(result.score) if result.score is not None else ""
                    reason = result.reason or ""
                else:
                    score = ""
                    reason = ""
                row.append(score)
                row.append(reason)
            
            rows.append(row)
        
        return [header] + rows
    
    def _create_csv_file(
        self,
        experiment: Experiment,
        export_id: int,
        csv_data: List[List[str]]
    ) -> str:
        """Create CSV file from data"""
        # Generate file name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{experiment.name}_实验报告_{export_id}_{timestamp}.csv"
        
        # Create exports directory in uploads folder (similar to dataset uploads)
        # Use absolute path to ensure file is accessible
        from pathlib import Path
        base_dir = Path(__file__).parent.parent.parent  # Go up to project root
        exports_dir = base_dir / "uploads" / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = exports_dir / file_name
        absolute_path = str(file_path.absolute())
        
        # Write CSV file with UTF-8 BOM (for Excel compatibility)
        with open(absolute_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            for row in csv_data:
                writer.writerow(row)
        
        return absolute_path

