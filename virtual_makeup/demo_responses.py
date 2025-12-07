# 퍼스널컬러별 데모 메이크업 Response

# === 기본 메이크업 설정 (초기 원본값) ===
# 사용자 요청 설정:
# - 피부 베이스: 톤업 30%
# - 볼터치: 피치 코랄 40%
# - 아이라이너: 소프트 블랙 80% (두께 4, 꼬리 32%, 각도 -15도)
# - 입술: 코랄 핑크 50%
# - 눈썹: 내추럴 브라운 20%
# - 속눈썹: 비활성화 (구현 문제로 제외)

DEFAULT_MAKEUP = {
    "personal_color": "기본",
    "makeup": {
        # 피부 베이스: 톤업, 30%
        "skin_base": {
            "type": "tone_up",
            "intensity": 0.3
        },
        # 입술: 코랄 핑크, 50%
        "lip": {
            "color": "#E8836B",  # 코랄 핑크
            "type": "glossy",
            "intensity": 0.5
        },
        # 볼터치: 피치 코랄, 40%
        "blush": {
            "color": "#FFAA80",  # 피치 코랄
            "position": "cheekbone",
            "intensity": 0.4
        },
        # 아이라이너: 소프트 블랙, 80%
        "eyeliner": {
            "color": "#2F2F2F",  # 소프트 블랙
            "intensity": 0.8,
            "thickness": 4,
            "tail_length": 0.32,  # 꼬리 32%
            "angle": -15.0        # 각도 -15도
        },
        # 눈썹: 내추럴 브라운, 20%
        "eyebrow": {
            "color": "#5C4033",  # 내추럴 브라운
            "intensity": 0.2
        }
        # 속눈썹, 아이섀도우: 비활성화
    },
    "recommendation_reason": "자연스럽고 데일리한 메이크업 기본 설정입니다."
}


MAKEUP_RESPONSES = {
    "봄_웜톤": {
        "personal_color": "봄 웜톤",
        "makeup": {
            "lip": {
                "color": "#E8836B",  # 코랄
                "type": "glossy"
            },
            "blush": {
                "color": "#FFAA80"  # 피치
            }
        },
        "recommendation_reason": "밝고 따뜻한 코랄, 피치 계열이 봄 웜톤의 화사한 피부를 더욱 빛나게 해줍니다."
    },

    "여름_쿨톤": {
        "personal_color": "여름 쿨톤",
        "makeup": {
            "lip": {
                "color": "#DB7093",  # 로즈 핑크
                "type": "matte"
            },
            "blush": {
                "color": "#FFB6C1"  # 라이트 핑크
            }
        },
        "recommendation_reason": "부드러운 로즈, 라벤더 계열이 여름 쿨톤의 우아한 분위기를 살려줍니다."
    },

    "가을_웜톤": {
        "personal_color": "가을 웜톤",
        "makeup": {
            "lip": {
                "color": "#8B4513",  # 브라운 레드
                "type": "matte"
            },
            "blush": {
                "color": "#CD853F"  # 테라코타
            }
        },
        "recommendation_reason": "깊고 따뜻한 브라운, 테라코타 계열이 가을 웜톤의 성숙한 매력을 강조합니다."
    },

    "겨울_쿨톤": {
        "personal_color": "겨울 쿨톤",
        "makeup": {
            "lip": {
                "color": "#C41E3A",  # 체리 레드
                "type": "matte"
            },
            "blush": {
                "color": "#DB7093"  # 쿨 핑크
            }
        },
        "recommendation_reason": "선명하고 강렬한 레드, 실버 계열이 겨울 쿨톤의 드라마틱한 분위기를 완성합니다."
    }
}

# 수정 요청 예시
MODIFICATION_EXAMPLES = {
    "입술 더 진하게": {
        "action": "modify",
        "target": "lip",
        "adjustment": {
            "intensity": "+0.2"
        }
    },
    "입술 연하게": {
        "action": "modify",
        "target": "lip",
        "adjustment": {
            "intensity": "-0.2"
        }
    },
    "블러셔 연하게": {
        "action": "modify",
        "target": "blush",
        "adjustment": {
            "intensity": "-0.2"
        }
    },
    "립 색상 더 빨갛게": {
        "action": "modify",
        "target": "lip",
        "adjustment": {
            "color_shift": "redder"
        }
    },
    "볼터치 없애줘": {
        "action": "remove",
        "target": "blush"
    },
    "립 제거": {
        "action": "remove",
        "target": "lip"
    },
    "아이라이너 지워줘": {
        "action": "remove",
        "target": "eyeliner"
    }
}


