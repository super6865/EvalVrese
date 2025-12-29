#!/usr/bin/env python3
"""
修复 message_list 数据格式问题

将数据库中错误存储为字符串的 message_list 转换为正确的数组格式
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.evaluator import Evaluator, EvaluatorVersion
import json
from typing import Dict, Any, Optional

def convert_string_to_message_list(text: str) -> list:
    """
    将字符串转换为 message_list 数组格式
    
    Args:
        text: 字符串内容
        
    Returns:
        格式化的 message_list 数组
    """
    if not text or not isinstance(text, str):
        return []
    
    # 创建标准的 message_list 格式
    return [
        {
            "role": "system",
            "content": {
                "text": text,
                "content_type": "Text"
            }
        }
    ]

def fix_evaluator_prompt_content(evaluator: Evaluator, db: SessionLocal) -> bool:
    """
    修复单个 evaluator 的 prompt_content.message_list
    
    Returns:
        True if fixed, False otherwise
    """
    if not evaluator.prompt_content:
        return False
    
    if not isinstance(evaluator.prompt_content, dict):
        return False
    
    message_list = evaluator.prompt_content.get("message_list")
    needs_fix = False
    fixed_content = None
    
    # 如果 message_list 是字符串，需要转换
    if isinstance(message_list, str):
        print(f"  Found string message_list in evaluator {evaluator.id}, converting...")
        fixed_content = evaluator.prompt_content.copy()
        fixed_content["message_list"] = convert_string_to_message_list(message_list)
        needs_fix = True
    # 如果 message_list 已经是数组，检查格式是否正确
    elif isinstance(message_list, list):
        # 检查是否为空数组
        if len(message_list) == 0:
            return False
        # 检查第一个元素是否是字符串（错误格式）
        if len(message_list) > 0 and isinstance(message_list[0], str):
            print(f"  Found array with string elements in evaluator {evaluator.id}, converting...")
            fixed_content = evaluator.prompt_content.copy()
            fixed_content["message_list"] = convert_string_to_message_list(message_list[0])
            needs_fix = True
    
    if needs_fix and fixed_content:
        # Use raw SQL update to ensure JSON is properly serialized
        from sqlalchemy import text
        import json
        db.execute(
            text('UPDATE evaluators SET prompt_content = :content WHERE id = :id'),
            {'content': json.dumps(fixed_content, ensure_ascii=False), 'id': evaluator.id}
        )
        return True
    
    return False

def fix_version_prompt_content(version: EvaluatorVersion, db: SessionLocal) -> bool:
    """
    修复单个 version 的 prompt_content.message_list
    
    Returns:
        True if fixed, False otherwise
    """
    if not version.prompt_content:
        return False
    
    if not isinstance(version.prompt_content, dict):
        return False
    
    message_list = version.prompt_content.get("message_list")
    needs_fix = False
    fixed_content = None
    
    # 如果 message_list 是字符串，需要转换
    if isinstance(message_list, str):
        print(f"  Found string message_list in version {version.id}, converting...")
        fixed_content = version.prompt_content.copy()
        fixed_content["message_list"] = convert_string_to_message_list(message_list)
        needs_fix = True
    # 如果 message_list 已经是数组，检查格式是否正确
    elif isinstance(message_list, list):
        # 检查是否为空数组
        if len(message_list) == 0:
            return False
        # 检查第一个元素是否是字符串（错误格式）
        if len(message_list) > 0 and isinstance(message_list[0], str):
            print(f"  Found array with string elements in version {version.id}, converting...")
            fixed_content = version.prompt_content.copy()
            fixed_content["message_list"] = convert_string_to_message_list(message_list[0])
            needs_fix = True
    
    if needs_fix and fixed_content:
        # Use raw SQL update to ensure JSON is properly serialized
        from sqlalchemy import text
        import json
        db.execute(
            text('UPDATE evaluator_versions SET prompt_content = :content WHERE id = :id'),
            {'content': json.dumps(fixed_content, ensure_ascii=False), 'id': version.id}
        )
        return True
    
    return False

def main():
    """主函数"""
    db = SessionLocal()
    fixed_count = 0
    
    try:
        print("开始修复 message_list 数据格式...")
        print("=" * 60)
        
        # 修复所有 evaluator
        evaluators = db.query(Evaluator).filter(
            Evaluator.evaluator_type == "prompt"
        ).all()
        
        print(f"\n检查 {len(evaluators)} 个 prompt evaluator...")
        
        for evaluator in evaluators:
            if fix_evaluator_prompt_content(evaluator, db):
                fixed_count += 1
                print(f"  ✓ Fixed evaluator {evaluator.id}: {evaluator.name}")
        
        # 修复所有 version
        versions = db.query(EvaluatorVersion).join(
            Evaluator
        ).filter(
            Evaluator.evaluator_type == "prompt"
        ).all()
        
        print(f"\n检查 {len(versions)} 个 evaluator version...")
        
        for version in versions:
            if fix_version_prompt_content(version, db):
                fixed_count += 1
                print(f"  ✓ Fixed version {version.id} (evaluator {version.evaluator_id})")
        
        # 提交更改
        if fixed_count > 0:
            print(f"\n提交 {fixed_count} 个修复...")
            db.commit()
            print("✓ 修复完成！")
        else:
            print("\n没有需要修复的数据。")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()

