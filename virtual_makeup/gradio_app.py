"""
Gradio UI로 가상 메이크업 테스트
"""

import gradio as gr
from PIL import Image
import os
import sys
import json
from openai import OpenAI
from dotenv import load_dotenv

# 현재 폴더를 path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# .env 로드
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from demo_responses import MAKEUP_RESPONSES, get_makeup_response, apply_modification, MODIFICATION_EXAMPLES, DEFAULT_MAKEUP
from demo_responses import prepare_makeup_response
from makeup_applier_cv import MakeupApplierCV

# OpenAI 클라이언트
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 전역 변수
applier = None
current_makeup = None


def load_model():
    """모델 로드"""
    global applier
    if applier is None:
        applier = MakeupApplierCV()
    return "✅ 모델 로딩 완료!"


def apply_initial_makeup(image, personal_color, makeup_response_override=None):
    """
    퍼스널컬러에 맞는 초기 메이크업 적용.
    makeup_response_override: RAG/모델에서 받은 커스텀 메이크업 응답(dict)이면 이를 우선 사용.
    """
    global current_makeup, applier

    if image is None:
        return None, "❌ 이미지를 업로드해주세요"

    if applier is None:
        load_model()

    # 퍼스널컬러/외부 응답 기반 메이크업 설정
    current_makeup = prepare_makeup_response(personal_color, makeup_response_override)

    # 임시 파일로 저장
    temp_input = "/tmp/temp_input.jpg"
    temp_output = "/tmp/temp_output.jpg"

    if isinstance(image, str):
        img = Image.open(image)
    else:
        img = Image.fromarray(image)

    img.save(temp_input)

    # 메이크업 적용
    result = applier.apply_makeup(
        image_path=temp_input,
        makeup_response=current_makeup,
        output_path=temp_output
    )

    # 메이크업 정보 텍스트
    makeup = current_makeup['makeup']

    makeup_info = f"**퍼스널컬러:** {current_makeup['personal_color']}\n\n"

    if 'skin_base' in makeup:
        makeup_info += f"**피부 베이스:** {makeup['skin_base']['type']} ({makeup['skin_base']['intensity']:.0%})\n\n"

    if 'lip' in makeup:
        makeup_info += f"**립:** {makeup['lip']['color']} ({makeup['lip']['intensity']:.0%})\n\n"

    if 'blush' in makeup:
        makeup_info += f"**블러셔:** {makeup['blush']['color']} ({makeup['blush']['intensity']:.0%})\n\n"

    if 'eyeliner' in makeup:
        makeup_info += f"**아이라이너:** {makeup['eyeliner']['color']} (두께: {makeup['eyeliner']['thickness']}, 각도: {makeup['eyeliner']['angle']}°)\n\n"

    if 'eyebrow' in makeup:
        makeup_info += f"**눈썹:** {makeup['eyebrow']['color']} ({makeup['eyebrow']['intensity']:.0%})\n\n"

    makeup_info += f"**추천 이유:** {current_makeup['recommendation_reason']}"

    return result, makeup_info


