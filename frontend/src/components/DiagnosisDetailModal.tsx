import React, { useState, useRef } from 'react';
import { formatKoreanDate } from '@/utils/dateUtils';
import {
  Modal,
  Button,
  message,
  Tooltip,
  Typography,
  Tabs,
  Tag,
  Divider,
} from 'antd';
import {
  DeleteOutlined,
  DownloadOutlined,
  TrophyOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import type { SurveyResultDetail } from '@/api/survey';
import type { PersonalColorType } from '@/types/personalColor';
import html2canvas from 'html2canvas';

const { Title, Text } = Typography;

interface DiagnosisDetailModalProps {
  open: boolean;
  onClose: () => void;
  selectedResult: SurveyResultDetail | null;
  onDelete?: (resultId: number, resultName: string) => void;
  showDeleteButton?: boolean;
  recentResults?: SurveyResultDetail[]; // 유니크 최신 리스트
}

/**
 * 진단 결과 상세보기 모달 컴포넌트 - MyPage 스타일 적용
 */
const DiagnosisDetailModal: React.FC<DiagnosisDetailModalProps> = ({
  open,
  onClose,
  selectedResult,
  onDelete,
  showDeleteButton = true,
  recentResults = [],
}) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const [activeTabKey, setActiveTabKey] = useState<string>('');

  // selectedResult가 변경될 때 해당 결과의 ID를 탭 키로 설정
  React.useEffect(() => {
    if (selectedResult) {
      setActiveTabKey(selectedResult.id ? String(selectedResult.id) : 'tab-0');
    } else {
      setActiveTabKey('');
    }
  }, [selectedResult]);

  const handleClose = () => {
    onClose();
  };

  const handleColorCopy = (color: string) => {
    navigator.clipboard.writeText(color);
    message.success(`${color} 복사됨!`);
  };

  const handleDownloadImage = async () => {
    if (!contentRef.current || !selectedResult) return;

    try {
      message.loading('이미지를 생성하는 중...', 0);

      // 완전히 새로운 DOM 생성 (CSS 클래스 없이)
      const createImageContent = () => {
        const container = document.createElement('div');
        container.style.cssText = `
          width: 600px;
          padding: 20px;
          background-color: #ffffff;
          font-family: 'Arial', sans-serif;
          color: #000000;
          line-height: 1.6;
          box-sizing: border-box;
        `;

        // 제목
        const header = document.createElement('div');
        header.style.cssText = `
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 24px;
        `;

        const titleSection = document.createElement('div');
        const titleIcon = document.createElement('span');
        titleIcon.textContent = '🏆';
        titleIcon.style.cssText = 'color: #eab308; margin-right: 8px;';

        const titleText = document.createElement('span');
        titleText.textContent = '퍼스널컬러 분석 결과';
        titleText.style.cssText = 'font-size: 18px; font-weight: bold; color: #000000;';

        titleSection.appendChild(titleIcon);
        titleSection.appendChild(titleText);

        const dateSection = document.createElement('div');
        const dateIcon = document.createElement('span');
        dateIcon.textContent = '📅';
        dateIcon.style.cssText = 'margin-right: 4px;';

        const dateText = document.createElement('span');
        dateText.textContent = formatKoreanDate(selectedResult.created_at, true);
        dateText.style.cssText = 'color: #6b7280; font-size: 14px;';

        dateSection.appendChild(dateIcon);
        dateSection.appendChild(dateText);

        header.appendChild(titleSection);
        header.appendChild(dateSection);
        container.appendChild(header);

        // 진단 결과
        if (selectedResult.top_types && selectedResult.top_types.length > 0) {
          selectedResult.top_types.slice(0, 3).forEach((typeData, index) => {
            const typeCard = document.createElement('div');
            typeCard.style.cssText = `
              margin-bottom: 20px;
              border-radius: 16px;
              overflow: hidden;
              box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            `;

            // 메인 카드
            const mainCard = document.createElement('div');
            mainCard.style.cssText = `
              padding: 16px;
              text-align: center;
              color: #ffffff;
            `;

            // 타입별 배경색 설정
            if (typeData.type === 'spring') {
              mainCard.style.background = 'linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%)';
              mainCard.style.color = '#2d3436';
            } else if (typeData.type === 'summer') {
              mainCard.style.background = 'linear-gradient(135deg, #a8e6cf 0%, #dcedc8 100%)';
              mainCard.style.color = '#2d3436';
            } else if (typeData.type === 'autumn') {
              mainCard.style.background = 'linear-gradient(135deg, #d4a574 0%, #8b4513 100%)';
              mainCard.style.color = '#ffffff';
            } else if (typeData.type === 'winter') {
              mainCard.style.background = 'linear-gradient(135deg, #74b9ff 0%, #0984e3 100%)';
              mainCard.style.color = '#ffffff';
            }

            const typeTitle = document.createElement('h3');
            typeTitle.style.cssText = `
              margin: 0 0 8px 0;
              font-size: 20px;
              font-weight: bold;
            `;
            typeTitle.textContent = `${index === 0 ? '🏆 ' : ''}${typeData.name}`;

            const typeDesc = document.createElement('p');
            typeDesc.style.cssText = `
              margin: 0;
              font-size: 14px;
              opacity: 0.9;
            `;
            typeDesc.textContent = typeData.description || '';

            mainCard.appendChild(typeTitle);
            if (typeData.description) {
              mainCard.appendChild(typeDesc);
            }
            typeCard.appendChild(mainCard);

            // 컬러 팔레트
            if (typeData.color_palette && typeData.color_palette.length > 0) {
              const paletteSection = document.createElement('div');
              paletteSection.style.cssText = `
                padding: 16px;
                background-color: #ffffff;
                border-top: 1px solid #f0f0f0;
              `;

              const paletteTitle = document.createElement('p');
              paletteTitle.style.cssText = `
                margin: 0 0 12px 0;
                font-weight: bold;
                color: #374151;
                font-size: 14px;
              `;
              paletteTitle.textContent = '🎨 당신만의 컬러 팔레트';

              const paletteGrid = document.createElement('div');
              paletteGrid.style.cssText = `
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 12px;
                margin-bottom: 12px;
              `;

              typeData.color_palette.slice(0, 8).forEach(color => {
                const colorItem = document.createElement('div');
                colorItem.style.cssText = 'text-align: center;';

                const colorCircle = document.createElement('div');
                colorCircle.style.cssText = `
                  width: 40px;
                  height: 40px;
                  border-radius: 50%;
                  margin: 0 auto 4px auto;
                  background-color: ${color === '#ffffff' ? '#f5f5f5' : color};
                  border: 2px solid ${color === '#ffffff' ? '#d9d9d9' : '#ffffff'};
                  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                `;

                const colorLabel = document.createElement('div');
                colorLabel.style.cssText = `
                  font-size: 10px;
                  color: #6b7280;
                `;
                colorLabel.textContent = color;

                colorItem.appendChild(colorCircle);
                colorItem.appendChild(colorLabel);
                paletteGrid.appendChild(colorItem);
              });

              paletteSection.appendChild(paletteTitle);
              paletteSection.appendChild(paletteGrid);
              typeCard.appendChild(paletteSection);
            }

            // 스타일 키워드
            if (typeData.style_keywords && typeData.style_keywords.length > 0) {
              const keywordsSection = document.createElement('div');
              keywordsSection.style.cssText = `
                padding: 16px;
                background-color: #fafafa;
                border-top: 1px solid #f0f0f0;
              `;

              const keywordsTitle = document.createElement('p');
              keywordsTitle.style.cssText = `
                margin: 0 0 8px 0;
                font-weight: bold;
                color: #374151;
                font-size: 14px;
              `;
              keywordsTitle.textContent = '✨ 스타일 키워드';

              const keywordsContainer = document.createElement('div');
              keywordsContainer.style.cssText = `
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
              `;

              typeData.style_keywords.forEach(keyword => {
                const keywordTag = document.createElement('span');
                keywordTag.style.cssText = `
                  padding: 0px 7px 5px 7px;
                  background-color: #f0f5ff;
                  color: #1d39c4;
                  border-radius: 4px;
                  border: 1px solid #adc6ff;
                  font-size: 12px;
                `;
                keywordTag.textContent = keyword;
                keywordsContainer.appendChild(keywordTag);
              });

              keywordsSection.appendChild(keywordsTitle);
              keywordsSection.appendChild(keywordsContainer);
              typeCard.appendChild(keywordsSection);
            }

            // 메이크업 팁
            if (typeData.makeup_tips && typeData.makeup_tips.length > 0) {
              const tipsSection = document.createElement('div');
              tipsSection.style.cssText = `
                padding: 16px;
                background-color: #fef7f0;
                border-top: 1px solid #f0f0f0;
              `;

              const tipsTitle = document.createElement('p');
              tipsTitle.style.cssText = `
                margin: 0 0 8px 0;
                font-weight: bold;
                color: #374151;
                font-size: 14px;
              `;
              tipsTitle.textContent = '💄 메이크업 팁';

              const tipsContainer = document.createElement('div');
              tipsContainer.style.cssText = `
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
              `;

              typeData.makeup_tips.forEach(tip => {
                const tipTag = document.createElement('span');
                tipTag.style.cssText = `
                  padding: 0px 7px 5px 7px;
                  background-color: #fff2e8;
                  color: #d4380d;
                  border-radius: 4px;
                  border: 1px solid #ffbb96;
                  font-size: 12px;
                `;
                tipTag.textContent = tip;
                tipsContainer.appendChild(tipTag);
              });

              tipsSection.appendChild(tipsTitle);
              tipsSection.appendChild(tipsContainer);
              typeCard.appendChild(tipsSection);
            }

            container.appendChild(typeCard);
          });
        }

        // 상세 분석
        if (selectedResult.detailed_analysis) {
          const analysisSection = document.createElement('div');
          analysisSection.style.cssText = `
            margin-top: 20px;
            padding: 16px;
            background: linear-gradient(135deg, #fef7ff 0%, #fdf2f8 100%);
            border-radius: 8px;
            border: 1px solid #e5e7eb;
          `;

          const analysisTitle = document.createElement('h4');
          analysisTitle.style.cssText = `
            margin: 0 0 12px 0;
            font-size: 16px;
            font-weight: bold;
            color: #374151;
          `;
          analysisTitle.textContent = 'AI 상세 분석';

          const analysisContent = document.createElement('p');
          analysisContent.style.cssText = `
            margin: 0;
            color: #4b5563;
            line-height: 1.6;
            white-space: pre-line;
          `;
          analysisContent.textContent = selectedResult.detailed_analysis;

          analysisSection.appendChild(analysisTitle);
          analysisSection.appendChild(analysisContent);
          container.appendChild(analysisSection);
        }

        return container;
      };

      const imageContent = createImageContent();

      // 임시 컨테이너에 추가
      const tempContainer = document.createElement('div');
      tempContainer.style.cssText = `
        position: absolute;
        top: -9999px;
        left: -9999px;
        width: 600px;
      `;
      tempContainer.appendChild(imageContent);
      document.body.appendChild(tempContainer);

      const canvas = await html2canvas(imageContent, {
        backgroundColor: '#ffffff',
        scale: 2,
        useCORS: true,
        allowTaint: true,
        logging: false,
        width: 600,
        height: imageContent.offsetHeight
      });

      // 임시 컨테이너 제거
      document.body.removeChild(tempContainer);

      message.destroy();

      const link = document.createElement('a');
      link.download = `퍼스널컬러_진단결과_${selectedResult.result_name || selectedResult.result_tone}_${new Date().getTime()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();

      message.success('이미지가 다운로드되었습니다!');
    } catch (error) {
      message.destroy();
      console.error('이미지 다운로드 실패:', error);
      message.error('이미지 다운로드에 실패했습니다.');
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
            onClick={() => {
              if (selectedResult) {
                onDelete(
                  selectedResult.id,
                  selectedResult.result_name ||
                  `${selectedResult.result_tone.toUpperCase()} 타입`
                );
                handleClose();
              }
            }}
          >
            삭제
          </Button>
        ] : []),
        <Button
          key="download"
          type="primary"
          icon={<DownloadOutlined />}
          onClick={handleDownloadImage}
        >
          이미지 저장
        </Button>,
        <Button key="close" onClick={handleClose}>
          닫기
        </Button>,
      ]}
      width={700}
    >
      {selectedResult ? (
        <div
          ref={contentRef}
          className="space-y-6 py-2"
          style={{
            backgroundColor: '#ffffff',
            color: '#000000',
            padding: '20px',
            fontFamily: 'Arial, sans-serif',
          }}
        >
          {/* Top Types 결과 - Tabs UI (recentResults 기반) */}
          {recentResults && recentResults.length > 0 ? (
            <div>
              <div className="flex justify-between">
                <Title level={5} className="mb-4 flex items-center">
                  <TrophyOutlined className="mr-2 text-yellow-500" />
                  퍼스널컬러 분석 결과
                </Title>
              </div>
              <Tabs
                activeKey={activeTabKey}
                onChange={setActiveTabKey}
                items={recentResults.slice(0, 3).map((result, index) => {
                  const isRecommended = index === 0;
                  
                  // 11가지 퍼스널컬러 타입 정의
                  const typeNames: Record<string, { name: string; emoji: string; color: string }> = {
                    // Spring
                    spring: { name: '봄 웜톤', emoji: '🌸', color: '#fab1a0' },
                    spring_light: { name: '봄 라이트', emoji: '🌼', color: '#fff5ba' },
                    spring_true: { name: '봄 트루', emoji: '🍑', color: '#ffb7b2' },
                    spring_bright: { name: '봄 브라이트', emoji: '🌺', color: '#ff9ff3' },
                    // Summer
                    summer: { name: '여름 쿨톤', emoji: '💎', color: '#a8e6cf' },
                    summer_light: { name: '여름 라이트', emoji: '☁️', color: '#dff9fb' },
                    summer_true: { name: '여름 트루', emoji: '🍧', color: '#74b9ff' },
                    summer_mute: { name: '여름 뮤트', emoji: '🌫️', color: '#b2bec3' },
                    // Autumn
                    autumn: { name: '가을 웜톤', emoji: '🍂', color: '#d4a574' },
                    autumn_soft: { name: '가을 소프트', emoji: '🌾', color: '#e1b12c' },
                    autumn_deep: { name: '가을 딥', emoji: '🍁', color: '#a0522d' },
                    // Winter
                    winter: { name: '겨울 쿨톤', emoji: '❄️', color: '#74b9ff' },
                    winter_bright: { name: '겨울 브라이트', emoji: '✨', color: '#00cec9' },
                    winter_true: { name: '겨울 트루', emoji: '🧊', color: '#0984e3' },
                    winter_deep: { name: '겨울 딥', emoji: '🌌', color: '#2d3436' },
                  };

                  const allBackgrounds: Record<string, { background: string; color: string }> = {
                    // Spring
                    spring: { background: 'linear-gradient(135deg, #ffeaa7 0%, #fab1a0 100%)', color: '#2d3436' },
                    spring_light: { background: 'linear-gradient(135deg, #fff5ba 0%, #ffcccc 100%)', color: '#2d3436' },
                    spring_true: { background: 'linear-gradient(135deg, #fab1a0 0%, #ff7675 100%)', color: '#2d3436' },
                    spring_bright: { background: 'linear-gradient(135deg, #ff9ff3 0%, #feca57 100%)', color: '#2d3436' },
                    // Summer
                    summer: { background: 'linear-gradient(135deg, #a8e6cf 0%, #dcedc8 100%)', color: '#2d3436' },
                    summer_light: { background: 'linear-gradient(135deg, #dff9fb 0%, #c7ecee 100%)', color: '#2d3436' },
                    summer_true: { background: 'linear-gradient(135deg, #74b9ff 0%, #a29bfe 100%)', color: '#ffffff' },
                    summer_mute: { background: 'linear-gradient(135deg, #b2bec3 0%, #636e72 100%)', color: '#ffffff' },
                    // Autumn
                    autumn: { background: 'linear-gradient(135deg, #d4a574 0%, #8b4513 100%)', color: '#ffffff' },
                    autumn_soft: { background: 'linear-gradient(135deg, #e1b12c 0%, #cd6133 100%)', color: '#ffffff' },
                    autumn_deep: { background: 'linear-gradient(135deg, #a0522d 0%, #800000 100%)', color: '#ffffff' },
                    // Winter
                    winter: { background: 'linear-gradient(135deg, #74b9ff 0%, #0984e3 100%)', color: '#ffffff' },
                    winter_bright: { background: 'linear-gradient(135deg, #00cec9 0%, #6c5ce7 100%)', color: '#ffffff' },
                    winter_true: { background: 'linear-gradient(135deg, #0984e3 0%, #00cec9 100%)', color: '#ffffff' },
                    winter_deep: { background: 'linear-gradient(135deg, #2d3436 0%, #636e72 100%)', color: '#ffffff' },
                  };

                  // 톤 키 정규화 함수
                  const getNormalizedKey = (r: SurveyResultDetail): string => {
                    const text = (r.result_name || r.result_tone).toLowerCase().replace(/\s+/g, '_');
                    
                    if (text.includes('spring') || text.includes('봄')) {
                      if (text.includes('light') || text.includes('라이트')) return 'spring_light';
                      if (text.includes('bright') || text.includes('브라이트')) return 'spring_bright';
                      if (text.includes('true') || text.includes('트루')) return 'spring_true';
                      return 'spring';
                    }
                    if (text.includes('summer') || text.includes('여름')) {
                      if (text.includes('light') || text.includes('라이트')) return 'summer_light';
                      if (text.includes('mute') || text.includes('뮤트') || text.includes('soft') || text.includes('소프트')) return 'summer_mute';
                      if (text.includes('true') || text.includes('트루')) return 'summer_true';
                      return 'summer';
                    }
                    if (text.includes('autumn') || text.includes('가을')) {
                      if (text.includes('mute') || text.includes('뮤트') || text.includes('soft') || text.includes('소프트')) return 'autumn_soft';
                      if (text.includes('deep') || text.includes('딥')) return 'autumn_deep';
                      return 'autumn';
                    }
                    if (text.includes('winter') || text.includes('겨울')) {
                      if (text.includes('bright') || text.includes('브라이트')) return 'winter_bright';
                      if (text.includes('deep') || text.includes('딥') || text.includes('dark') || text.includes('다크')) return 'winter_deep';
                      if (text.includes('true') || text.includes('트루')) return 'winter_true';
                      return 'winter';
                    }
                    return 'spring';
                  };

                  const normalizedKey = getNormalizedKey(result);
                  const typeInfo = typeNames[normalizedKey] || typeNames.spring;
                  const displayStyle = allBackgrounds[normalizedKey] || allBackgrounds.spring;

                  return {
                    key: result.id ? String(result.id) : `tab-${index}`,
                    label: (
                      <div className="flex items-center px-2 gap-1">
                        {isRecommended && (
                          <Tag color="gold" className="ml-1 text-xs">추천</Tag>
                        )}
                        <span className="mr-1">{typeInfo.emoji}</span>
                        <span className={isRecommended ? 'text-purple-600' : ''}>{result.result_name || typeInfo.name}</span>
                      </div>
                    ),
                    children: (
                      <div className="space-y-4">
                        {/* 생성 일자 */}
                        <Text className="!text-gray-500 flex items-center justify-end">
                          <CalendarOutlined className="mr-1" />
                          {formatKoreanDate(result.created_at, true)}
                        </Text>
                        {/* 메인 타입 카드 */}
                        <div className="p-4 rounded-2xl text-center transition-all duration-300" style={{ background: displayStyle.background, color: displayStyle.color }}>
                          <Title level={3} style={{ color: displayStyle.color, margin: 0 }}>{result.result_name || typeInfo.name}</Title>
                          <Text style={{ color: displayStyle.color, fontSize: '14px', display: 'block', marginTop: '8px' }}>{result.result_description}</Text>
                        </div>
                        {/* 컬러 팔레트 */}
                        {result.color_palette && result.color_palette.length > 0 && (
                          <div>
                            <Text strong className="!text-gray-700 block mb-2 text-sm">🎨 당신만의 컬러 팔레트</Text>
                            <div className="flex flex-wrap justify-center gap-3 mb-3">
                              {result.color_palette.slice(0, 8).map((color, colorIndex) => {
                                const isWhite = color.toLowerCase() === '#ffffff';
                                return (
                                  <Tooltip key={colorIndex} title={`${color} 복사`} placement="top">
                                    <div className="cursor-pointer transition-transform hover:scale-110 active:scale-95 group" onClick={() => handleColorCopy(color)}>
                                      <div className="w-12 h-12 rounded-full border-2 border-white shadow-lg group-hover:shadow-xl transition-shadow" style={{ backgroundColor: isWhite ? '#f5f5f5' : color, borderColor: isWhite ? '#d9d9d9' : '#ffffff' }} />
                                      <Text className="text-xs text-center block mt-1 !text-gray-600">{color}</Text>
                                    </div>
                                  </Tooltip>
                                );
                              })}
                            </div>
                          </div>
                        )}
                        {/* 스타일 키워드 */}
                        {result.style_keywords && result.style_keywords.length > 0 && (
                          <div>
                            <Text strong className="!text-gray-700 block mb-2 text-sm">✨ 스타일 키워드</Text>
                            <div className="flex flex-wrap gap-2">
                              {result.style_keywords.map((keyword, keywordIndex) => (
                                <Tag key={keywordIndex} color="geekblue">{keyword}</Tag>
                              ))}
                            </div>
                          </div>
                        )}
                        {/* 메이크업 팁 */}
                        {result.makeup_tips && result.makeup_tips.length > 0 && (
                          <div>
                            <Text strong className="!text-gray-700 block mb-2 text-sm">💄 메이크업 팁</Text>
                            <div className="flex flex-wrap gap-2">
                              {result.makeup_tips.map((tip, tipIndex) => (
                                <Tag key={tipIndex} color="volcano">{tip}</Tag>
                              ))}
                            </div>
                          </div>
                        )}
                        {/* 상세 분석 */}
                        {result.detailed_analysis && (
                          <div>
                            <Divider />
                            <Title level={5} className="mb-3">AI 상세 분석</Title>
                            <div className="bg-gradient-to-r from-purple-50 to-pink-50 p-4 rounded-lg">
                              <Text className="!text-gray-700 leading-relaxed whitespace-pre-line">{result.detailed_analysis}</Text>
                            </div>
                          </div>
                        )}
                      </div>
                    ),
                  };
                })}
                className="mb-4"
              />
            </div>
          ) : (
            <div className="text-center text-gray-400 py-8">
              진단 결과 데이터가 없습니다.
            </div>
          )}
          {/* 컬러 팔레트 (기존 코드 유지하되 top_types가 있을 때는 숨김) */}
          {selectedResult.color_palette && selectedResult.color_palette.length > 0 && (!selectedResult.top_types || selectedResult.top_types.length === 0) && (
            <div>
              <Title level={5} className="mb-3">추천 컬러 팔레트</Title>
              <div className="flex flex-wrap gap-2">
                {selectedResult.color_palette.map((color, index) => (
                  <div key={index} className="flex items-center bg-white border rounded-lg p-2 shadow-sm">
                    <div className="w-6 h-6 rounded mr-2 border" style={{ backgroundColor: color }} />
                    <Text className="text-sm">{color}</Text>
                  </div>
                ))}
              </div>
            </div>
          )}
          {/* 스타일 키워드 (기존 코드 유지하되 top_types가 있을 때는 숨김) */}
          {selectedResult.style_keywords && selectedResult.style_keywords.length > 0 && (!selectedResult.top_types || selectedResult.top_types.length === 0) && (
            <div>
              <Title level={5} className="mb-3">스타일 키워드</Title>
              <div className="flex flex-wrap gap-2">
                {selectedResult.style_keywords.map((keyword, index) => (
                  <Tag key={index} color="geekblue">{keyword}</Tag>
                ))}
              </div>
            </div>
          )}
          {/* 메이크업 팁 (기존 코드 유지하되 top_types가 있을 때는 숨김) */}
          {selectedResult.makeup_tips && selectedResult.makeup_tips.length > 0 && (!selectedResult.top_types || selectedResult.top_types.length === 0) && (
            <div>
              <Title level={5} className="mb-3">메이크업 팁</Title>
              <div className="flex flex-wrap gap-2">
                {selectedResult.makeup_tips.map((tip, index) => (
                  <Tag key={index} color="volcano">{tip}</Tag>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center text-gray-400 py-8">진단 결과 데이터가 없습니다.</div>
      )}
    </Modal>
  );
};

export default DiagnosisDetailModal;