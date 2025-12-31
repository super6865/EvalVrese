#!/usr/bin/env python3
"""
脚本：将 group_id 为 NULL 的实验迁移到"通用实验"分组

使用方法：
    cd backend
    python scripts/migrate_experiments_to_default_group.py
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.experiment import ExperimentGroup, Experiment


def migrate_experiments_to_default_group():
    """将 group_id 为 NULL 的实验迁移到"通用实验"分组"""
    db = SessionLocal()
    try:
        # 查找或创建"通用实验"分组
        default_group = db.query(ExperimentGroup).filter(
            ExperimentGroup.name == '通用实验',
            ExperimentGroup.parent_id.is_(None)
        ).first()
        
        if not default_group:
            print("创建'通用实验'分组...")
            default_group = ExperimentGroup(
                name='通用实验',
                parent_id=None,
                description='默认实验分组，用于存放未分组的实验'
            )
            db.add(default_group)
            db.commit()
            db.refresh(default_group)
            print(f"✓ 已创建'通用实验'分组 (ID: {default_group.id})")
        else:
            print(f"✓ 找到'通用实验'分组 (ID: {default_group.id})")
        
        # 查找所有 group_id 为 NULL 的实验
        experiments_without_group = db.query(Experiment).filter(
            Experiment.group_id.is_(None)
        ).all()
        
        if not experiments_without_group:
            print("✓ 所有实验都已绑定到分组，无需迁移")
            return
        
        print(f"\n找到 {len(experiments_without_group)} 个未分组的实验，开始迁移...")
        
        # 更新这些实验的 group_id
        updated_count = 0
        for experiment in experiments_without_group:
            experiment.group_id = default_group.id
            updated_count += 1
            print(f"  - 迁移实验: {experiment.name} (ID: {experiment.id})")
        
        db.commit()
        print(f"\n✓ 成功将 {updated_count} 个实验迁移到'通用实验'分组")
        
    except Exception as e:
        db.rollback()
        print(f"✗ 迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    print("=" * 60)
    print("实验分组迁移脚本")
    print("=" * 60)
    migrate_experiments_to_default_group()
    print("=" * 60)
    print("迁移完成！")
    print("=" * 60)