def parse_modification_with_gpt(user_input: str) -> dict:
    """GPT로 사용자 입력을 메이크업 수정 명령으로 파싱"""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """너는 메이크업 수정 요청을 JSON으로 파싱하는 AI야.

가능한 action: "modify" (수정), "remove" (제거)
가능한 target: lip, blush, eyeliner, eyebrow, skin_base, eyeshadow

"없애줘", "제거해줘", "지워줘", "빼줘" 같은 요청은 action: "remove"로 처리해.

가능한 adjustment (action이 modify일 때):
- intensity: "+0.1" ~ "+0.3" (진하게/강하게), "-0.1" ~ "-0.3" (연하게/약하게)
- color: "#RRGGBB" 형식 (색상 변경 시)
- colors: ["#색상1", "#색상2", "#색상3"] (아이섀도우 그라데이션 색상들)
- color_shift: "redder"(더 빨갛게), "pinker"(더 핑크), "darker"(더 어둡게), "lighter"(더 밝게)
- style: "smoky"(스모키), "glitter"(글리터), "gradient"(그라데이션) - 아이섀도우 스타일
- tail_length: "+0.1" ~ "+0.2" (아이라이너 꼬리 길게), "-0.1" ~ "-0.2" (꼬리 짧게)
- thickness: "+1" ~ "+2" (아이라이너 두껍게), "-1" ~ "-2" (얇게)
- angle: "+5" ~ "+15" (아이라이너 각도 올림), "-5" ~ "-15" (각도 내림)
- type: "tone_up"(밝게), "tone_down"(어둡게), "warm"(따뜻하게), "cool"(차갑게) - 피부 타입
- warmth: "+0.3" ~ "+0.5" (피부 따뜻하게), "-0.3" ~ "-0.5" (피부 차갑게)

예시:
- "입술 진하게" → {"action": "modify", "target": "lip", "adjustment": {"intensity": "+0.2"}}
- "블러셔 많이 연하게" → {"action": "modify", "target": "blush", "adjustment": {"intensity": "-0.3"}}
- "볼터치 없애줘" → {"action": "remove", "target": "blush"}
- "립 제거해줘" → {"action": "remove", "target": "lip"}
- "아이라이너 지워줘" → {"action": "remove", "target": "eyeliner"}
- "눈썹 빼줘" → {"action": "remove", "target": "eyebrow"}
- "아이섀도우 없애줘" → {"action": "remove", "target": "eyeshadow"}
- "립 더 빨갛게" → {"action": "modify", "target": "lip", "adjustment": {"color_shift": "redder"}}
- "눈썹 살짝 진하게" → {"action": "modify", "target": "eyebrow", "adjustment": {"intensity": "+0.1"}}
- "스모키 메이크업으로" → {"action": "modify", "target": "eyeshadow", "adjustment": {"style": "smoky", "colors": ["#808080", "#404040", "#202020"]}}
- "글리터 아이섀도우" → {"action": "modify", "target": "eyeshadow", "adjustment": {"style": "glitter", "colors": ["#FFD700", "#FFC0CB"]}}
- "핑크 아이섀도우" → {"action": "modify", "target": "eyeshadow", "adjustment": {"style": "gradient", "colors": ["#FFB6C1", "#FF69B4", "#FF1493"]}}
- "아이섀도우 진하게" → {"action": "modify", "target": "eyeshadow", "adjustment": {"intensity": "+0.2"}}
- "아이라이너 더 길게" → {"action": "modify", "target": "eyeliner", "adjustment": {"tail_length": "+0.15"}}
- "아이라이너 짧게" → {"action": "modify", "target": "eyeliner", "adjustment": {"tail_length": "-0.1"}}
- "아이라이너 두껍게" → {"action": "modify", "target": "eyeliner", "adjustment": {"thickness": "+1"}}
- "아이라이너 각도 올려" → {"action": "modify", "target": "eyeliner", "adjustment": {"angle": "+10"}}
- "피부 어둡게" → {"action": "modify", "target": "skin_base", "adjustment": {"type": "tone_down", "intensity": "+0.2"}}
- "피부 밝게" → {"action": "modify", "target": "skin_base", "adjustment": {"type": "tone_up", "intensity": "+0.2"}}
- "피부 더 하얗게" → {"action": "modify", "target": "skin_base", "adjustment": {"type": "tone_up", "intensity": "+0.2"}}
- "피부 따뜻하게" → {"action": "modify", "target": "skin_base", "adjustment": {"warmth": "+0.4"}}
- "피부 차갑게" → {"action": "modify", "target": "skin_base", "adjustment": {"warmth": "-0.4"}}

반드시 JSON만 반환해. 다른 텍스트 없이."""
                },
                {"role": "user", "content": user_input}
            ],
            temperature=0.1,
            max_tokens=150
        )

        result = response.choices[0].message.content.strip()

        # ```json ... ``` 형식 제거
        if "```" in result:
            lines = result.split("```")
            for line in lines:
                line = line.strip()
                if line.startswith("json"):
                    line = line[4:].strip()
                if line.startswith("{"):
                    result = line
                    break

        parsed = json.loads(result)
        # action이 없으면 기본값 "modify" 사용
        if "action" not in parsed:
            parsed["action"] = "modify"
        return parsed

    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}, 원본: {result}")
        return None
    except Exception as e:
        print(f"GPT API 오류: {e}")
        return None


