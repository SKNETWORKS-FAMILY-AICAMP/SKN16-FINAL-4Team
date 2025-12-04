import requests
from bs4 import BeautifulSoup
import json
import os
from urllib.parse import urljoin, urlparse
import time
from pathlib import Path
import random
import mimetypes
import logging

# 로거 설정 (상위에서 기본 로깅 설정을 기대)
logger = logging.getLogger(__name__)

# ==============================================================================
# 1. 클래스 정의 및 초기화
# ==============================================================================

class VogueKoreaScraper:
    """
    Vogue Korea 웹사이트에서 패션/뷰티 트렌드 기사 목록, 상세 내용 및 이미지를 스크래핑하고
    RAG 시스템 구축을 위해 JSON 및 개별 텍스트 파일로 저장하는 클래스입니다.
    """
    def __init__(self, category="fashion"):
        """
        category: "fashion" 또는 "beauty"
        """
        self.category = category
        
        # 카테고리별 URL 설정
        if category == "fashion":
            self.base_url = "https://www.vogue.co.kr/fashion/fashion-trend/"
            self.category_name = "패션 트렌드"
        elif category == "beauty":
            self.base_url = "https://www.vogue.co.kr/beauty/beauty-trend/"
            self.category_name = "뷰티 트렌드"
        else:
            raise ValueError("category는 'fashion' 또는 'beauty'만 가능합니다.")
        
        self.headers = {
            # 봇으로 인식되지 않도록 사용자 에이전트 설정
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        # 세션 유지를 통해 요청 효율성 증대
        self.session = requests.Session()
        
        # 파일 저장 경로 설정 (pathlib 사용으로 OS 독립적인 경로 관리)
        # 카테고리별로 폴더 분리
        self.output_dir = Path(__file__).parent.parent.parent / "data" / "RAG" / "mutable" / f"vogue_{category}"
        self.images_dir = self.output_dir / "images"
        
        # 출력 디렉토리 자동 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"출력 디렉토리 준비 완료 ({self.category_name}): {self.output_dir}")
    
    # ==============================================================================
    # 2. 기사 링크 추출 (목록 페이지)
    # ==============================================================================
    
    def get_article_links(self, max_articles=20):
        """메인 페이지에서 기사 링크 추출"""
        logger.info(f"메인 페이지 크롤링 중: {self.base_url}")
        
        try:
            response = self.session.get(self.base_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            articles = []
            
            # 기사 목록에서 링크 추출 (기존의 안정적인 셀렉터 유지)
            article_items = soup.select('#post_list li')
            
            for item in article_items:
                if len(articles) >= max_articles:
                    break
                    
                link_tag = item.select_one('a')
                title_tag = item.select_one('h3.s_tit')
                category_tag = item.select_one('p.category')
                date_tag = item.select_one('p.date')
                
                if link_tag and title_tag:
                    # 상대 경로를 절대 URL로 변환하여 안전성 확보
                    article_url = urljoin(self.base_url, link_tag['href'])
                    
                    article_info = {
                        'title': title_tag.text.strip(),
                        'url': article_url,
                        'category': category_tag.text.strip() if category_tag else '',
                        'date': date_tag.text.strip() if date_tag else ''
                    }
                    
                    articles.append(article_info)
                    logger.info(f"발견: {article_info['title']}")
            
            logger.info(f"\n총 {len(articles)}개의 기사 링크를 발견했습니다.")
            return articles
            
        except Exception as e:
            logger.error(f"메인 페이지 크롤링 오류: {e}")
            return []
    
    # ==============================================================================
    # 3. 이미지 다운로드 (개선 사항 2 반영: URLjoin 및 Content-Type 확장자 확인)
    # ==============================================================================
    
    def download_image(self, img_url, article_id, img_index, article_url):
        """
        이미지 다운로드 및 저장.
        - urljoin을 사용하여 상대 URL 처리 안정화.
        - Content-Type 헤더를 통해 정확한 확장자 추정.
        """
        try:
            # 상대 경로를 절대 URL로 변환하여 안전성 확보
            # (개선 사항 2.1 반영)
            img_url = urljoin(article_url, img_url)

            # data: URL이나 placeholder 이미지 건너뛰기
            if img_url.startswith('data:') or 'placeholder' in img_url.lower():
                return None
            
            # 스트림을 사용하여 큰 파일 처리 및 10초 타임아웃 설정
            response = self.session.get(img_url, headers=self.headers, timeout=10, stream=True)
            response.raise_for_status()
            
            # (개선 사항 2.2 반영) Content-Type으로 확장자 추정
            content_type = response.headers.get('Content-Type')
            ext = mimetypes.guess_extension(content_type.split(';')[0].strip()) if content_type else None
            
            # 파일 경로의 확장자나 기본 확장자(.jpg)로 대체
            if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
                path_ext = os.path.splitext(urlparse(img_url).path)[1].lower()
                if path_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
                    ext = path_ext
                else:
                    ext = '.jpg'
            
            # 파일명 생성
            filename = f"{article_id}_img_{img_index}{ext}"
            filepath = self.images_dir / filename
            
            # 이미지 저장
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"  이미지 저장: {filename}")
            # RAG 텍스트 파일에 저장할 때 로컬 경로를 문자열로 반환
            return str(filepath)
            
        except Exception as e:
            # 실패해도 전체 크롤링은 계속 진행
            logger.warning(f"  이미지 다운로드 실패 ({img_url}): {e}")
            return None
    
    # ==============================================================================
    # 4. 개별 기사 상세 내용 크롤링 (개선 사항 1, 3 반영: 셀렉터 안정화 및 메타데이터 추가)
    # ==============================================================================
    
    def scrape_article(self, article_info):
        """개별 기사 상세 내용 크롤링 및 데이터 구조화"""
        url = article_info['url']
        logger.info(f"\n기사 크롤링 중: {article_info['title']}")
        
        try:
            response = self.session.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # URL 기반으로 기사 ID 생성
            article_id = Path(urlparse(url).path).name
            if not article_id:
                 # URL이 '/'로 끝날 경우를 대비하여 한 단계 위의 경로 사용
                article_id = url.rstrip('/').split('/')[-1]
                
            article_id = article_id.replace('%', '_').replace('.', '_')[:50]
            
            # (개선 사항 1 반영) 기사 본문 영역 셀렉터 리스트 (안정성 강화)
            article_body_selectors = [
                '.article_view .article_body', # 가장 일반적인 셀렉터
                '.entry-content',
                'article',
                '.post-content'
            ]

            article_body = None
            for selector in article_body_selectors:
                article_body = soup.select_one(selector)
                if article_body:
                    break
            
            if not article_body:
                logger.warning("  경고: 기사 본문 영역을 찾을 수 없습니다. (article_body is None)")
                content = "ERROR: 본문 추출 실패"
            else:
                content_parts = []
                
                # 서브타이틀이나 리드 텍스트 추출 (기사 본문 앞에 배치)
                subtitle = soup.select_one('.article_view .subtitle, .article_view .lead')
                if subtitle:
                    content_parts.append(subtitle.get_text(strip=True))
                
                # (개선 사항 3 반영) 본문 내용 추출 및 필터링
                paragraphs = article_body.find_all(['p', 'h2', 'h3', 'h4', 'li', 'blockquote'])
                
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    # 짧은 텍스트 필터링 (10자 미만 텍스트나 광고 관련 텍스트 필터링)
                    if text and len(text) > 10 and not any(k in text.lower() for k in ['광고', '협찬', '문의']): 
                        content_parts.append(text)
                        
                content = '\n\n'.join(content_parts)


            # 이미지 추출 및 다운로드
            images = []
            image_tags = article_body.find_all('img') if article_body else []
            
            for idx, img in enumerate(image_tags, 1):
                # data-src 속성 우선 확인 (lazy loading 대응)
                img_url = img.get('data-src') or img.get('src')
                
                if img_url:
                    # 다운로드 함수에 현재 기사 URL을 전달하여 urljoin이 작동하도록 함
                    local_path = self.download_image(img_url, article_id, idx, url)
                    if local_path:
                        images.append({
                            'url': img_url,
                            'local_path': local_path,
                            'alt': img.get('alt', ''),
                            'caption': img.get('caption', '')
                        })
            
            # 저자 정보
            author = ''
            author_tag = soup.select_one('.author, .by_editor, .writer, [itemprop="author"] span, .article_view > p:contains("by")')
            if author_tag:
                author = author_tag.get_text(strip=True)
                
            # (개선 사항 3 반영) 키워드 / 태그 정보 추출
            keywords = []
            tag_section = soup.select_one('.tag_area, .tags')
            if tag_section:
                tag_links = tag_section.find_all('a')
                keywords = [a.get_text(strip=True) for a in tag_links if a.get_text(strip=True)]
            
            # 결과 데이터 구조화
            article_data = {
                'id': article_id,
                'title': article_info['title'],
                'url': url,
                'category': article_info['category'],
                'date': article_info['date'],
                'author': author,
                'keywords': keywords, # 추가된 메타데이터
                'content': content,
                'images': images,
                'image_count': len(images),
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"  본문 길이: {len(content)} 자")
            logger.info(f"  이미지 개수: {len(images)} 개")
            logger.info(f"  키워드: {', '.join(keywords)}")
            
            return article_data
            
        except Exception as e:
            logger.error(f"기사 크롤링 오류 ({url}): {e}")
            return None
    
    # ==============================================================================
    # 5. 데이터 저장 함수
    # ==============================================================================
    
    def get_existing_article_ids(self):
        """저장된 기사 ID 목록 반환 (중복 처리용)"""
        existing_ids = set()
        
        # 기존 텍스트 파일 확인
        for txt_file in self.output_dir.glob('*.txt'):
            if txt_file.name != '.gitkeep':  # 시스템 파일 제외
                article_id = txt_file.stem
                existing_ids.add(article_id)
        
        return existing_ids
    
    def save_to_json(self, articles_data, filename="vogue_articles.json"):
        """크롤링한 데이터를 JSON 파일로 저장"""
        filepath = self.output_dir / filename
        
        # 기존 데이터 있으면 로드해서 병합
        existing_data = {}
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data_list = json.load(f)
                    existing_data = {item['id']: item for item in existing_data_list}
                logger.info(f"기존 JSON 파일에서 {len(existing_data)}개의 기사 로드")
            except Exception as e:
                logger.warning(f"기존 JSON 로드 실패: {e}")
        
        # 새로운 데이터와 기존 데이터 병합 (새 데이터가 우선)
        for article in articles_data:
            existing_data[article['id']] = article
        
        # 병합된 데이터 저장
        merged_list = list(existing_data.values())
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(merged_list, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n데이터 저장 완료: {filepath}")
        logger.info(f"총 {len(merged_list)}개의 기사 저장 (신규: {len(articles_data)}개, 기존: {len(existing_data) - len(articles_data)}개)")
    
    def save_to_text(self, article_data, skip_existing=False):
        """
        개별 기사를 텍스트 파일로 저장 (RAG용)
        skip_existing=True일 경우 기존 파일이 있으면 스킵
        """
        filename = f"{article_data['id']}.txt"
        filepath = self.output_dir / filename
        
        # 기존 파일 확인 (스킵 옵션)
        if skip_existing and filepath.exists():
            logger.info(f"  [SKIP] 기존 파일 존재: {filename}")
            return False
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"제목: {article_data['title']}\n")
            f.write(f"URL: {article_data['url']}\n")
            f.write(f"카테고리: {article_data['category']}\n")
            f.write(f"날짜: {article_data['date']}\n")
            f.write(f"저자: {article_data['author']}\n")
            f.write(f"키워드: {', '.join(article_data['keywords'])}\n") # 추가된 메타데이터
            f.write(f"이미지 개수: {article_data['image_count']}\n")
            f.write("\n" + "="*80 + "\n\n")
            f.write(article_data['content'])
            
            if article_data['images']:
                f.write("\n\n" + "="*80 + "\n")
                f.write("이미지 정보:\n\n")
                for idx, img in enumerate(article_data['images'], 1):
                    # 로컬 경로만 참조하도록 업데이트
                    f.write(f"{idx}. 로컬 경로: {img['local_path']}\n")
                    if img['alt']:
                        f.write(f"  설명: {img['alt']}\n")
                    f.write(f"  원본 URL: {img['url']}\n\n")
        
        return True
    
    # ==============================================================================
    # 6. 전체 실행 로직 (개선 사항 4 반영: 랜덤 딜레이 적용)
    # ==============================================================================
    
    def run(self, max_articles=20, min_delay=1, max_delay=3, skip_existing=False):
        """
        전체 크롤링 실행 함수.
        min_delay와 max_delay 사이의 랜덤한 지연 시간을 적용하여 서버 부하를 줄임.
        
        Parameters:
        -----------
        max_articles: int
            크롤링할 최대 기사 수
        min_delay, max_delay: float
            요청 사이의 지연 시간 범위 (초)
        skip_existing: bool
            True일 경우 기존 파일이 있는 기사는 스킵하고 새로운 기사만 크롤링
            False일 경우 모든 기사를 다시 크롤링 (기존 파일 덮어쓰기)
        """
        logger.info("="*80)
        logger.info(f"보그 코리아 {self.category_name} 크롤링 시작")
        logger.info(f"중복 처리 방식: {'기존 파일 스킵' if skip_existing else '전체 재크롤링'}")
        logger.info("="*80)
        
        # 기존 기사 ID 확인
        existing_ids = self.get_existing_article_ids() if skip_existing else set()
        if existing_ids:
            logger.info(f"기존 기사 {len(existing_ids)}개 발견")
        
        # 1. 기사 목록 가져오기
        article_links = self.get_article_links(max_articles)
        
        if not article_links:
            logger.info("크롤링할 기사가 없습니다. 종료합니다.")
            return []
        
        # skip_existing=True인 경우 새로운 기사만 필터링
        if skip_existing:
            new_articles = [art for art in article_links 
                           if Path(urlparse(art['url']).path).name.replace('%', '_').replace('.', '_')[:50] 
                           not in existing_ids]
            
            if not new_articles:
                logger.info(f"\n모든 기사가 이미 크롤링되었습니다. 종료합니다.")
                return []
            
            logger.info(f"신규 기사: {len(new_articles)}개, 기존 기사: {len(article_links) - len(new_articles)}개")
            article_links = new_articles
        
        # 2. 각 기사 상세 내용 크롤링
        all_articles = []
        saved_count = 0
        skipped_count = 0
        
        for idx, article_info in enumerate(article_links, 1):
            logger.info(f"\n[{idx}/{len(article_links)}] 상세 크롤링 진행 중...")
            
            article_data = self.scrape_article(article_info)
            
            if article_data:
                all_articles.append(article_data)
                # 개별 텍스트 파일로 저장
                if self.save_to_text(article_data, skip_existing=skip_existing):
                    saved_count += 1
                else:
                    skipped_count += 1
            
            # (개선 사항 4 반영) 서버 부하 방지를 위한 랜덤 딜레이
            if idx < len(article_links):
                delay = random.uniform(min_delay, max_delay)
                logger.info(f"  다음 요청까지 랜덤 대기: {delay:.2f}초")
                time.sleep(delay)
        
        # 3. 전체 데이터를 JSON으로 저장
        if all_articles:
            self.save_to_json(all_articles)
            
            logger.info("\n" + "="*80)
            logger.info(f"크롤링 완료!")
            logger.info(f"총 {len(all_articles)}개의 기사를 수집했습니다.")
            if skip_existing:
                logger.info(f"  - 새로 저장: {saved_count}개")
                logger.info(f"  - 스킵: {skipped_count}개")
            logger.info(f"데이터 및 이미지 저장 위치: {self.output_dir}")
            logger.info("="*80)
            
        return all_articles


# ==============================================================================
# 7. 실행 예제
# ==============================================================================

if __name__ == "__main__":
    logger.info("="*80)
    logger.info("Vogue Korea 패션/뷰티 트렌드 크롤링 시작")
    logger.info("="*80)
    
    # 중복 처리 옵션
    # skip_existing=True: 기존 파일이 있는 기사는 스킵하고 새로운 기사만 크롤링
    # skip_existing=False: 모든 기사를 다시 크롤링 (기존 파일 덮어쓰기)
    SKIP_EXISTING = True  # 추천: True (효율적)
    
    categories = ["fashion", "beauty"]
    all_results = {}
    
    for category in categories:
        logger.info(f"\n{'='*80}")
        logger.info(f"[{category.upper()}] 크롤링 시작")
        logger.info(f"{'='*80}")
        
        # 카테고리별 Scraper 인스턴스 생성
        scraper = VogueKoreaScraper(category=category)
        
        # 최대 20개 기사 크롤링
        # skip_existing=True: 기존 기사는 스킵하고 새로운 기사만 수집
        # skip_existing=False: 모든 기사를 다시 크롤링
        articles = scraper.run(
            max_articles=20,
            min_delay=1,
            max_delay=3,
            skip_existing=SKIP_EXISTING
        )
        all_results[category] = articles
        
        # 결과 확인
        if articles:
            logger.info(f"\n[수집된 데이터 미리보기 - {category}]")
            logger.info(f"제목: {articles[0]['title']}")
            logger.info(f"URL: {articles[0]['url']}")
            logger.info(f"저자: {articles[0]['author']}")
            logger.info(f"키워드: {', '.join(articles[0]['keywords'])}")
            logger.info(f"본문 미리보기 (200자): {articles[0]['content'][:200]}...")
        
        # 카테고리 간 대기 (서버 부하 방지)
        if category != categories[-1]:
            logger.info(f"\n다음 카테고리 크롤링까지 5초 대기...")
            time.sleep(5)
    
    # 최종 요약
    logger.info(f"\n{'='*80}")
    logger.info("전체 크롤링 완료!")
    logger.info(f"{'='*80}")
    for category, articles in all_results.items():
        count = len(articles) if articles else 0
        logger.info(f"[{category}] {count}개의 기사 수집 완료")
