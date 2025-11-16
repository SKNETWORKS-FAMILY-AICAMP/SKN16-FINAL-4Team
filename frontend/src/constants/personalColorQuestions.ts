import type {
  PersonalColorQuestion,
  PersonalColorResult,
} from '@/types/personalColor';

export const PERSONAL_COLOR_QUESTIONS: PersonalColorQuestion[] = [
  {
    id: 1,
    category: '피부 색상',
    question: '자연광에서 손목 안쪽 피부를 보면 전체적으로 어떤 색감이 도나요?',
    options: [
      {
        id: 'opt_warm_undertone',
        label: '노란빛, 복숭아빛 - 황금색 느낌',
        scores: { spring: 2, summer: 0, autumn: 2, winter: 0 },
      },
      {
        id: 'opt_cool_undertone',
        label: '분홍빛, 붉은빛 - 분홍색 느낌',
        scores: { spring: 0, summer: 2, autumn: 0, winter: 2 },
      },
      {
        id: 'opt_neutral_undertone',
        label: '두 색감이 섞여있음',
        scores: { spring: 1, summer: 1, autumn: 1, winter: 1 },
      },
    ],
  },
  {
    id: 2,
    category: '피부 명도',
    question: '전반적인 피부 톤의 밝기는 어떻게 되나요?',
    options: [
      {
        id: 'opt_light_skin',
        label: '밝음 (아이보리, 밝은 베이지 톤)',
        scores: { spring: 2, summer: 2, autumn: 0, winter: 0 },
      },
      {
        id: 'opt_medium_skin',
        label: '중간 (자연스러운 중간 톤)',
        scores: { spring: 1, summer: 1, autumn: 2, winter: 1 },
      },
      {
        id: 'opt_dark_skin',
        label: '어두움 (깊고 어두운 톤)',
        scores: { spring: 0, summer: 0, autumn: 1, winter: 2 },
      },
    ],
  },
  {
    id: 3,
    category: '머리카락 색상',
    question:
      '자연 상태의 머리카락 색상은 어떤가요? (염색하지 않은 본래 색기준)',
    options: [
      {
        id: 'opt_hair_golden',
        label: '금색, 밝은 갈색, 적갈색',
        scores: { spring: 3, summer: 0, autumn: 1, winter: 0 },
      },
      {
        id: 'opt_hair_ashy',
        label: '회색기미, 애쉬 갈색, 밝은 갈색',
        scores: { spring: 0, summer: 3, autumn: 0, winter: 0 },
      },
      {
        id: 'opt_hair_deep_warm',
        label: '구리색, 초콜릿, 검정색',
        scores: { spring: 0, summer: 0, autumn: 3, winter: 0 },
      },
      {
        id: 'opt_hair_deep_cool',
        label: '검정색, 진한 갈색',
        scores: { spring: 0, summer: 0, autumn: 0, winter: 3 },
      },
    ],
  },
  {
    id: 4,
    category: '눈동자 색상',
    question: '눈동자의 색상과 톤은 어떻게 되나요?',
    options: [
      {
        id: 'opt_eye_warm_light',
        label: '황금 갈색, 토파즈, 밝은 아쿠아',
        scores: { spring: 3, summer: 0, autumn: 1, winter: 0 },
      },
      {
        id: 'opt_eye_cool_soft',
        label: '연한 파란색, 회색 파란색, 소프트 갈색',
        scores: { spring: 0, summer: 3, autumn: 0, winter: 0 },
      },
      {
        id: 'opt_eye_warm_deep',
        label: '올리브 그린, 황금 갈색, 검은색',
        scores: { spring: 0, summer: 0, autumn: 3, winter: 0 },
      },
      {
        id: 'opt_eye_cool_clear',
        label: '검은색, 회색, 깊은 파란색',
        scores: { spring: 0, summer: 0, autumn: 0, winter: 3 },
      },
    ],
  },
  {
    id: 5,
    category: '손목 정맥',
    question: '손목 안쪽의 정맥 색을 보면 어떻게 보이나요?',
    options: [
      {
        id: 'opt_vein_golden_green',
        label: '녹색 또는 노란 녹색',
        scores: { spring: 2, summer: 0, autumn: 2, winter: 0 },
      },
      {
        id: 'opt_vein_blue',
        label: '파란색 또는 보라 파란색',
        scores: { spring: 0, summer: 2, autumn: 0, winter: 2 },
      },
      {
        id: 'opt_vein_mixed',
        label: '녹색과 파란색이 섞여있음',
        scores: { spring: 1, summer: 1, autumn: 1, winter: 1 },
      },
    ],
  },
  {
    id: 6,
    category: '보조 특성 - 혈색',
    question: '얼굴의 혈색은 어떻게 보이나요?',
    options: [
      {
        id: 'opt_complexion_healthy',
        label: '생기있고 투명함 - 밝고 건강한 인상',
        scores: { spring: 2, summer: 1, autumn: 0, winter: 0 },
      },
      {
        id: 'opt_complexion_rosy',
        label: '분홍색 또는 붉은 색감 - 분홍빛 도는 인상',
        scores: { spring: 0, summer: 2, autumn: 0, winter: 1 },
      },
      {
        id: 'opt_complexion_muted',
        label: '차분하거나 흐릿함 - 깊고 자연스러운 인상',
        scores: { spring: 0, summer: 0, autumn: 2, winter: 1 },
      },
    ],
  },
  {
    id: 7,
    category: '메탈 악세서리',
    question: '금장과 은장 중 얼굴을 더 밝고 생기있게 보이게 하는 것은?',
    options: [
      {
        id: 'opt_metal_warm',
        label: '골드/구리색',
        scores: { spring: 2, summer: 0, autumn: 2, winter: 0 },
      },
      {
        id: 'opt_metal_cool',
        label: '실버/백금',
        scores: { spring: 0, summer: 2, autumn: 0, winter: 2 },
      },
      {
        id: 'opt_metal_both',
        label: '둘 다 어울림',
        scores: { spring: 1, summer: 1, autumn: 1, winter: 1 },
      },
    ],
  },
  {
    id: 8,
    category: '화이트/베이지 톤',
    question:
      '순백색과 아이보리/크림색 중 피부를 더 환하고 깔끔하게 보이게 하는 색은?',
    options: [
      {
        id: 'opt_white_pure',
        label: '순백색 - 깨끗하고 선명한 흰색',
        scores: { spring: 0, summer: 2, autumn: 0, winter: 2 },
      },
      {
        id: 'opt_white_ivory',
        label: '아이보리/크림색 - 따뜻하고 부드러운 흰색',
        scores: { spring: 2, summer: 0, autumn: 2, winter: 0 },
      },
      {
        id: 'opt_white_unsure',
        label: '둘 다 비슷하게 보임',
        scores: { spring: 1, summer: 1, autumn: 1, winter: 1 },
      },
    ],
  },
];

