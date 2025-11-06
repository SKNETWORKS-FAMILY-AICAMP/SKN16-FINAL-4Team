#!/usr/bin/env python3
"""
Fine-tuned 모델 성능 평가 스크립트
"""

import os
import openai
import json
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

class ChatbotEvaluator:
    def __init__(self):
        """평가기 초기화"""
        # 환경변수에서 API 키와 모델 정보 가져오기
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # .env 파일에서 모델 정보 가져오기
        self.base_model = os.getenv('DEFAULT_MODEL', 'gpt-4.1-nano-2025-04-14')
        self.fine_tuned_model = os.getenv('EMOTION_MODEL_ID')
        
        print(f"🤖 Base Model: {self.base_model}")
        if self.fine_tuned_model:
            print(f"🎯 Fine-tuned Model: {self.fine_tuned_model[:30]}***")
        else:
            print("🎯 Fine-tuned Model: Not configured")
        
        # 평가용 프롬프트 세트 (친구 느낌, 감정 공감, 자연스러움 테스트)
        self.evaluation_prompts = [
            {
                "id": 1,
                "category": "고민상담형",
                "prompt": "요즘 회사 일이 너무 힘들어서 스트레스 받아. 나 어떡하면 좋을까?",
                "expected_tone": "공감, 위로, 실질적 조언"
            },
            {
                "id": 2,
                "category": "일상잡담형",
                "prompt": "오늘 날씨 좀 쌀쌀하네. 너는 이런 날씨 어떨 때 가장 좋다고 느껴?",
                "expected_tone": "친구같은 맞장구, 자기 경험 공유"
            },
            {
                "id": 3,
                "category": "감정인식형",
                "prompt": "나 오늘 기분이 좀 우울한 것 같아. 네가 내 기분을 알아차릴 수 있을까?",
                "expected_tone": "감정 인식, 위로, 응원"
            },
            {
                "id": 4,
                "category": "스트레스해소형",
                "prompt": "나 요즘 너무 바빠서 머리가 터질 것 같아. 너는 어떻게 스트레스 풀어?",
                "expected_tone": "가벼운 분위기, 친구 톤, 실용적 조언"
            },
            {
                "id": 5,
                "category": "응원형",
                "prompt": "시험 앞두고 너무 떨리는데, 너한테 응원 한마디 듣고 싶어.",
                "expected_tone": "응원, 격려, 긍정적 에너지"
            },
            {
                "id": 6,
                "category": "기쁨공유형",
                "prompt": "나 오늘 회사에서 칭찬 받았어! 왠지 기분 좋다.",
                "expected_tone": "축하, 기쁨 공유, 긍정적 반응"
            },
            {
                "id": 7,
                "category": "고민상담형",
                "prompt": "최근에 취업 준비하는데 너무 불안해. 조언 좀 해줄 수 있어?",
                "expected_tone": "공감, 조언, 격려"
            },
            {
                "id": 8,
                "category": "친밀감테스트형",
                "prompt": "너랑 이야기하면 기분 좋아질까?",
                "expected_tone": "친구 느낌, 따뜻한 반응"
            }
        ]

    def get_chatbot_response(self, prompt: str, model: str = None, use_system_prompt: bool = True) -> str:
        """
        챗봇 모델에 프롬프트를 전달하고 응답을 받는 함수
        """
        if model is None:
            model = self.fine_tuned_model or self.base_model
        
        try:
            messages = []
            
            # 시스템 프롬프트 추가 (선택적)
            if use_system_prompt:
                # Fine-tuned 모델용 최적화된 프롬프트 vs Base 모델용 프롬프트
                if model == self.fine_tuned_model:
                    # Fine-tuned 모델용 균형잡힌 프롬프트 - 감정 공감 능력 최대 활용
                    system_prompt = """당신은 사용자의 가장 친한 친구입니다. 다음 가이드라인을 따라 대화하세요:

� 감정 공감 우선:
- 사용자의 감정을 먼저 정확히 파악하고 공감 표현
- "정말 힘들겠다", "그런 마음 이해해" 같은 공감 언어 사용
- 감정을 무시하거나 성급히 해결책만 제시하지 말고 먼저 위로

💬 자연스러운 친구 톤:
- 적절한 친구 표현 사용 ("그치", "맞아", "진짜") 
- 친근하되 품격 유지
- 과도한 줄임말이나 지나친 캐주얼함은 피하기

🤝 진정성 있는 조언:
- 자신의 경험이나 생각을 자연스럽게 공유
- 실질적이면서도 따뜻한 해결책 제시
- 사용자가 혼자가 아님을 느끼게 하는 응원

당신은 감정을 깊이 이해하는 능력이 뛰어나므로, 이를 활용해 사용자와 진심어린 대화를 나누세요."""
                else:
                    # Base 모델용 기본 프롬프트
                    system_prompt = """당신은 친구처럼 편안하고 공감해주는 챗봇입니다. 
                    사용자의 감정을 잘 이해하고 자연스럽게 대화해주세요.
                    반말로 친구같이 편안하게 대화하되, 따뜻하고 진심어린 톤을 유지해주세요."""
                
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.8,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error: {str(e)}"

    def evaluate_response_manual(self, prompt_data: Dict, response: str) -> Dict:
        """
        사람이 직접 평가할 수 있도록 응답을 출력하고 점수 입력 받기
        """
        print("\n" + "="*80)
        print(f"📝 프롬프트 ID: {prompt_data['id']}")
        print(f"📂 카테고리: {prompt_data['category']}")
        print(f"👤 사용자 입력: {prompt_data['prompt']}")
        print(f"🎯 기대 톤: {prompt_data['expected_tone']}")
        print("-"*80)
        print(f"🤖 챗봇 응답:\n{response}")
        print("-"*80)
        
        # 평가 점수 입력 (1-10점 척도)
        print("\n평가 항목 (1-10점):")
        print("1-2점: 매우 부족, 3-4점: 부족, 5-6점: 보통, 7-8점: 좋음, 9-10점: 매우 우수")
        try:
            naturalness = int(input("1. 실제 친구와 대화하는 느낌 (자연스러움): "))
            empathy = int(input("2. 감정 공감 및 적절한 반응: "))
            friendliness = int(input("3. 친구같은 편안한 톤: "))
            
            # 점수 범위 체크
            for score, name in [(naturalness, "자연스러움"), (empathy, "감정공감"), (friendliness, "친구톤")]:
                if score < 1 or score > 10:
                    print(f"⚠️ {name} 점수가 범위를 벗어났습니다. 1-10 사이로 입력해주세요.")
                    return self.evaluate_response_manual(prompt_data, response)
            
        except ValueError:
            print("⚠️ 숫자만 입력해주세요.")
            return self.evaluate_response_manual(prompt_data, response)
        
        return {
            "prompt_id": prompt_data['id'],
            "category": prompt_data['category'],
            "naturalness": naturalness,
            "empathy": empathy,
            "friendliness": friendliness,
            "average": round((naturalness + empathy + friendliness) / 3, 2)
        }

    def auto_evaluate_with_gpt4(self, prompt: str, response: str) -> Dict:
        """
        GPT-4.1을 활용한 자동 평가
        """
        evaluation_prompt = f"""다음은 친구처럼 대화하는 챗봇의 응답입니다. 아래 기준으로 평가해주세요.

사용자 입력: {prompt}
챗봇 응답: {response}

평가 기준 (1-10점):
1. 자연스러움 (실제 친구와 대화하는 느낌, 기계적이지 않음)
   - 1-2: 매우 기계적, 3-4: 부자연스러움, 5-6: 보통, 7-8: 자연스러움, 9-10: 매우 자연스러움
2. 감정 공감력 (사용자 감정을 잘 파악하고 적절히 반응)
   - 1-2: 감정 무시, 3-4: 감정 파악 부족, 5-6: 보통, 7-8: 적절한 공감, 9-10: 매우 깊은 공감
3. 친구같은 톤 (편안하고 친근한 말투, 반말 사용)
   - 1-2: 매우 격식적, 3-4: 어색함, 5-6: 보통, 7-8: 친근함, 9-10: 진짜 친구 같음

JSON 형식으로 답변해주세요:
{{
  "naturalness": 점수(1-10),
  "empathy": 점수(1-10),
  "friendliness": 점수(1-10),
  "reasoning": "평가 이유 간단히"
}}"""
        
        try:
            response_eval = self.client.chat.completions.create(
                model=self.base_model,  # GPT-4.1-nano 사용
                messages=[{"role": "user", "content": evaluation_prompt}],
                temperature=0.3,
                max_tokens=300
            )
            
            eval_text = response_eval.choices[0].message.content.strip()
            
            # JSON 파싱 시도
            try:
                eval_result = json.loads(eval_text)
                eval_result["average"] = round((eval_result["naturalness"] + eval_result["empathy"] + eval_result["friendliness"]) / 3, 2)
                return eval_result
            except json.JSONDecodeError:
                # JSON 파싱 실패시 기본값 반환 (10점 기준)
                return {
                    "naturalness": 5,
                    "empathy": 5,
                    "friendliness": 5,
                    "average": 5.0,
                    "reasoning": f"파싱 실패. 원본: {eval_text[:100]}..."
                }
                
        except Exception as e:
            return {
                "naturalness": 1,
                "empathy": 1,
                "friendliness": 1,
                "average": 1.0,
                "error": str(e)
            }

    def run_evaluation(self, model: str = None, use_auto_eval: bool = False, save_results: bool = True):
        """
        전체 평가 프로세스 실행
        """
        if model is None:
            model = self.fine_tuned_model or self.base_model
        
        results = []
        model_name = "Fine-tuned" if model == self.fine_tuned_model else "Base"
        
        print(f"🚀 {model_name} 모델 성능 평가를 시작합니다...")
        print(f"📊 모델: {model}")
        print(f"🔍 평가 방식: {'자동 평가' if use_auto_eval else '수동 평가'}\n")
        
        for i, prompt_data in enumerate(self.evaluation_prompts, 1):
            print(f"\n진행률: {i}/{len(self.evaluation_prompts)}")
            
            # 챗봇 응답 생성
            response = self.get_chatbot_response(prompt_data['prompt'], model)
            
            # 평가 수행
            if use_auto_eval:
                evaluation = self.auto_evaluate_with_gpt4(prompt_data['prompt'], response)
                evaluation.update({
                    "prompt_id": prompt_data['id'],
                    "category": prompt_data['category']
                })
                print(f"✅ 자동 평가 완료 - 평균: {evaluation.get('average', 0):.2f}/10")
            else:
                evaluation = self.evaluate_response_manual(prompt_data, response)
            
            evaluation.update({
                'response': response,
                'prompt': prompt_data['prompt'],
                'model': model,
                'model_type': model_name
            })
            
            results.append(evaluation)
        
        # 결과 저장
        if save_results:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'chatbot_evaluation_results_{model_name.lower()}_{timestamp}.json'
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 평가 결과가 '{filename}'에 저장되었습니다.")
        
        # 결과 요약 출력
        self.print_evaluation_summary(results, model_name)
        
        return results

    def print_evaluation_summary(self, results: List[Dict], model_name: str):
        """평가 결과 요약 출력"""
        print("\n" + "="*80)
        print(f"📊 {model_name} 모델 평가 결과 요약")
        print("="*80)
        
        # 전체 평균 계산
        avg_naturalness = sum(r['naturalness'] for r in results) / len(results)
        avg_empathy = sum(r['empathy'] for r in results) / len(results)
        avg_friendliness = sum(r['friendliness'] for r in results) / len(results)
        overall_avg = sum(r['average'] for r in results) / len(results)
        
        print(f"🎯 전체 평균 점수:")
        print(f"   자연스러움: {avg_naturalness:.2f}/10.0")
        print(f"   감정 공감력: {avg_empathy:.2f}/10.0")
        print(f"   친구 느낌: {avg_friendliness:.2f}/10.0")
        print(f"   종합 평균: {overall_avg:.2f}/10.0")
        
        # 성능 등급 판정 (10점 기준)
        if overall_avg >= 9.0:
            grade = "🏆 최우수 (Exceptional)"
        elif overall_avg >= 8.0:
            grade = "🥇 우수 (Excellent)"
        elif overall_avg >= 7.0:
            grade = "✅ 양호 (Good)"
        elif overall_avg >= 6.0:
            grade = "🔄 보통 (Average)"
        elif overall_avg >= 5.0:
            grade = "⚠️ 개선필요 (Needs Improvement)"
        else:
            grade = "❌ 미흡 (Poor)"
        
        print(f"   성능 등급: {grade}")
        
        # 카테고리별 평균 점수
        print(f"\n📈 카테고리별 평균 점수:")
        categories = {}
        for r in results:
            cat = r['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r['average'])
        
        for cat, scores in categories.items():
            avg = sum(scores) / len(scores)
            print(f"   {cat}: {avg:.2f}/10.0")
        
        print("="*80)

    def comprehensive_four_way_comparison(self, use_auto_eval: bool = True):
        """4가지 케이스 종합 비교: Fine-tuning vs 프롬프트 엔지니어링 효과 분석"""
        if not self.fine_tuned_model:
            print("❌ Fine-tuned 모델이 설정되지 않았습니다.")
            return
        
        print("🔍 4가지 케이스 종합 성능 비교")
        print("="*80)
        print("1. Base Model (Raw)")
        print("2. Base Model + Prompt") 
        print("3. Fine-tuned Model (Raw)")
        print("4. Fine-tuned Model + Prompt")
        print("="*80)
        
        all_results = {}
        
        # 1. Base Model (Raw) - 시스템 프롬프트 없음
        print("\n1️⃣ Base Model (Raw) 평가")
        base_raw_results = []
        for i, prompt_data in enumerate(self.evaluation_prompts, 1):
            print(f"진행률: {i}/{len(self.evaluation_prompts)} - {prompt_data['prompt'][:30]}...")
            response = self.get_chatbot_response(prompt_data['prompt'], self.base_model, use_system_prompt=False)
            
            if use_auto_eval:
                evaluation = self.auto_evaluate_with_gpt4(prompt_data['prompt'], response)
                evaluation.update({"prompt_id": prompt_data['id'], "category": prompt_data['category']})
            else:
                print(f"\n🤖 Base Raw 응답: {response}")
                evaluation = self.evaluate_response_manual(prompt_data, response)
            
            evaluation.update({
                'response': response,
                'prompt': prompt_data['prompt'],
                'model': self.base_model,
                'model_type': 'Base_Raw'
            })
            base_raw_results.append(evaluation)
        
        all_results['base_raw'] = base_raw_results
        
        # 2. Base Model + Prompt
        print(f"\n2️⃣ Base Model + Prompt 평가")
        base_prompt_results = []
        for i, prompt_data in enumerate(self.evaluation_prompts, 1):
            print(f"진행률: {i}/{len(self.evaluation_prompts)} - {prompt_data['prompt'][:30]}...")
            response = self.get_chatbot_response(prompt_data['prompt'], self.base_model, use_system_prompt=True)
            
            if use_auto_eval:
                evaluation = self.auto_evaluate_with_gpt4(prompt_data['prompt'], response)
                evaluation.update({"prompt_id": prompt_data['id'], "category": prompt_data['category']})
            else:
                print(f"\n🤖 Base+Prompt 응답: {response}")
                evaluation = self.evaluate_response_manual(prompt_data, response)
            
            evaluation.update({
                'response': response,
                'prompt': prompt_data['prompt'],
                'model': self.base_model,
                'model_type': 'Base_Prompt'
            })
            base_prompt_results.append(evaluation)
        
        all_results['base_prompt'] = base_prompt_results
        
        # 3. Fine-tuned Model (Raw)
        print(f"\n3️⃣ Fine-tuned Model (Raw) 평가")
        ft_raw_results = []
        for i, prompt_data in enumerate(self.evaluation_prompts, 1):
            print(f"진행률: {i}/{len(self.evaluation_prompts)} - {prompt_data['prompt'][:30]}...")
            response = self.get_chatbot_response(prompt_data['prompt'], self.fine_tuned_model, use_system_prompt=False)
            
            if use_auto_eval:
                evaluation = self.auto_evaluate_with_gpt4(prompt_data['prompt'], response)
                evaluation.update({"prompt_id": prompt_data['id'], "category": prompt_data['category']})
            else:
                print(f"\n🤖 Fine-tuned Raw 응답: {response}")
                evaluation = self.evaluate_response_manual(prompt_data, response)
            
            evaluation.update({
                'response': response,
                'prompt': prompt_data['prompt'],
                'model': self.fine_tuned_model,
                'model_type': 'FT_Raw'
            })
            ft_raw_results.append(evaluation)
        
        all_results['ft_raw'] = ft_raw_results
        
        # 4. Fine-tuned Model + Prompt
        print(f"\n4️⃣ Fine-tuned Model + Prompt 평가")
        ft_prompt_results = []
        for i, prompt_data in enumerate(self.evaluation_prompts, 1):
            print(f"진행률: {i}/{len(self.evaluation_prompts)} - {prompt_data['prompt'][:30]}...")
            response = self.get_chatbot_response(prompt_data['prompt'], self.fine_tuned_model, use_system_prompt=True)
            
            if use_auto_eval:
                evaluation = self.auto_evaluate_with_gpt4(prompt_data['prompt'], response)
                evaluation.update({"prompt_id": prompt_data['id'], "category": prompt_data['category']})
            else:
                print(f"\n🤖 Fine-tuned+Prompt 응답: {response}")
                evaluation = self.evaluate_response_manual(prompt_data, response)
            
            evaluation.update({
                'response': response,
                'prompt': prompt_data['prompt'],
                'model': self.fine_tuned_model,
                'model_type': 'FT_Prompt'
            })
            ft_prompt_results.append(evaluation)
        
        all_results['ft_prompt'] = ft_prompt_results
        
        # 종합 결과 분석
        self.print_four_way_comparison_results(all_results)
        
        # 결과 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'four_way_comparison_results_{timestamp}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 4가지 케이스 비교 결과가 '{filename}'에 저장되었습니다.")
        
        return all_results

    def compare_models(self, use_auto_eval: bool = True):
        """Base 모델과 Fine-tuned 모델 비교 (기존 방식 유지)"""
        return self.comprehensive_four_way_comparison(use_auto_eval)

    def print_four_way_comparison_results(self, all_results: Dict):
        """4가지 케이스 종합 비교 결과 출력"""
        print("\n" + "="*80)
        print("🏆 4가지 케이스 종합 성능 비교 결과")
        print("="*80)
        
        # 각 케이스별 평균 점수 계산
        averages = {}
        for case_name, results in all_results.items():
            case_avg = sum(r['average'] for r in results) / len(results)
            averages[case_name] = case_avg
        
        # 결과 출력
        print(f"📊 케이스별 종합 성능:")
        print(f"   1. Base (Raw):          {averages['base_raw']:.2f}/10.0")
        print(f"   2. Base + Prompt:       {averages['base_prompt']:.2f}/10.0")
        print(f"   3. Fine-tuned (Raw):    {averages['ft_raw']:.2f}/10.0")
        print(f"   4. Fine-tuned + Prompt: {averages['ft_prompt']:.2f}/10.0")
        
        # 최고 성능 케이스 찾기
        best_case = max(averages.keys(), key=lambda k: averages[k])
        best_score = averages[best_case]
        
        case_names = {
            'base_raw': 'Base (Raw)',
            'base_prompt': 'Base + Prompt',
            'ft_raw': 'Fine-tuned (Raw)',
            'ft_prompt': 'Fine-tuned + Prompt'
        }
        
        print(f"\n🏆 최고 성능: {case_names[best_case]} ({best_score:.2f}/10.0)")
        
        # 효과 분석
        print(f"\n📈 효과 분석:")
        
        # Fine-tuning 효과 (Raw 모델 비교)
        ft_effect = averages['ft_raw'] - averages['base_raw']
        print(f"   Fine-tuning 순수 효과: {ft_effect:+.2f}점")
        
        # 프롬프트 효과 (Base 모델에서)
        prompt_effect_base = averages['base_prompt'] - averages['base_raw']
        print(f"   프롬프트 효과 (Base):  {prompt_effect_base:+.2f}점")
        
        # 프롬프트 효과 (Fine-tuned 모델에서)
        prompt_effect_ft = averages['ft_prompt'] - averages['ft_raw']
        print(f"   프롬프트 효과 (FT):    {prompt_effect_ft:+.2f}점")
        
        # 최적 조합 vs 기준선 비교
        improvement_from_baseline = averages['ft_prompt'] - averages['base_raw']
        print(f"   전체 개선 효과:         {improvement_from_baseline:+.2f}점")
        
        # 세부 항목별 분석
        print(f"\n📋 세부 항목별 비교:")
        metrics = ['naturalness', 'empathy', 'friendliness']
        metric_names = {'naturalness': '자연스러움', 'empathy': '감정공감', 'friendliness': '친구톤'}
        
        for metric in metrics:
            print(f"\n   {metric_names[metric]}:")
            for case_name, results in all_results.items():
                metric_avg = sum(r[metric] for r in results) / len(results)
                print(f"     {case_names[case_name]}: {metric_avg:.2f}/10.0")
        
        # 권장사항
        print(f"\n💡 권장사항:")
        if best_score >= 9.0:
            print(f"   ✅ {case_names[best_case]} 방식을 프로덕션에 적용 추천")
        elif best_score >= 8.0:
            print(f"   🔄 {case_names[best_case]} 방식이 가장 우수하나 추가 개선 고려")
        else:
            print(f"   ⚠️ 모든 방식이 8.0 미만. 추가적인 개선 작업 필요")
        
        # Fine-tuning vs 프롬프트 효과 비교
        if ft_effect > prompt_effect_base:
            print(f"   🎯 Fine-tuning이 프롬프트보다 {ft_effect - prompt_effect_base:.2f}점 더 효과적")
        elif prompt_effect_base > ft_effect:
            print(f"   🎯 프롬프트가 Fine-tuning보다 {prompt_effect_base - ft_effect:.2f}점 더 효과적")
        else:
            print(f"   ⚖️ Fine-tuning과 프롬프트 효과가 비슷함")
        
        print("="*80)

    def print_comparison_results(self, base_results: List[Dict], ft_results: List[Dict]):
        """모델 비교 결과 출력 (기존 방식 유지)"""
        print("\n" + "="*80)
        print("🏆 모델 성능 비교 결과")
        print("="*80)
        
        # 평균 점수 계산
        base_avg = sum(r['average'] for r in base_results) / len(base_results)
        ft_avg = sum(r['average'] for r in ft_results) / len(ft_results)
        
        improvement = ft_avg - base_avg
        
        print(f"📊 종합 성능:")
        print(f"   Base 모델: {base_avg:.2f}/10.0")
        print(f"   Fine-tuned 모델: {ft_avg:.2f}/10.0")
        print(f"   개선 정도: {improvement:+.2f}점")
        
        if improvement > 1.0:
            print(f"   🎉 Fine-tuning 효과: 상당한 개선!")
        elif improvement > 0.5:
            print(f"   ✅ Fine-tuning 효과: 의미있는 개선")
        elif improvement > 0:
            print(f"   🔄 Fine-tuning 효과: 약간의 개선")
        else:
            print(f"   ⚠️ Fine-tuning 효과: 개선 없음 또는 성능 저하")
        
        print("="*80)

def main():
    """메인 실행 함수"""
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   .env 파일에 OPENAI_API_KEY를 설정해주세요.")
        return
    
    evaluator = ChatbotEvaluator()
    
    print("🎓 AI 부트캠프 - 챗봇 성능 평가")
    print("="*60)
    
    # 평가 옵션 선택
    print("\n평가 옵션을 선택해주세요:")
    print("1. Fine-tuned 모델만 평가 (수동)")
    print("2. Fine-tuned 모델만 평가 (자동)")
    print("3. 4가지 케이스 종합 비교 (자동) ⭐ 추천")
    print("4. 4가지 케이스 종합 비교 (수동)")
    print("5. Base 모델만 평가 (수동)")
    
    try:
        choice = input("\n선택 (1-5): ").strip()
        
        if choice == "1":
            evaluator.run_evaluation(use_auto_eval=False)
        elif choice == "2":
            evaluator.run_evaluation(use_auto_eval=True)
        elif choice == "3":
            print("\n🚀 4가지 케이스 자동 비교를 시작합니다...")
            print("   1. Base (Raw)")
            print("   2. Base + Prompt") 
            print("   3. Fine-tuned (Raw)")
            print("   4. Fine-tuned + Prompt")
            evaluator.comprehensive_four_way_comparison(use_auto_eval=True)
        elif choice == "4":
            print("\n🚀 4가지 케이스 수동 비교를 시작합니다...")
            print("⚠️ 각 응답마다 직접 점수를 입력해야 합니다 (총 32회)")
            confirm = input("계속 진행하시겠습니까? (y/n): ").strip().lower()
            if confirm == 'y':
                evaluator.comprehensive_four_way_comparison(use_auto_eval=False)
            else:
                print("평가가 취소되었습니다.")
        elif choice == "5":
            evaluator.run_evaluation(model=evaluator.base_model, use_auto_eval=False)
        else:
            print("❌ 잘못된 선택입니다.")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 평가가 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()