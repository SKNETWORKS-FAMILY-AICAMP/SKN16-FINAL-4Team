import type { ReportData } from '@/api/report';
import type { SurveyResultDetail } from '@/api/survey';
import type { PersonalColorType } from '@/types/personalColor';

/**
 * ReportData를 SurveyResultDetail 형태로 변환하는 함수
 * DiagnosisDetailModal에서 사용할 수 있는 형태로 변환
 */
export const convertReportDataToSurveyDetail = (reportData: ReportData, historyId: number): SurveyResultDetail => {
  // 결과 타입에서 퍼스널 컬러 타입 추출
  const resultType = reportData.report_data.user_info.result_type;
  const extractPersonalColorType = (resultTypeString: string): PersonalColorType => {
    const lowerResult = resultTypeString.toLowerCase();
    if (lowerResult.includes('봄') || lowerResult.includes('spring')) return 'spring';
    if (lowerResult.includes('여름') || lowerResult.includes('summer')) return 'summer';
    if (lowerResult.includes('가을') || lowerResult.includes('autumn')) return 'autumn';
    if (lowerResult.includes('겨울') || lowerResult.includes('winter')) return 'winter';
    return 'spring'; // 기본값
  };

  const personalColorType = extractPersonalColorType(resultType);

  // analysis_date가 한국어 형식일 경우 현재 날짜로 변환
  const analysisDate = reportData.report_data.user_info.analysis_date;
  let createdAt: string;
  
  // 한국어 날짜 형식인지 확인하고, ISO 형식으로 변환
  if (analysisDate && analysisDate.includes('년')) {
    // 현재 날짜를 ISO 형식으로 사용 (실제로는 백엔드에서 ISO 형식으로 보내는 것이 좋음)
    createdAt = new Date().toISOString();
  } else {
    // 이미 ISO 형식이거나 다른 형식인 경우
    createdAt = analysisDate || new Date().toISOString();
  }

  return {
    id: historyId,
    user_id: 0, // 사용자 ID는 현재 컨텍스트에서 알 수 없으므로 0으로 설정
    created_at: createdAt,
    result_tone: personalColorType,
    confidence: parseFloat(reportData.report_data.user_info.confidence.replace('%', '')),
    total_score: 100, // 기본값
    detailed_analysis: reportData.report_data.color_analysis.detailed_analysis,
    result_name: reportData.report_data.user_info.result_type,
    result_description: reportData.report_data.color_analysis.description,
    color_palette: reportData.report_data.color_recommendations.color_codes,
    style_keywords: reportData.report_data.color_recommendations.style_keywords,
    makeup_tips: reportData.report_data.color_recommendations.makeup_tips,
    // top_types를 단일 결과로 생성 (기존 설문 결과와 호환성을 위해)
    top_types: [{
      type: personalColorType,
      name: resultType,
      description: reportData.report_data.color_analysis.description,
      color_palette: reportData.report_data.color_recommendations.color_codes,
      style_keywords: reportData.report_data.color_recommendations.style_keywords,
      makeup_tips: reportData.report_data.color_recommendations.makeup_tips,
      score: 100 // 기본값
    }],
    answers: [] // 챗봇 진단에서는 설문 답변이 없으므로 빈 배열
  };
};

/**
 * 챗봇 진단 결과인지 확인하는 함수
 */
export const isChatbotDiagnosis = (result: SurveyResultDetail): boolean => {
  // 답변이 없거나 매우 적은 경우 챗봇 진단으로 간주
  return result.answers.length === 0;
};