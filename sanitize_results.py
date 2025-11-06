#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
평가 결과 파일에서 민감 정보를 마스킹하는 스크립트
"""

import json
import glob
import os
import re

def sanitize_model_ids(data):
    """
    모델 ID에서 민감한 정보를 마스킹
    """
    # Fine-tuned 모델 ID 패턴
    ft_pattern = r'ft:gpt-4\.1-nano-2025-04-14:personal:natural-fixed-1106-1205:[A-Za-z0-9]+'
    
    # 재귀적으로 모든 값에서 모델 ID 치환
    def replace_recursive(obj):
        if isinstance(obj, dict):
            return {k: replace_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_recursive(item) for item in obj]
        elif isinstance(obj, str):
            # Fine-tuned 모델 ID를 일반적인 이름으로 치환
            return re.sub(ft_pattern, 'ft:gpt-4.1-nano-2025-04-14:***:***:***', obj)
        else:
            return obj
    
    return replace_recursive(data)

def sanitize_evaluation_files():
    """
    모든 평가 결과 파일을 안전하게 변환
    """
    # 평가 결과 파일들 찾기
    result_files = glob.glob('four_way_comparison_results_*.json')
    
    for file_path in result_files:
        try:
            # 원본 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 민감 정보 마스킹
            sanitized_data = sanitize_model_ids(data)
            
            # 새 파일명으로 저장
            base_name = os.path.splitext(file_path)[0]
            new_file_path = f"{base_name}_sanitized.json"
            
            with open(new_file_path, 'w', encoding='utf-8') as f:
                json.dump(sanitized_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ {file_path} → {new_file_path}")
            
        except Exception as e:
            print(f"❌ {file_path} 처리 실패: {e}")

def create_gitignore_entries():
    """
    .gitignore에 추가할 항목 제안
    """
    gitignore_entries = [
        "",
        "# Fine-tuning 관련 민감 정보",
        "*_results_*.json",
        "!*_sanitized.json",
        "*.log",
        "fine_tuning_*",
        ""
    ]
    
    print("\n📋 .gitignore에 추가 권장 항목:")
    for entry in gitignore_entries:
        print(entry)

if __name__ == "__main__":
    print("🔒 평가 결과 파일 보안 강화")
    print("=" * 50)
    
    sanitize_evaluation_files()
    create_gitignore_entries()
    
    print("\n💡 권장사항:")
    print("1. 원본 파일들은 로컬에만 보관")
    print("2. '_sanitized.json' 파일들만 GitHub에 업로드")
    print("3. .gitignore 설정으로 실수 방지")