def _merge_makeup(base: dict, incoming: dict) -> dict:
    """기본 메이크업 위에 incoming 항목을 덮어쓰되, dict 값은 병합."""
    import copy

    merged = copy.deepcopy(base)

    for makeup_key, makeup_value in incoming.get("makeup", {}).items():
        if makeup_key in merged["makeup"] and isinstance(makeup_value, dict):
            merged["makeup"][makeup_key].update(makeup_value)
        else:
            merged["makeup"][makeup_key] = copy.deepcopy(makeup_value)

    merged["personal_color"] = incoming.get("personal_color", merged.get("personal_color"))
    merged["recommendation_reason"] = incoming.get("recommendation_reason", merged.get("recommendation_reason"))
    return merged


def get_makeup_response(personal_color: str) -> dict:
    """
    퍼스널컬러에 맞는 메이크업 추천 반환 (DEFAULT_MAKEUP 베이스로 병합)

    NOTE: personal_color가 "기본"이면 DEFAULT_MAKEUP을 그대로 반환.
    """
    import copy

    if personal_color in ("기본", "default", "기본 메이크업", None):
        return copy.deepcopy(DEFAULT_MAKEUP)

    key = personal_color.replace(" ", "_")
    personal_makeup = MAKEUP_RESPONSES.get(key, MAKEUP_RESPONSES["봄_웜톤"])
    return _merge_makeup(DEFAULT_MAKEUP, personal_makeup)


def prepare_makeup_response(personal_color: str, external_response: dict | None = None) -> dict:
    """
    외부(RAG/모델)에서 받은 메이크업 응답을 앱에서 바로 쓸 수 있는 형태로 병합.

    기대 포맷(단순화):
    {
        "personal_color": "봄 웜톤",            # 선택
        "makeup": {
            "lip": {"color": "#E8836B"},        # 필수: 립 색상(HEX)
            "blush": {"color": "#FFAA80"},      # 필수: 블러셔 색상(HEX)
            "eyebrow": {"color": "#5C4033"},    # 필수: 눈썹 색상(HEX)
            # 선택: "eyeshadow": {"colors": ["#FFB6C1", "#FF69B4"]}
            # 선택: "eyeliner": {"color": "#2F2F2F"}
            # skin_base는 기본값(tone_up, 0.3, warmth 0.0)으로 고정
        },
        "recommendation_reason": "설명 텍스트"   # 선택
    }

    - 색상 외 항목은 보내지 않아도 되고, 보내면 그대로 사용
    - 아이섀도우/아이라이너는 생략 가능, 피부 베이스는 기본값 고정
    """
    import copy

    if external_response:
        incoming = copy.deepcopy(external_response)
        result = {
            "personal_color": incoming.get("personal_color", personal_color),
            "recommendation_reason": incoming.get(
                "recommendation_reason",
                DEFAULT_MAKEUP.get("recommendation_reason")
            ),
            "makeup": copy.deepcopy(incoming.get("makeup", {}))
        }
        # 피부 베이스는 기본값 고정
        result["makeup"]["skin_base"] = copy.deepcopy(DEFAULT_MAKEUP["makeup"]["skin_base"])
        return result

    result = get_makeup_response(personal_color)
    # 피부 베이스는 기본값 고정
    result["makeup"]["skin_base"] = copy.deepcopy(DEFAULT_MAKEUP["makeup"]["skin_base"])
    return result