export const PERSONAL_COLOR_RESULTS: Record<string, PersonalColorResult> = {
  spring: {
    type: 'spring',
    scores: { spring: 0, summer: 0, autumn: 0, winter: 0 },
    confidence: 0,
    name: '봄 웜톤 (Spring Warm)',
    description: '밝고 화사한 당신은 생동감 넘치는 봄의 여신입니다!',
    characteristics: [
      '화사함, 발랄함이 특징적인 스타일',
      '따뜻하고 밝은 피부톤',
      '생기발랄하고 젊은 인상',
      '선명하고 화사한 색상이 잘 어울림',
    ],
    keyColors: ['코럴', '피치', '골든 옐로우', '터콰이즈', '라벤더'],
    recommendedMakeup: [
      '코럴 블러셔',
      '피치 립',
      '골든 아이섀도우',
      '브라운 마스카라',
    ],
    avoidColors: [
      '네이비',
      '다크 그레이',
      '머스타드',
      '올리브 그린',
      '다크 퍼플',
    ],
    styles: ['화사함', '발랄함', '생동감', '밝음', '따뜻함'],
    swatches: [
      '#FF6F61',
      '#FFD1B3',
      '#FFE5B4',
      '#98FB98',
      '#40E0D0',
      '#E6E6FA',
      '#FFFACD',
    ],
    recommendations: {
      bestColors: [
        '코럴',
        '피치',
        '라이트 옐로우',
        '민트',
        '라임그린',
        '터콰이즈',
        '라벤더',
      ],
      avoidColors: [
        '네이비',
        '다크 그레이',
        '머스타드',
        '올리브 그린',
        '다크 퍼플',
      ],
      makeup: {
        foundation: '코럴 컬러, 피치 블러셔, 골든 아이섀도우',
        lipstick: ['코럴핑크', '피치', '살구색', '따뜻한 코럴'],
        eyeshadow: ['골든브라운', '피치', '코럴', '라이트 옐로우'],
      },
      fashion: {
        basic: ['아이보리', '밝은 베이지', '크림', '라이트 그레이'],
        accent: ['코럴', '피치', '라임그린', '터콰이즈'],
      },
    },
  },
  summer: {
    type: 'summer',
    scores: { spring: 0, summer: 0, autumn: 0, winter: 0 },
    confidence: 0,
    name: '여름 쿨톤 (Summer Cool)',
    description: '우아하고 부드러운 당신은 시원한 여름의 요정입니다!',
    characteristics: [
      '차분함, 세련됨이 특징적인 스타일',
      '시원하고 부드러운 피부톤',
      '우아하고 로맨틱한 인상',
      '부드럽고 차분한 색상이 잘 어울림',
    ],
    keyColors: ['로즈', '라벤더', '소프트 블루', '더스티핑크', '라이트 그레이'],
    recommendedMakeup: [
      '로즈 블러셔',
      '더스티핑크 립',
      '라벤더 아이섀도우',
      '브라운 마스카라',
    ],
    avoidColors: ['머스타드', '올리브 그린', '오렌지', '브라운', '골드'],
    styles: ['차분함', '세련됨', '우아함', '로맨틱', '부드러움'],
    swatches: [
      '#F8BBD9',
      '#E6E6FA',
      '#ADD8E6',
      '#DDA0DD',
      '#D3D3D3',
      '#FFB6C1',
      '#B0E0E6',
    ],
    recommendations: {
      bestColors: [
        '로즈',
        '라벤더',
        '소프트 블루',
        '딥 블루',
        '라이트 그레이',
        '소프트 퍼플',
      ],
      avoidColors: ['머스타드', '올리브 그린', '오렌지', '브라운', '골드'],
      makeup: {
        foundation: '로즈핑크, 로즈 블러셔, 핑크 브라운 아이섀도우',
        lipstick: ['로즈핑크', '더스티핑크', '라벤더핑크', '소프트베리'],
        eyeshadow: ['소프트브라운', '라벤더', '핑크브라운', '라이트블루'],
      },
      fashion: {
        basic: ['네이비', '그레이', '화이트', '소프트베이지'],
        accent: ['라벤더', '로즈', '소프트블루', '라이트퍼플'],
      },
    },
  },
  autumn: {
    type: 'autumn',
    scores: { spring: 0, summer: 0, autumn: 0, winter: 0 },
    confidence: 0,
    name: '가을 웜톤 (Autumn Warm)',
    description: '깊고 풍성한 당신은 성숙한 가을의 여왕입니다!',
    characteristics: [
      '따뜻함, 성숙함이 특징적인 스타일',
      '황금빛 따뜻한 피부톤',
      '깊이 있고 성숙한 인상',
      '깊고 따뜻한 색상이 잘 어울림',
    ],
    keyColors: ['버건디', '카키', '골드', '딥 오렌지', '올리브 그린'],
    recommendedMakeup: [
      '오렌지 블러셔',
      '브릭레드 립',
      '골든브라운 아이섀도우',
      '브라운 마스카라',
    ],
    avoidColors: ['블랙', '순백색', '네이비', '푸시아', '실버'],
    styles: ['따뜻함', '성숙함', '깊이', '풍성함', '고급스러움'],
    swatches: [
      '#800020',
      '#8B7355',
      '#FFD700',
      '#FF4500',
      '#556B2F',
      '#A0522D',
      '#CD853F',
    ],
    recommendations: {
      bestColors: [
        '버건디',
        '카키',
        '골드',
        '딥 오렌지',
        '딥 브라운',
        '올리브 그린',
      ],
      avoidColors: ['블랙', '순백색', '네이비', '푸시아', '실버'],
      makeup: {
        foundation: '골드 컬러, 오렌지 블러셔, 브라운 계열 아이섀도우',
        lipstick: ['브릭레드', '오렌지브라운', '딥코럴', '버건디'],
        eyeshadow: ['골든브라운', '딥오렌지', '카키', '브론즈'],
      },
      fashion: {
        basic: ['카멜', '딥브라운', '카키', '크림'],
        accent: ['버건디', '골드', '딥오렌지', '올리브그린'],
      },
    },
  },
  winter: {
    type: 'winter',
    scores: { spring: 0, summer: 0, autumn: 0, winter: 0 },
    confidence: 0,
    name: '겨울 쿨톤 (Winter Cool)',
    description: '강렬하고 명확한 당신은 차가운 겨울의 여신입니다!',
    characteristics: [
      '강렬함, 고급스러움이 특징적인 스타일',
      '시원하고 맑은 피부톤',
      '도시적이고 시크한 인상',
      '강렬하고 선명한 색상이 잘 어울림',
    ],
    keyColors: ['블랙', '퓨어 화이트', '로얄블루', '푸시아', '트루레드'],
    recommendedMakeup: [
      '푸시아 블러셔',
      '트루레드 립',
      '스모키 아이섀도우',
      '블랙 마스카라',
    ],
    avoidColors: ['베이지', '머스타드', '옐로우', '카키', '오렌지'],
    styles: ['강렬함', '고급스러움', '시크함', '도시적', '명확함'],
    swatches: [
      '#000000',
      '#FFFFFF',
      '#4169E1',
      '#FF1493',
      '#DC143C',
      '#50C878',
      '#191970',
    ],
    recommendations: {
      bestColors: [
        '블랙',
        '퓨어 화이트',
        '버건디',
        '아이비',
        '로얄블루',
        '푸시아',
      ],
      avoidColors: ['베이지', '머스타드', '옐로우', '카키', '오렌지'],
      makeup: {
        foundation: '레드 컬러, 푸시아 블러셔, 스모키 아이섀도우',
        lipstick: ['트루레드', '딥베리', '푸시아', '와인레드'],
        eyeshadow: ['스모키그레이', '딥퍼플', '네이비', '실버'],
      },
      fashion: {
        basic: ['블랙', '퓨어 화이트', '네이비', '차콜 그레이'],
        accent: ['로얄 블루', '푸시아', '트루 레드', '에메랄드'],
      },
    },
  },
};
