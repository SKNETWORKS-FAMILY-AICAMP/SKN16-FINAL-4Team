#!/usr/bin/env python3
"""
불변 지식 파일 진단 스크립트

PDF 텍스트 추출, 파일 상태, 설정 확인
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag_service.core.config import IMMUTABLE_BACKUP_DIR, IMMUTABLE_KNOWLEDGE_FILES

print("="*70)
print("📋 불변 지식 파일 진단")
print("="*70)

print(f"\n✅ 설정된 백업 디렉토리: {IMMUTABLE_BACKUP_DIR}")
print(f"✅ 설정된 지식 파일: {IMMUTABLE_KNOWLEDGE_FILES}")

print(f"\n📁 백업 디렉토리 존재 여부: {IMMUTABLE_BACKUP_DIR.exists()}")

if IMMUTABLE_BACKUP_DIR.exists():
    files = list(IMMUTABLE_BACKUP_DIR.glob("*"))
    print(f"📂 백업 디렉토리 파일 목록 ({len(files)}개):")
    for f in files:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"   - {f.name} ({size_mb:.2f}MB)")
        
        # Try PDF extraction
        if f.suffix.lower() == '.pdf':
            print(f"\n      🔍 PDF 텍스트 추출 시도...")
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(str(f))
                total_text = ""
                for page_num, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text() or ""
                        total_text += text
                        if text.strip():
                            print(f"         ✅ 페이지 {page_num + 1}: {len(text)} 문자")
                    except Exception as e:
                        print(f"         ⚠️  페이지 {page_num + 1} 추출 실패: {e}")
                
                if total_text.strip():
                    print(f"\n      ✅ 총 추출 텍스트: {len(total_text)} 문자")
                    print(f"      📝 첫 100자:\n{total_text[:100]}...")
                else:
                    print(f"\n      ⚠️  추출된 텍스트가 없습니다 (이미지 기반 PDF일 수 있음)")
            except ImportError:
                print(f"      ⚠️  PyPDF2 미설치 (pip install PyPDF2 필요)")
            except Exception as e:
                print(f"      ❌ PDF 추출 실패: {e}")

print("\n" + "="*70)
print("✅ 진단 완료")
print("="*70)