def apply_modification(current_makeup: dict, modification: dict) -> dict:
    """수정 요청을 현재 메이크업에 적용"""
    import copy
    new_makeup = copy.deepcopy(current_makeup)

    action = modification.get("action", "modify")
    target = modification.get("target")
    adjustment = modification.get("adjustment", {})

    # remove action 처리: 해당 메이크업 요소 제거
    if action == "remove":
        if target in new_makeup["makeup"]:
            del new_makeup["makeup"][target]
        return new_makeup

    # target이 없으면 기본값으로 생성
    if target not in new_makeup["makeup"]:
        new_makeup["makeup"][target] = {"intensity": 0.5}

    target_makeup = new_makeup["makeup"][target]

    # intensity 조절
    if "intensity" in adjustment:
        change = adjustment["intensity"]
        current_intensity = target_makeup.get("intensity", 0.5)
        if isinstance(change, str):
            if change.startswith("+"):
                target_makeup["intensity"] = min(1.0, current_intensity + float(change[1:]))
            elif change.startswith("-"):
                target_makeup["intensity"] = max(0.1, current_intensity - float(change[1:]))
        else:
            target_makeup["intensity"] = change

    # style 변경 (아이섀도우용)
    if "style" in adjustment:
        target_makeup["style"] = adjustment["style"]

    # colors 변경 (아이섀도우용)
    if "colors" in adjustment:
        target_makeup["colors"] = adjustment["colors"]

    # color 변경 (단일 색상)
    if "color" in adjustment:
        target_makeup["color"] = adjustment["color"]

    # color_shift 처리
    if "color_shift" in adjustment:
        shift = adjustment["color_shift"]
        if "color" in target_makeup:
            current_color = target_makeup["color"]
            target_makeup["color"] = apply_color_shift(current_color, shift)

    # 아이라이너 tail_length 조절
    if "tail_length" in adjustment:
        change = adjustment["tail_length"]
        current_tail = target_makeup.get("tail_length", 0.32)
        if isinstance(change, str):
            if change.startswith("+"):
                target_makeup["tail_length"] = min(0.8, current_tail + float(change[1:]))
            elif change.startswith("-"):
                target_makeup["tail_length"] = max(0.1, current_tail - float(change[1:]))
        else:
            target_makeup["tail_length"] = float(change)

    # 아이라이너 thickness 조절
    if "thickness" in adjustment:
        change = adjustment["thickness"]
        current_thickness = target_makeup.get("thickness", 4)
        if isinstance(change, str):
            if change.startswith("+"):
                target_makeup["thickness"] = min(10, current_thickness + int(change[1:]))
            elif change.startswith("-"):
                target_makeup["thickness"] = max(1, current_thickness - int(change[1:]))
        else:
            target_makeup["thickness"] = int(change)

    # 아이라이너 angle 조절
    if "angle" in adjustment:
        change = adjustment["angle"]
        current_angle = target_makeup.get("angle", -15.0)
        if isinstance(change, str):
            if change.startswith("+"):
                target_makeup["angle"] = min(30, current_angle + float(change[1:]))
            elif change.startswith("-"):
                target_makeup["angle"] = max(-45, current_angle - float(change[1:]))
        else:
            target_makeup["angle"] = float(change)

    # 피부 type 변경 (tone_up, tone_down, warm, cool)
    if "type" in adjustment:
        target_makeup["type"] = adjustment["type"]

    # 피부 warmth 조절
    if "warmth" in adjustment:
        change = adjustment["warmth"]
        current_warmth = target_makeup.get("warmth", 0.0)
        if isinstance(change, str):
            if change.startswith("+"):
                target_makeup["warmth"] = min(1.0, current_warmth + float(change[1:]))
            elif change.startswith("-"):
                target_makeup["warmth"] = max(-1.0, current_warmth - float(change[1:]))
        else:
            target_makeup["warmth"] = float(change)

    return new_makeup


def apply_color_shift(hex_color: str, shift: str) -> str:
    """색상 조정 (redder, pinker, darker, lighter)"""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    if shift == "redder":
        r = min(255, r + 30)
        g = max(0, g - 15)
        b = max(0, b - 15)
    elif shift == "pinker":
        r = min(255, r + 20)
        b = min(255, b + 20)
    elif shift == "darker":
        r = max(0, r - 30)
        g = max(0, g - 30)
        b = max(0, b - 30)
    elif shift == "lighter":
        r = min(255, r + 30)
        g = min(255, g + 30)
        b = min(255, b + 30)

    return f"#{r:02X}{g:02X}{b:02X}"


if __name__ == "__main__":
    # 테스트
    print("=== 봄 웜톤 메이크업 ===")
    response = get_makeup_response("봄 웜톤")
    print(response)

    print("\n=== 입술 더 진하게 수정 ===")
    modified = apply_modification(response, MODIFICATION_EXAMPLES["입술 더 진하게"])
    print(f"수정 전 intensity: {response['makeup']['lip']['intensity']}")
    print(f"수정 후 intensity: {modified['makeup']['lip']['intensity']}")
