import React, { useState, useRef } from 'react';
import { formatKoreanDate } from '@/utils/dateUtils';
import {
  Modal,
  Button,
  message,
} from 'antd';
import {
  DeleteOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import type { SurveyResultDetail } from '@/api/survey';
import html2canvas from 'html2canvas';

interface DiagnosisDetailModalProps {
  open: boolean;
  onClose: () => void;
  selectedResult: SurveyResultDetail | null;
  onDelete?: (resultId: number, resultName: string) => void;
  showDeleteButton?: boolean;
}

/**
 * 진단 결과 상세보기 모달 컴포넌트 - 이미지 다운로드 최적화
 */
const DiagnosisDetailModal: React.FC<DiagnosisDetailModalProps> = ({
  open,
  onClose,
  selectedResult,
  onDelete,
  showDeleteButton = true,
}) => {
  const [isDownloading, setIsDownloading] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  // 모달 닫기 - 컴포넌트 초기화
  const handleClose = () => {
    onClose();
  };

  // 진단 기록 삭제
  const handleDelete = () => {
    if (selectedResult && onDelete) {
      onDelete(
        selectedResult.id,
        selectedResult.result_name || `${selectedResult.result_tone.toUpperCase()} 타입`
      );
      handleClose();
    }
  };

  // 간단한 이미지 다운로드 핸들러
  const handleDownloadImage = async () => {
    if (!selectedResult || !contentRef.current) return;
    
    setIsDownloading(true);
    try {
      // 매우 기본적인 html2canvas 설정으로 oklch 문제 회피
      const canvas = await html2canvas(contentRef.current, {
        backgroundColor: '#ffffff',
        scale: 1,
        useCORS: true,
        allowTaint: true,
        logging: false,
        removeContainer: true,
        foreignObjectRendering: false,
      });

      // 이미지로 변환 및 다운로드
      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.download = `personal-color-diagnosis-${selectedResult.id}-${new Date().toISOString().slice(0, 10)}.png`;
          link.href = url;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
          message.success('진단 결과 이미지가 다운로드되었습니다!');
        }
      }, 'image/png', 0.95);
      
    } catch (error: any) {
      console.error('이미지 다운로드 오류:', error);
      message.error('이미지 다운로드 중 오류가 발생했습니다.');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <Modal
      title="진단 결과 상세"
      open={open}
      onCancel={handleClose}
      footer={[
        ...(showDeleteButton && onDelete ? [
          <Button
            key="delete"
            danger
            icon={<DeleteOutlined />}
            onClick={handleDelete}
          >
            삭제
          </Button>
        ] : []),
        <Button
          key="download"
          type="primary"
          icon={<DownloadOutlined />}
          onClick={handleDownloadImage}
          loading={isDownloading}
          style={{ backgroundColor: '#3b82f6', borderColor: '#3b82f6' }}
        >
          {isDownloading ? '다운로드 중...' : '이미지 다운로드'}
        </Button>,
        <Button key="close" onClick={handleClose}>
          닫기
        </Button>,
      ]}
      width={700}
    >
      {selectedResult && (
        <div 
          ref={contentRef} 
          style={{
            backgroundColor: '#ffffff',
            color: '#000000',
            padding: '20px',
            fontFamily: 'Arial, sans-serif'
          }}
        >
          {/* 진단 결과 헤더 */}
          <div style={{ textAlign: 'center', marginBottom: '30px' }}>
            <h2 style={{ 
              fontSize: '24px', 
              fontWeight: 'bold', 
              color: '#6366f1', 
              marginBottom: '8px',
              margin: '0 0 8px 0'
            }}>
              🎨 퍼스널 컬러 진단 결과
            </h2>
            <p style={{ color: '#6b7280', margin: '0' }}>
              분석일: {selectedResult.created_at 
                ? formatKoreanDate(selectedResult.created_at, true) 
                : '분석 완료'}
            </p>
          </div>

          {/* 메인 결과 타입 */}
          {selectedResult.top_types && selectedResult.top_types.length > 0 && (
            <div style={{ marginBottom: '20px' }}>
              {selectedResult.top_types.slice(0, 1).map((typeData: any, index: number) => {
                const typeNames: Record<string, { name: string; emoji: string; color: string }> = {
                  spring: { name: '봄 웜톤', emoji: '🌸', color: '#fab1a0' },
                  summer: { name: '여름 쿨톤', emoji: '💎', color: '#a8e6cf' },
                  autumn: { name: '가을 웜톤', emoji: '🍂', color: '#d4a574' },
                  winter: { name: '겨울 쿨톤', emoji: '❄️', color: '#74b9ff' },
                };
                const typeInfo = typeNames[typeData.type] || typeNames.spring;

                return (
                  <div
                    key={index}
                    style={{
                      background: `linear-gradient(135deg, ${typeInfo.color}, ${typeInfo.color}aa)`,
                      color: '#000000',
                      padding: '20px',
                      borderRadius: '12px',
                      textAlign: 'center',
                      marginBottom: '20px'
                    }}
                  >
                    <h3 style={{ 
                      fontSize: '20px', 
                      fontWeight: 'bold', 
                      margin: '0 0 8px 0',
                      color: '#000000'
                    }}>
                      {typeInfo.emoji} {typeData.name}
                    </h3>
                    <p style={{ 
                      fontSize: '14px', 
                      margin: '0',
                      color: '#000000'
                    }}>
                      {typeData.description}
                    </p>
                  </div>
                );
              })}

              {/* 컬러 팔레트 */}
              {selectedResult.top_types[0]?.color_palette && (
                <div style={{ marginBottom: '20px' }}>
                  <h4 style={{ 
                    color: '#374151', 
                    marginBottom: '12px',
                    fontSize: '16px',
                    fontWeight: 'bold'
                  }}>
                    🎨 당신만의 컬러 팔레트
                  </h4>
                  <div style={{ 
                    display: 'flex', 
                    flexWrap: 'wrap', 
                    justifyContent: 'center', 
                    gap: '12px' 
                  }}>
                    {selectedResult.top_types[0].color_palette.slice(0, 8).map((color: string, colorIndex: number) => (
                      <div key={colorIndex} style={{ textAlign: 'center' }}>
                        <div
                          style={{
                            width: '48px',
                            height: '48px',
                            backgroundColor: color,
                            borderRadius: '50%',
                            border: '2px solid #ffffff',
                            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                            margin: '0 auto 4px'
                          }}
                        />
                        <span style={{ 
                          fontSize: '11px', 
                          color: '#6b7280',
                          display: 'block'
                        }}>
                          {color}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 스타일 키워드 */}
              {selectedResult.top_types[0]?.style_keywords && selectedResult.top_types[0].style_keywords.length > 0 && (
                <div style={{ marginBottom: '20px' }}>
                  <h4 style={{ 
                    color: '#374151', 
                    marginBottom: '12px',
                    fontSize: '16px',
                    fontWeight: 'bold'
                  }}>
                    ✨ 스타일 키워드
                  </h4>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {selectedResult.top_types[0].style_keywords.map((keyword: string, keywordIndex: number) => (
                      <span
                        key={keywordIndex}
                        style={{
                          background: '#e0e7ff',
                          color: '#3730a3',
                          padding: '4px 12px',
                          borderRadius: '16px',
                          fontSize: '12px',
                          fontWeight: '500'
                        }}
                      >
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* 메이크업 팁 */}
              {selectedResult.top_types[0]?.makeup_tips && selectedResult.top_types[0].makeup_tips.length > 0 && (
                <div style={{ marginBottom: '20px' }}>
                  <h4 style={{ 
                    color: '#374151', 
                    marginBottom: '12px',
                    fontSize: '16px',
                    fontWeight: 'bold'
                  }}>
                    💄 메이크업 팁
                  </h4>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {selectedResult.top_types[0].makeup_tips.map((tip: string, tipIndex: number) => (
                      <span
                        key={tipIndex}
                        style={{
                          background: '#fee2e2',
                          color: '#991b1b',
                          padding: '4px 12px',
                          borderRadius: '16px',
                          fontSize: '12px',
                          fontWeight: '500'
                        }}
                      >
                        {tip}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* AI 상세 분석 */}
          {selectedResult.detailed_analysis && (
            <div style={{ marginTop: '20px' }}>
              <h4 style={{ 
                color: '#374151', 
                marginBottom: '12px',
                fontSize: '16px',
                fontWeight: 'bold'
              }}>
                🤖 AI 상세 분석
              </h4>
              <div style={{
                background: 'linear-gradient(135deg, #f3e8ff 0%, #fce7f3 100%)',
                padding: '16px',
                borderRadius: '8px',
                borderLeft: '4px solid #8b5cf6'
              }}>
                <p style={{ 
                  color: '#374151', 
                  lineHeight: '1.6',
                  margin: '0',
                  whiteSpace: 'pre-line'
                }}>
                  {selectedResult.detailed_analysis}
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
};

export default DiagnosisDetailModal;