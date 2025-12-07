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
    # === 봄 (Spring) ===
    "봄_웜톤": {  # Fallback
        "personal_color": "봄 웜톤",
        "makeup": {
            "lip": {"color": "#FF7F50", "type": "glossy"},  # Coral
            "blush": {"color": "#FF9966"},  # Apricot
            "eyeshadow": {"colors": ["#FFDAB9", "#FFA07A"], "style": "gradient"}
        },
        "recommendation_reason": "봄 웜톤의 화사함과 생기를 살려주는 코랄, 피치 컬러가 베스트입니다."
    },
    "봄_라이트": {
        "personal_color": "봄 라이트",
        "makeup": {
            "lip": {"color": "#FFB7C5", "type": "glossy", "intensity": 0.4},  # Light Pink/Coral
            "blush": {"color": "#FFDAB9", "intensity": 0.3},  # Peach Puff
            "eyeshadow": {"colors": ["#FFF5EE", "#FFE4E1"], "style": "gradient"},
            "eyeliner": {"color": "#8B4513", "thickness": 2, "intensity": 0.6} # Soft Brown
        },
        "recommendation_reason": "투명하고 맑은 이미지를 위해 연한 파스텔 톤의 코랄과 피치를 사용하고, 진한 아이라인은 피하는 것이 좋습니다."
    },
    "봄_트루": {
        "personal_color": "봄 트루",
        "makeup": {
            "lip": {"color": "#FF6347", "type": "glossy", "intensity": 0.6},  # Tomato/Coral Red
            "blush": {"color": "#FF7F50", "intensity": 0.5},  # Coral
            "eyeshadow": {"colors": ["#FFD700", "#DAA520"], "style": "gradient"}, # Gold
            "eyeliner": {"color": "#5C4033", "thickness": 3}
        },
        "recommendation_reason": "따뜻하고 생동감 넘치는 오렌지, 코랄 레드 컬러가 봄 트루 타입의 에너지를 돋보이게 합니다."
    },
    "봄_브라이트": {
        "personal_color": "봄 브라이트",
        "makeup": {
            "lip": {"color": "#FF4500", "type": "glossy", "intensity": 0.7},  # Orange Red
            "blush": {"color": "#FF69B4", "intensity": 0.4},  # Hot Pink (Warm)
            "eyeshadow": {"colors": ["#FFE4B5", "#FFA500"], "style": "gradient"},
            "eyeliner": {"color": "#000000", "thickness": 3, "intensity": 0.9} # Clear contrast
        },
        "recommendation_reason": "채도가 높고 선명한 비비드 컬러가 잘 어울리며, 또렷한 아이라인과 립 포인트 메이크업이 베스트입니다."
    },

    # === 여름 (Summer) ===
    "여름_쿨톤": { # Fallback
        "personal_color": "여름 쿨톤",
        "makeup": {
            "lip": {"color": "#FF69B4", "type": "matte"},  # Hot Pink
            "blush": {"color": "#D8BFD8"},  # Thistle
            "eyeshadow": {"colors": ["#E6E6FA", "#D8BFD8"], "style": "gradient"}
        },
        "recommendation_reason": "여름 쿨톤의 청량하고 우아한 분위기를 위해 핑크, 라벤더 계열을 추천합니다."
    },
    "여름_라이트": {
        "personal_color": "여름 라이트",
        "makeup": {
            "lip": {"color": "#FFB6C1", "type": "glossy", "intensity": 0.4},  # Light Pink
            "blush": {"color": "#E6E6FA", "intensity": 0.3},  # Lavender
            "eyeshadow": {"colors": ["#F0F8FF", "#E6E6FA"], "style": "gradient"},
            "eyeliner": {"color": "#696969", "thickness": 2, "intensity": 0.5} # Dim Grey
        },
        "recommendation_reason": "흰기가 섞인 파스텔 톤의 딸기우유 핑크나 라벤더 컬러로 맑고 깨끗한 느낌을 연출하세요."
    },
    "여름_트루": {
        "personal_color": "여름 트루",
        "makeup": {
            "lip": {"color": "#C71585", "type": "matte", "intensity": 0.6},  # Medium Violet Red
            "blush": {"color": "#DDA0DD", "intensity": 0.4},  # Plum
            "eyeshadow": {"colors": ["#D8BFD8", "#BA55D3"], "style": "gradient"},
            "eyeliner": {"color": "#555555", "thickness": 3}
        },
        "recommendation_reason": "쿨톤의 정석인 로즈 핑크, 오키드 컬러를 사용하여 시원하고 세련된 이미지를 강조하세요."
    },
    "여름_뮤트": {
        "personal_color": "여름 뮤트",
        "makeup": {
            "lip": {"color": "#BC8F8F", "type": "matte", "intensity": 0.5},  # Rosy Brown
            "blush": {"color": "#D8BFD8", "intensity": 0.3},  # Thistle (Greyish)
            "eyeshadow": {"colors": ["#C0C0C0", "#778899"], "style": "smoky"}, # Silver/Grey
            "eyeliner": {"color": "#483D8B", "thickness": 3} # Dark Slate Blue
        },
        "recommendation_reason": "회색빛이 섞인 차분한 말린 장미(MLBB) 컬러나 모브 톤으로 분위기 있는 메이크업을 완성하세요."
    },

    # === 가을 (Autumn) ===
    "가을_웜톤": { # Fallback
        "personal_color": "가을 웜톤",
        "makeup": {
            "lip": {"color": "#A52A2A", "type": "matte"},  # Brown
            "blush": {"color": "#CD853F"},  # Peru
            "eyeshadow": {"colors": ["#DEB887", "#8B4513"], "style": "gradient"}
        },
        "recommendation_reason": "가을 웜톤의 그윽하고 고급스러운 분위기에는 브라운, 테라코타 컬러가 제격입니다."
    },
    "가을_소프트": { # Mute
        "personal_color": "가을 소프트",
        "makeup": {
            "lip": {"color": "#CD5C5C", "type": "matte", "intensity": 0.5},  # Indian Red
            "blush": {"color": "#F4A460", "intensity": 0.3},  # Sandy Brown
            "eyeshadow": {"colors": ["#F5DEB3", "#D2B48C"], "style": "gradient"}, # Wheat/Tan
            "eyeliner": {"color": "#8B4513", "thickness": 2}
        },
        "recommendation_reason": "부드럽고 차분한 베이지, 살몬, 누디한 컬러를 사용하여 자연스럽고 우아한 느낌을 주세요."
    },
    "가을_딥": {
        "personal_color": "가을 딥",
        "makeup": {
            "lip": {"color": "#800000", "type": "matte", "intensity": 0.8},  # Maroon
            "blush": {"color": "#8B4513", "intensity": 0.4},  # Saddle Brown
            "eyeshadow": {"colors": ["#CD853F", "#654321"], "style": "smoky"},
            "eyeliner": {"color": "#2F2F2F", "thickness": 4}
        },
        "recommendation_reason": "깊이감 있는 칠리, 브릭 레드, 다크 브라운 컬러로 고혹적이고 섹시한 분위기를 연출하세요."
    },

    # === 겨울 (Winter) ===
    "겨울_쿨톤": { # Fallback
        "personal_color": "겨울 쿨톤",
        "makeup": {
            "lip": {"color": "#DC143C", "type": "glossy"},  # Crimson
            "blush": {"color": "#FF00FF", "intensity": 0.2},  # Magenta (Light)
            "eyeshadow": {"colors": ["#E0FFFF", "#708090"], "style": "glitter"}
        },
        "recommendation_reason": "겨울 쿨톤의 카리스마 있는 이미지를 위해 선명한 레드, 푸시아 핑크와 블랙 아이라인을 추천합니다."
    },
    "겨울_브라이트": {
        "personal_color": "겨울 브라이트",
        "makeup": {
            "lip": {"color": "#FF00FF", "type": "glossy", "intensity": 0.8},  # Magenta
            "blush": {"color": "#FF69B4", "intensity": 0.3},  # Hot Pink
            "eyeshadow": {"colors": ["#FFFFFF", "#C0C0C0"], "style": "glitter"}, # White/Silver
            "eyeliner": {"color": "#000000", "thickness": 4, "intensity": 1.0}
        },
        "recommendation_reason": "형광빛이 도는 쨍한 핑크나 레드 립을 포인트로 하고, 눈화장은 깔끔하게 하거나 글리터로 포인트를 주세요."
    },
    "겨울_트루": {
        "personal_color": "겨울 트루",
        "makeup": {
            "lip": {"color": "#8B008B", "type": "matte", "intensity": 0.7},  # Dark Magenta
            "blush": {"color": "#DA70D6", "intensity": 0.3},  # Orchid
            "eyeshadow": {"colors": ["#E6E6FA", "#708090"], "style": "gradient"},
            "eyeliner": {"color": "#000000", "thickness": 3}
        },
        "recommendation_reason": "차가운 느낌의 플럼, 베리 계열 컬러가 피부를 더욱 하얗고 깨끗하게 보이게 합니다."
    },
    "겨울_딥": {
        "personal_color": "겨울 딥",
        "makeup": {
            "lip": {"color": "#800080", "type": "matte", "intensity": 0.9},  # Purple
            "blush": {"color": "#8B008B", "intensity": 0.2},  # Dark Magenta (Very light)
            "eyeshadow": {"colors": ["#708090", "#2F4F4F"], "style": "smoky"}, # Slate Grey
            "eyeliner": {"color": "#000000", "thickness": 4}
        },
        "recommendation_reason": "검붉은 버건디, 딥 퍼플 등 무게감 있는 컬러로 도시적이고 시크한 매력을 발산하세요."
    },
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
    
    # Direct match
    if key in MAKEUP_RESPONSES:
        personal_makeup = MAKEUP_RESPONSES[key]
    else:
        # Fallback based on season name
        if "봄" in personal_color:
            personal_makeup = MAKEUP_RESPONSES["봄_웜톤"]
        elif "여름" in personal_color:
            personal_makeup = MAKEUP_RESPONSES["여름_쿨톤"]
        elif "가을" in personal_color:
            personal_makeup = MAKEUP_RESPONSES["가을_웜톤"]
        elif "겨울" in personal_color:
            personal_makeup = MAKEUP_RESPONSES["겨울_쿨톤"]
        else:
            personal_makeup = MAKEUP_RESPONSES["봄_웜톤"]

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