def modify_makeup(modification_text):
    """챗봇 스타일로 메이크업 수정 (GPT 파싱)"""
    global current_makeup

    if current_makeup is None:
        return None, "❌ 먼저 메이크업을 적용해주세요"

    # GPT로 자연어 파싱
    modification = parse_modification_with_gpt(modification_text)

    if modification is None:
        return None, "❌ 요청을 이해하지 못했어요. 다시 시도해주세요."

    # 메이크업 수정
    current_makeup = apply_modification(current_makeup, modification)

    # 다시 적용
    temp_input = "/tmp/temp_input.jpg"
    temp_output = "/tmp/temp_output_modified.jpg"

    result = applier.apply_makeup(
        image_path=temp_input,
        makeup_response=current_makeup,
        output_path=temp_output
    )

    makeup = current_makeup['makeup']
    action = modification.get("action", "modify")
    target = modification.get("target", "")

    # 제거 액션 처리
    if action == "remove":
        target_names = {
            "lip": "립", "blush": "볼터치", "eyeliner": "아이라이너",
            "eyebrow": "눈썹", "eyeshadow": "아이섀도우", "skin_base": "피부 베이스"
        }
        target_name = target_names.get(target, target)
        makeup_info = f"**{target_name} 제거됨**\n\n"
    else:
        makeup_info = f"**수정 적용됨:** {modification_text}\n\n"

    # 현재 적용된 메이크업 상태 표시
    if 'lip' in makeup:
        makeup_info += f"**현재 립 강도:** {makeup['lip']['intensity']:.0%}\n"
    if 'blush' in makeup:
        makeup_info += f"**현재 블러셔 강도:** {makeup['blush']['intensity']:.0%}\n"
    if 'eyeliner' in makeup:
        tail = makeup['eyeliner'].get('tail_length', 0.32)
        makeup_info += f"**아이라이너:** 두께 {makeup['eyeliner']['thickness']}, 꼬리 {tail:.0%}, 각도 {makeup['eyeliner']['angle']}°\n"
    if 'eyeshadow' in makeup:
        style = makeup['eyeshadow'].get('style', 'gradient')
        colors = makeup['eyeshadow'].get('colors', [])
        intensity = makeup['eyeshadow'].get('intensity', 0.5)
        makeup_info += f"**아이섀도우:** {style} 스타일 ({intensity:.0%}), 색상: {', '.join(colors)}\n"
    if 'eyebrow' in makeup:
        makeup_info += f"**눈썹:** {makeup['eyebrow']['intensity']:.0%}\n"
    if 'skin_base' in makeup:
        skin_type = makeup['skin_base'].get('type', 'tone_up')
        makeup_info += f"**피부 베이스:** {skin_type} ({makeup['skin_base']['intensity']:.0%})\n"

    return result, makeup_info


# Gradio UI
with gr.Blocks(title="가상 메이크업 테스트") as demo:
    gr.Markdown("# 💄 가상 메이크업 테스트")
    gr.Markdown("퍼스널컬러 기반 메이크업을 적용하고, 챗봇 스타일로 수정해보세요!")

    with gr.Row():
        with gr.Column():
            # 입력
            input_image = gr.Image(label="얼굴 사진 업로드", type="numpy")
            personal_color = gr.Textbox(
                label="퍼스널컬러 (응답값 입력)",
                placeholder="예: 봄 웜톤 / 여름 쿨톤 ...",
                lines=1
            )
            apply_btn = gr.Button("🎨 메이크업 적용", variant="primary")

        with gr.Column():
            # 출력
            output_image = gr.Image(label="결과")
            makeup_info = gr.Markdown(label="메이크업 정보")

    gr.Markdown("---")
    gr.Markdown("## 💬 메이크업 수정 (챗봇 스타일)")

    with gr.Row():
        modification_input = gr.Textbox(
            label="수정 요청",
            placeholder="예: 입술 더 진하게, 블러셔 연하게, 스모키 메이크업으로...",
            lines=1
        )
        modify_btn = gr.Button("수정 적용")

    gr.Markdown(f"**사용 가능한 수정 요청:** {', '.join(MODIFICATION_EXAMPLES.keys())}")

    # 이벤트 연결
    apply_btn.click(
        fn=apply_initial_makeup,
        inputs=[input_image, personal_color],
        outputs=[output_image, makeup_info]
    )

    modify_btn.click(
        fn=modify_makeup,
        inputs=[modification_input],
        outputs=[output_image, makeup_info]
    )


if __name__ == "__main__":
    print("🚀 Gradio 앱 시작...")
    print("⚠️ 첫 실행 시 모델 다운로드에 시간이 걸립니다 (약 4GB)")
    demo.launch(share=True)
