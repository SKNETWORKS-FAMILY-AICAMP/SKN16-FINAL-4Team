import json
import io
import base64
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List, Any

class PersonalColorReportGenerator:
    def __init__(self):
        self.color_palettes = {
            "spring": {
                "name": "봄 웜톤",
                "colors": ["#FFB6C1", "#FFA07A", "#FFFF99", "#98FB98", "#87CEEB"],
                "hex_colors": ["#FFB6C1", "#FFA07A", "#FFFF99", "#98FB98", "#87CEEB"],
                "description": "생기 넘치고 화사한 당신! 밝고 따뜻한 색상이 잘 어울립니다."
            },
            "summer": {
                "name": "여름 쿨톤", 
                "colors": ["#E6E6FA", "#B0C4DE", "#FFC0CB", "#DDA0DD", "#F0F8FF"],
                "hex_colors": ["#E6E6FA", "#B0C4DE", "#FFC0CB", "#DDA0DD", "#F0F8FF"],
                "description": "시원하고 우아한 당신! 부드럽고 차가운 색상이 잘 어울립니다."
            },
            "autumn": {
                "name": "가을 웜톤",
                "colors": ["#D2691E", "#CD853F", "#DEB887", "#BC8F8F", "#F4A460"],
                "hex_colors": ["#D2691E", "#CD853F", "#DEB887", "#BC8F8F", "#F4A460"],
                "description": "깊이 있고 세련된 당신! 진하고 따뜻한 색상이 잘 어울립니다."
            },
            "winter": {
                "name": "겨울 쿨톤",
                "colors": ["#FF1493", "#4169E1", "#000000", "#FFFFFF", "#8A2BE2"],
                "hex_colors": ["#FF1493", "#4169E1", "#000000", "#FFFFFF", "#8A2BE2"],
                "description": "명확하고 강렬한 당신! 선명하고 차가운 색상이 잘 어울립니다."
            }
        }

    def generate_color_palette_image(self, season: str) -> str:
        """퍼스널컬러 팔레트 이미지 생성"""
        # matplotlib import (이 함수에서만 사용)
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        from matplotlib.patches import Rectangle
        
        # 한글 폰트 설정 (matplotlib 사용할 때만)
        korean_fonts = ['Nanum Gothic', 'Arial Unicode MS', 'AppleGothic']
        available_fonts = [f.name for f in fm.fontManager.ttflist]
        
        for font in korean_fonts:
            if font in available_fonts:
                plt.rcParams['font.family'] = font
                break
        else:
            # 한글 폰트가 없는 경우 경고 무시
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
        
        plt.rcParams['axes.unicode_minus'] = False
        
        if season not in self.color_palettes:
            season = "spring"
            
        palette_info = self.color_palettes[season]
        colors = palette_info["hex_colors"]
        
        # 이미지 생성 (400x100)
        fig, ax = plt.subplots(1, 1, figsize=(8, 2))
        ax.set_xlim(0, len(colors))
        ax.set_ylim(0, 1)
        
        # 색상 박스 그리기
        for i, color in enumerate(colors):
            rect = Rectangle((i, 0), 1, 1, facecolor=color, edgecolor='white', linewidth=2)
            ax.add_patch(rect)
            
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"{palette_info['name']} 추천 컬러팔레트", fontsize=14, pad=20)
        
        # 이미지를 base64로 인코딩
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight', dpi=150)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return image_base64

    def generate_full_report_image(self, report_data: Dict[str, Any]) -> str:
        """전체 보고서를 이미지로 생성 - 실제 모달 스타일"""
        try:
            print("이미지 생성 시작...")
            
            # 더 큰 이미지 크기 설정 (모달 스타일에 맞게)
            width, height = 900, 1400
            background_color = (255, 255, 255)
            
            # 이미지 생성
            img = Image.new('RGB', (width, height), background_color)
            draw = ImageDraw.Draw(img)
            
            print("이미지 객체 생성 완료")
            
            # 한국어 지원 폰트 설정
            try:
                # 시스템에서 한국어 폰트를 찾아서 사용
                korean_fonts = [
                    "/System/Library/Fonts/AppleSDGothicNeo.ttc",  # macOS
                    "/System/Library/Fonts/Helvetica.ttc",         # macOS 대체
                    "/System/Library/Fonts/Arial.ttf",             # 일반
                    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Linux
                    "C:/Windows/Fonts/malgun.ttf",                 # Windows
                    "C:/Windows/Fonts/arial.ttf"                   # Windows 대체
                ]
                
                font_loaded = False
                for font_path in korean_fonts:
                    if os.path.exists(font_path):
                        try:
                            large_font = ImageFont.truetype(font_path, 28)
                            medium_font = ImageFont.truetype(font_path, 20) 
                            small_font = ImageFont.truetype(font_path, 16)
                            print(f"한국어 폰트 로드 완료: {font_path}")
                            font_loaded = True
                            break
                        except Exception as e:
                            print(f"폰트 로드 시도 실패 ({font_path}): {e}")
                            continue
                
                # 시스템 폰트를 찾지 못한 경우 기본 폰트 사용
                if not font_loaded:
                    print("시스템 폰트를 찾지 못했습니다. 기본 폰트를 사용합니다.")
                    large_font = ImageFont.load_default()
                    medium_font = ImageFont.load_default() 
                    small_font = ImageFont.load_default()
                    
            except Exception as font_error:
                print(f"폰트 로드 실패: {font_error}")
                large_font = ImageFont.load_default()
                medium_font = ImageFont.load_default() 
                small_font = ImageFont.load_default()
            
            # 색상 정의 (모달과 동일한 색상)
            primary_color = (108, 92, 231)  # #6c5ce7 (보라색)
            text_color = (45, 52, 54)       # #2d3436 (진한 회색)
            secondary_color = (116, 185, 255) # #74b9ff (파란색)
            background_section = (248, 249, 250) # #f8f9fa (연한 회색)
            accent_color = (253, 203, 110)   # #fdcb6e (노란색)
            success_color = (0, 184, 148)   # #00b894 (초록색)
            
            margin_x = 40
            y_position = 40
            
            # === 헤더 섹션 ===
            # 헤더 배경 (그라데이션 효과)
            for i in range(200):
                color_ratio = i / 200
                r = int(primary_color[0] * (1 - color_ratio * 0.3))
                g = int(primary_color[1] * (1 - color_ratio * 0.3))
                b = int(primary_color[2] * (1 - color_ratio * 0.1))
                draw.rectangle([(0, i), (width, i+1)], fill=(r, g, b))
            
            # 메인 제목
            title_text = "퍼스널 컬러 진단 보고서"
            draw.text((margin_x, 30), title_text, font=large_font, fill=(255, 255, 255))
            
            # 결과 타입 (큰 글자)
            result_type = report_data.get('user_info', {}).get('result_type', '퍼스널 컬러 진단')
            draw.text((margin_x, 80), result_type, font=large_font, fill=(255, 255, 255))
            
            # 분석일과 정확도
            analysis_info = f"분석일: {report_data.get('user_info', {}).get('analysis_date', '')}"
            draw.text((margin_x, 130), analysis_info, font=small_font, fill=(255, 255, 255))
            
            confidence = report_data.get('user_info', {}).get('confidence', '85%')
            # 정확도 배지 스타일
            draw.rounded_rectangle([(margin_x, 155), (margin_x + 120, 185)], radius=15, fill=success_color)
            draw.text((margin_x + 15, 165), f"정확도: {confidence}", font=small_font, fill=(255, 255, 255))
            
            y_position = 230
            
            # === 진단 결과 섹션 ===
            # 섹션 배경
            section_height = 180
            draw.rounded_rectangle([(margin_x, y_position), (width - margin_x, y_position + section_height)], 
                                 radius=12, fill=background_section)
            # 섹션 왼쪽 보라색 라인
            draw.rectangle([(margin_x, y_position), (margin_x + 4, y_position + section_height)], fill=primary_color)
            
            # 섹션 제목
            draw.text((margin_x + 20, y_position + 15), "[진단 결과]", font=medium_font, fill=primary_color)
            
            # 설명 텍스트
            description = report_data.get('color_analysis', {}).get('description', '퍼스널 컬러 분석이 완료되었습니다.')
            
            # 텍스트 래핑 (한글 처리 개선)
            import textwrap
            wrapped_lines = textwrap.wrap(description, width=45)
            text_y = y_position + 50
            for line in wrapped_lines[:4]:  # 최대 4줄
                draw.text((margin_x + 20, text_y), line, font=small_font, fill=text_color)
                text_y += 25
            
            # 상세 분석
            detailed_analysis = report_data.get('color_analysis', {}).get('detailed_analysis', '')
            if detailed_analysis:
                wrapped_detail = textwrap.wrap(detailed_analysis, width=45)
                for line in wrapped_detail[:2]:  # 최대 2줄
                    draw.text((margin_x + 20, text_y), line, font=small_font, fill=text_color)
                    text_y += 25
            
            y_position += section_height + 20
            
            # === 컬러 팔레트 섹션 ===
            section_height = 200
            draw.rounded_rectangle([(margin_x, y_position), (width - margin_x, y_position + section_height)], 
                                 radius=12, fill=background_section)
            draw.rectangle([(margin_x, y_position), (margin_x + 4, y_position + section_height)], fill=primary_color)
            
            # 섹션 제목
            draw.text((margin_x + 20, y_position + 15), "[추천 컬러 팔레트]", font=medium_font, fill=primary_color)
            
            # 컬러 박스들 (실제 모달처럼)
            colors = report_data.get('color_recommendations', {}).get('color_codes', 
                                   ['#FFB6C1', '#FFA07A', '#FFFF99', '#98FB98', '#87CEEB'])
            
            if colors and len(colors) > 0:
                box_width = 120
                box_height = 80
                start_x = margin_x + 20
                start_y = y_position + 60
                
                for i, color in enumerate(colors[:5]):
                    x_pos = start_x + (i % 5) * (box_width + 15)
                    if i >= 5:  # 두 번째 줄
                        y_pos = start_y + box_height + 15
                    else:
                        y_pos = start_y
                    
                    try:
                        # hex color를 RGB로 변환
                        hex_color = color.replace('#', '') if color.startswith('#') else color
                        if len(hex_color) == 6:
                            rgb_color = tuple(int(hex_color[j:j+2], 16) for j in (0, 2, 4))
                            # 컬러 박스 (둥근 모서리)
                            draw.rounded_rectangle([(x_pos, y_pos), (x_pos + box_width, y_pos + box_height)], 
                                                 radius=8, fill=rgb_color)
                            # 색상 코드 표시 (박스 아래)
                            draw.text((x_pos + 5, y_pos + box_height + 5), color, font=small_font, fill=text_color)
                    except Exception as color_error:
                        print(f"색상 처리 오류 ({color}): {color_error}")
                        draw.rounded_rectangle([(x_pos, y_pos), (x_pos + box_width, y_pos + box_height)], 
                                             radius=8, fill=(200, 200, 200))
            
            y_position += section_height + 20
            
            # === 스타일 키워드 ===
            keywords = report_data.get('color_recommendations', {}).get('style_keywords', [])
            if keywords:
                keyword_y = y_position - 10
                keyword_x = margin_x + 20
                for i, keyword in enumerate(keywords[:6]):  # 최대 6개
                    # 키워드 배지
                    keyword_width = len(keyword) * 12 + 20
                    draw.rounded_rectangle([(keyword_x, keyword_y), (keyword_x + keyword_width, keyword_y + 25)], 
                                         radius=12, fill=accent_color)
                    draw.text((keyword_x + 10, keyword_y + 5), keyword, font=small_font, fill=text_color)
                    keyword_x += keyword_width + 10
                    if keyword_x > width - 150:  # 줄바꿈
                        keyword_x = margin_x + 20
                        keyword_y += 35
            
            y_position += 60
            
            # === 메이크업 추천 섹션 ===
            makeup_tips = report_data.get('color_recommendations', {}).get('makeup_tips', [])
            if makeup_tips:
                section_height = 30 + len(makeup_tips) * 30
                draw.rounded_rectangle([(margin_x, y_position), (width - margin_x, y_position + section_height)], 
                                     radius=12, fill=background_section)
                draw.rectangle([(margin_x, y_position), (margin_x + 4, y_position + section_height)], fill=primary_color)
                
                draw.text((margin_x + 20, y_position + 15), "[메이크업 추천]", font=medium_font, fill=primary_color)
                
                tip_y = y_position + 50
                for tip in makeup_tips:
                    # 팁 배경
                    draw.rounded_rectangle([(margin_x + 20, tip_y - 5), (width - margin_x - 20, tip_y + 20)], 
                                         radius=6, fill=(255, 255, 255))
                    draw.rectangle([(margin_x + 20, tip_y - 5), (margin_x + 23, tip_y + 20)], fill=secondary_color)
                    draw.text((margin_x + 35, tip_y), f"• {tip}", font=small_font, fill=text_color)
                    tip_y += 30
                
                y_position += section_height + 20
            
            # === 스타일링 가이드 섹션 ===
            styling_guide = report_data.get('styling_guide', {})
            if styling_guide:
                section_height = 220
                draw.rounded_rectangle([(margin_x, y_position), (width - margin_x, y_position + section_height)], 
                                     radius=12, fill=background_section)
                draw.rectangle([(margin_x, y_position), (margin_x + 4, y_position + section_height)], fill=primary_color)
                
                draw.text((margin_x + 20, y_position + 15), "[스타일링 가이드]", font=medium_font, fill=primary_color)
                
                guide_y = y_position + 50
                
                # 추천 색상
                draw.text((margin_x + 20, guide_y), "[추천 색상]", font=small_font, fill=success_color)
                guide_y += 25
                best_colors = styling_guide.get('best_colors', [])
                for color in best_colors[:3]:
                    draw.text((margin_x + 40, guide_y), f"• {color}", font=small_font, fill=text_color)
                    guide_y += 20
                
                guide_y += 10
                # 피해야 할 색상
                draw.text((margin_x + 20, guide_y), "[피해야 할 색상]", font=small_font, fill=(231, 76, 60))
                guide_y += 25
                avoid_colors = styling_guide.get('avoid_colors', [])
                for color in avoid_colors[:3]:
                    draw.text((margin_x + 40, guide_y), f"• {color}", font=small_font, fill=text_color)
                    guide_y += 20
                
                y_position += section_height + 20
            
            # === 푸터 ===
            footer_y = height - 60
            draw.rectangle([(0, footer_y), (width, height)], fill=background_section)
            footer_text = "AI 퍼스널 컬러 진단 시스템"
            draw.text((margin_x, footer_y + 20), footer_text, font=small_font, fill=text_color)
            
            print("이미지 내용 작성 완료")
            
            # 이미지를 바이트로 변환
            buffer = io.BytesIO()
            
            # PNG 형식으로 저장 (고품질)
            try:
                img.save(buffer, format='PNG', optimize=False, compress_level=1)
                buffer.seek(0)
                
                # 버퍼 데이터 가져오기
                image_data = buffer.getvalue()
                buffer_size = len(image_data)
                
                print(f"이미지 버퍼 크기: {buffer_size} bytes")
                
                if buffer_size < 10000:  # 10KB 미만이면 오류로 간주
                    raise Exception(f"생성된 이미지가 너무 작습니다 (크기: {buffer_size} bytes)")
                
                # 이미지 데이터 유효성 검증
                try:
                    test_buffer = io.BytesIO(image_data)
                    test_img = Image.open(test_buffer)
                    test_img.verify()
                    print("이미지 무결성 검증 완료")
                except Exception as verify_error:
                    print(f"이미지 검증 실패: {verify_error}")
                    raise Exception("생성된 이미지가 손상되었습니다")
                
                # base64 인코딩
                image_base64 = base64.b64encode(image_data).decode()
                
                print(f"이미지 생성 성공: {buffer_size} bytes, base64 길이: {len(image_base64)}")
                return image_base64
                
            except Exception as save_error:
                print(f"이미지 저장 오류: {save_error}")
                raise Exception(f"이미지 저장 실패: {str(save_error)}")
            finally:
                buffer.close()
                
        except Exception as e:
            print(f"이미지 생성 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def generate_report_data(self, survey_result: Dict[str, Any], chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """보고서 데이터 생성"""
        season = survey_result.get("result_tone", "spring")
        palette_info = self.color_palettes.get(season, self.color_palettes["spring"])
        
        # 색상 팔레트 이미지 생성
        palette_image = self.generate_color_palette_image(season)
        
        # 스타일 키워드와 메이크업 팁 파싱
        try:
            style_keywords = json.loads(survey_result.get("style_keywords", "[]"))
            makeup_tips = json.loads(survey_result.get("makeup_tips", "[]"))
            color_palette = json.loads(survey_result.get("color_palette", "[]"))
        except:
            style_keywords = ["밝은", "화사한", "생동감"]
            makeup_tips = ["코랄 계열 립", "피치 계열 블러셔"]
            color_palette = palette_info["colors"]
        
        # 대화 요약 (주요 특징 추출)
        conversation_summary = self._extract_key_features(chat_history)
        
        report_data = {
            "user_info": {
                "analysis_date": datetime.now().strftime("%Y년 %m월 %d일"),
                "result_type": palette_info["name"],
                "confidence": f"{int(survey_result.get('confidence', 0.8) * 100)}%"
            },
            "color_analysis": {
                "primary_tone": survey_result.get("result_tone", season),
                "description": survey_result.get("result_description", palette_info["description"]),
                "detailed_analysis": survey_result.get("detailed_analysis", ""),
                "key_features": conversation_summary
            },
            "color_recommendations": {
                "palette_image": palette_image,
                "color_codes": color_palette,
                "style_keywords": style_keywords,
                "makeup_tips": makeup_tips
            },
            "styling_guide": self._generate_styling_guide(season),
            "shopping_tips": self._generate_shopping_tips(season)
        }
        
        return report_data

    def _extract_key_features(self, chat_history: List[Dict[str, str]]) -> List[str]:
        """대화에서 주요 특징 추출"""
        features = []
        for msg in chat_history:
            if msg.get("role") == "user":
                text = msg.get("text", "").lower()
                
                # 피부톤 관련
                if any(word in text for word in ["노란", "황색", "따뜻한"]):
                    features.append("따뜻한 톤의 피부")
                elif any(word in text for word in ["파란", "차가운", "시원한"]):
                    features.append("차가운 톤의 피부")
                
                # 색상 선호도
                if any(word in text for word in ["밝은", "화사한", "생동감"]):
                    features.append("밝고 생동감 있는 색상 선호")
                elif any(word in text for word in ["차분한", "깊은", "세련된"]):
                    features.append("차분하고 세련된 색상 선호")
        
        return list(set(features))[:3]  # 중복 제거 후 최대 3개

    def _generate_styling_guide(self, season: str) -> Dict[str, List[str]]:
        """계절별 스타일링 가이드 생성"""
        guides = {
            "spring": {
                "best_colors": ["코랄", "피치", "아이보리", "연두", "스카이블루"],
                "avoid_colors": ["검정", "진한 회색", "네이비", "버건디"],
                "fashion_tips": [
                    "밝고 화사한 색상의 의상 선택",
                    "골드 톤 액세서리가 잘 어울림",
                    "파스텔 톤과 비비드 컬러 모두 소화 가능"
                ]
            },
            "summer": {
                "best_colors": ["라벤더", "로즈핑크", "민트", "베이비블루", "그레이"],
                "avoid_colors": ["주황", "노란색", "카키", "브라운"],
                "fashion_tips": [
                    "부드럽고 우아한 파스텔 톤 추천",
                    "실버 톤 액세서리가 잘 어울림",
                    "무채색과 파스텔의 조화로 세련된 연출"
                ]
            },
            "autumn": {
                "best_colors": ["카키", "머스타드", "브라운", "와인", "올리브"],
                "avoid_colors": ["네온", "형광색", "차가운 파스텔"],
                "fashion_tips": [
                    "깊고 따뜻한 어스톤 컬러 활용",
                    "골드, 브론즈 톤 액세서리 추천",
                    "자연스럽고 성숙한 색상 조합"
                ]
            },
            "winter": {
                "best_colors": ["블랙", "화이트", "로얄블루", "에메랄드", "퓨어레드"],
                "avoid_colors": ["베이지", "카키", "주황", "황색"],
                "fashion_tips": [
                    "명확하고 강렬한 색상으로 드라마틱한 연출",
                    "실버, 플래티넘 액세서리가 완벽",
                    "흑백 대비나 비비드 컬러로 모던한 스타일"
                ]
            }
        }
        
        return guides.get(season, guides["spring"])

    def _generate_shopping_tips(self, season: str) -> List[str]:
        """계절별 쇼핑 팁 생성"""
        tips = {
            "spring": [
                "화장품은 코랄, 피치 계열 선택",
                "옷은 밝고 화사한 색상 위주로 구매",
                "골드 톤 액세서리로 포인트 연출",
                "헤어컬러는 따뜻한 브라운 계열 추천"
            ],
            "summer": [
                "로즈, 핑크 계열 립 제품 추천",
                "파스텔 톤과 그레이 계열 의상",
                "실버 액세서리로 우아함 강조",
                "애쉬 톤 헤어컬러가 잘 어울림"
            ],
            "autumn": [
                "브라운, 오렌지 계열 메이크업",
                "어스톤, 와인 컬러 의상 선택",
                "골드, 브론즈 액세서리 활용",
                "따뜻한 브라운 계열 헤어컬러"
            ],
            "winter": [
                "레드, 베리 계열 립 제품",
                "블랙, 화이트, 비비드 컬러 의상",
                "실버, 플래티넘 액세서리",
                "쿨 톤 헤어컬러나 자연색"
            ]
        }
        
        return tips.get(season, tips["spring"])

    def generate_html_report(self, report_data: Dict[str, Any]) -> str:
        """HTML 보고서 생성"""
        html_template = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>퍼스널 컬러 진단 보고서</title>
    <style>
        body {{
            font-family: 'Noto Sans KR', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }}
        .report-container {{
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 3px solid #e9ecef;
        }}
        .result-type {{
            font-size: 2.5em;
            font-weight: bold;
            color: #6c5ce7;
            margin: 20px 0;
        }}
        .section {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 12px;
            border-left: 4px solid #6c5ce7;
        }}
        .section h2 {{
            color: #6c5ce7;
            margin-bottom: 15px;
        }}
        .color-palette {{
            text-align: center;
            margin: 20px 0;
        }}
        .color-palette img {{
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .tips-list {{
            list-style: none;
            padding: 0;
        }}
        .tips-list li {{
            background: white;
            margin: 8px 0;
            padding: 12px;
            border-radius: 8px;
            border-left: 3px solid #74b9ff;
        }}
        .confidence-score {{
            display: inline-block;
            background: #00b894;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
        }}
        .keywords {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 15px 0;
        }}
        .keyword {{
            background: #fdcb6e;
            color: #2d3436;
            padding: 6px 12px;
            border-radius: 16px;
            font-size: 0.9em;
            font-weight: 500;
        }}
        @media print {{
            body {{ background: white; }}
            .report-container {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="header">
            <h1>🎨 퍼스널 컬러 진단 보고서</h1>
            <div class="result-type">{report_data['user_info']['result_type']}</div>
            <p>분석일: {report_data['user_info']['analysis_date']}</p>
            <span class="confidence-score">정확도: {report_data['user_info']['confidence']}</span>
        </div>

        <div class="section">
            <h2>📊 진단 결과</h2>
            <p><strong>{report_data['color_analysis']['description']}</strong></p>
            <p>{report_data['color_analysis']['detailed_analysis']}</p>
            
            {f'''<div class="keywords">
                {' '.join([f'<span class="keyword">{feature}</span>' for feature in report_data['color_analysis']['key_features']])}
            </div>''' if report_data['color_analysis']['key_features'] else ''}
        </div>

        <div class="section">
            <h2>🎨 추천 컬러 팔레트</h2>
            <div class="color-palette">
                <img src="data:image/png;base64,{report_data['color_recommendations']['palette_image']}" alt="컬러 팔레트" />
            </div>
            
            <div class="keywords">
                {' '.join([f'<span class="keyword">{keyword}</span>' for keyword in report_data['color_recommendations']['style_keywords']])}
            </div>
        </div>

        <div class="section">
            <h2>💄 메이크업 추천</h2>
            <ul class="tips-list">
                {' '.join([f'<li>{tip}</li>' for tip in report_data['color_recommendations']['makeup_tips']])}
            </ul>
        </div>

        <div class="section">
            <h2>👗 스타일링 가이드</h2>
            <h3>✅ 추천 색상</h3>
            <ul class="tips-list">
                {' '.join([f'<li>{color}</li>' for color in report_data['styling_guide']['best_colors']])}
            </ul>
            
            <h3>❌ 피해야 할 색상</h3>
            <ul class="tips-list">
                {' '.join([f'<li>{color}</li>' for color in report_data['styling_guide']['avoid_colors']])}
            </ul>
            
            <h3>💡 패션 팁</h3>
            <ul class="tips-list">
                {' '.join([f'<li>{tip}</li>' for tip in report_data['styling_guide']['fashion_tips']])}
            </ul>
        </div>

        <div class="section">
            <h2>🛍️ 쇼핑 가이드</h2>
            <ul class="tips-list">
                {' '.join([f'<li>{tip}</li>' for tip in report_data['shopping_tips']])}
            </ul>
        </div>

        <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 2px solid #e9ecef; color: #6c757d;">
            <p>이 보고서는 AI 퍼스널 컬러 진단 시스템에서 생성되었습니다.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html_template