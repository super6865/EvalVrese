"""
Experiment Group service
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.models.experiment import ExperimentGroup, Experiment
from datetime import datetime


class ExperimentGroupService:
    def __init__(self, db: Session):
        self.db = db

    def create_group(self, name: str, parent_id: Optional[int] = None, description: Optional[str] = None) -> ExperimentGroup:
        """Create a new experiment group"""
        # Check if parent exists if parent_id is provided
        if parent_id is not None:
            parent = self.db.query(ExperimentGroup).filter(ExperimentGroup.id == parent_id).first()
            if not parent:
                raise ValueError(f"Parent group with id {parent_id} not found")
        
        # Check if name is unique within the same parent
        existing = self.db.query(ExperimentGroup).filter(
            ExperimentGroup.name == name,
            ExperimentGroup.parent_id == parent_id
        ).first()
        if existing:
            raise ValueError(f"Group with name '{name}' already exists in this parent")
        
        group = ExperimentGroup(
            name=name,
            parent_id=parent_id,
            description=description
        )
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        return group

    def get_group(self, group_id: int) -> Optional[ExperimentGroup]:
        """Get a group by ID"""
        return self.db.query(ExperimentGroup).filter(ExperimentGroup.id == group_id).first()
    
    def get_default_group(self) -> Optional[ExperimentGroup]:
        """Get the default group '通用实验'"""
        return self.db.query(ExperimentGroup).filter(
            ExperimentGroup.name == '通用实验',
            ExperimentGroup.parent_id.is_(None)
        ).first()

    def update_group(self, group_id: int, name: Optional[str] = None, parent_id: Optional[int] = None, description: Optional[str] = None) -> ExperimentGroup:
        """Update a group"""
        group = self.get_group(group_id)
        if not group:
            raise ValueError(f"Group with id {group_id} not found")
        
        # Check if moving to a new parent would create a cycle
        if parent_id is not None and parent_id != group.parent_id:
            if self._would_create_cycle(group_id, parent_id):
                raise ValueError("Cannot move group: would create a cycle in the tree")
            
            # Check if name is unique in the new parent
            existing = self.db.query(ExperimentGroup).filter(
                ExperimentGroup.name == (name or group.name),
                ExperimentGroup.parent_id == parent_id,
                ExperimentGroup.id != group_id
            ).first()
            if existing:
                raise ValueError(f"Group with name '{name or group.name}' already exists in the target parent")
        
        # Check if name is unique in the same parent if only name is changed
        if name is not None and name != group.name and parent_id is None:
            existing = self.db.query(ExperimentGroup).filter(
                ExperimentGroup.name == name,
                ExperimentGroup.parent_id == group.parent_id,
                ExperimentGroup.id != group_id
            ).first()
            if existing:
                raise ValueError(f"Group with name '{name}' already exists in this parent")
        
        if name is not None:
            group.name = name
        if parent_id is not None:
            group.parent_id = parent_id
        if description is not None:
            group.description = description
        
        group.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(group)
        return group

    def delete_group(self, group_id: int) -> bool:
        """Delete a group"""
        group = self.get_group(group_id)
        if not group:
            return False
        
        # Check if group has children
        children = self.db.query(ExperimentGroup).filter(ExperimentGroup.parent_id == group_id).all()
        if children:
            raise ValueError("Cannot delete group: it has child groups. Please delete or move children first")
        
        # Check if group has experiments
        experiments = self.db.query(Experiment).filter(Experiment.group_id == group_id).all()
        if experiments:
            raise ValueError("Cannot delete group: it has experiments. Please move or delete experiments first")
        
        self.db.delete(group)
        self.db.commit()
        return True

    def list_groups(self) -> List[ExperimentGroup]:
        """List all groups"""
        return self.db.query(ExperimentGroup).order_by(ExperimentGroup.name).all()

    def get_tree(self) -> List[Dict[str, Any]]:
        """Get all groups as a tree structure"""
        all_groups = self.list_groups()
        
        # Build a map of groups by ID
        group_map = {g.id: {
            "id": g.id,
            "name": g.name,
            "parent_id": g.parent_id,
            "description": g.description,
            "created_at": g.created_at.isoformat() if g.created_at else None,
            "updated_at": g.updated_at.isoformat() if g.updated_at else None,
            "children": []
        } for g in all_groups}
        
        # Build tree structure
        root_nodes = []
        for group in all_groups:
            group_dict = group_map[group.id]
            if group.parent_id is None:
                root_nodes.append(group_dict)
            else:
                parent_dict = group_map.get(group.parent_id)
                if parent_dict:
                    parent_dict["children"].append(group_dict)
        
        # Sort function: "通用实验" first, then by created_at
        def sort_groups(groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            default_group = None
            other_groups = []
            
            for group in groups:
                if group["name"] == "通用实验" and group["parent_id"] is None:
                    default_group = group
                else:
                    other_groups.append(group)
            
            # Sort other groups by created_at
            other_groups.sort(key=lambda x: x["created_at"] or "", reverse=True)
            
            # Sort children recursively
            for group in other_groups:
                if group["children"]:
                    group["children"] = sort_groups(group["children"])
            
            if default_group:
                # Sort default group's children
                if default_group["children"]:
                    default_group["children"] = sort_groups(default_group["children"])
                return [default_group] + other_groups
            else:
                return other_groups
        
        # Sort root nodes
        return sort_groups(root_nodes)

    def _would_create_cycle(self, group_id: int, new_parent_id: int) -> bool:
        """Check if moving a group to a new parent would create a cycle"""
        # If moving to None (root), no cycle possible
        if new_parent_id is None:
            return False
        
        # If new parent is the group itself, cycle
        if new_parent_id == group_id:
            return True
        
        # Check if new_parent_id is a descendant of group_id
        current_parent_id = new_parent_id
        visited = set()
        
        while current_parent_id is not None:
            if current_parent_id == group_id:
                return True
            if current_parent_id in visited:
                break  # Prevent infinite loop
            visited.add(current_parent_id)
            
            parent = self.get_group(current_parent_id)
            if not parent:
                break
            current_parent_id = parent.parent_id
        
        return False

    def get_group_with_experiments(self, group_id: Optional[int] = None) -> Dict[str, Any]:
        """Get a group and its direct experiments count"""
        if group_id is None:
            # Return root level info
            experiments_count = self.db.query(Experiment).filter(Experiment.group_id.is_(None)).count()
            return {
                "id": None,
                "name": "全部实验",
                "experiments_count": experiments_count
            }
        
        group = self.get_group(group_id)
        if not group:
            return None
        
        # Count experiments in this group and all descendant groups
        experiments_count = self.db.query(Experiment).filter(Experiment.group_id == group_id).count()
        
        return {
            "id": group.id,
            "name": group.name,
            "parent_id": group.parent_id,
            "description": group.description,
            "experiments_count": experiments_count,
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "updated_at": group.updated_at.isoformat() if group.updated_at else None,
        }

