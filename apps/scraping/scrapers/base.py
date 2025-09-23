"""
ベーススクレイパークラス
"""
import time
import logging
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from django.conf import settings
from apps.scraping.models import ScrapingJob, ScrapingLog, ScrapingSource


logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    スクレイピング基底クラス
    """
    
    def __init__(self, source: ScrapingSource, job: Optional[ScrapingJob] = None):
        self.source = source
        self.job = job
        self.session = requests.Session()
        self.driver = None
        
        # セッション設定
        self.session.headers.update(self.source.headers or {})
        if self.source.user_agent:
            self.session.headers['User-Agent'] = self.source.user_agent
        
        # リクエスト設定
        self.delay = self.source.delay_seconds
        self.timeout = self.source.timeout_seconds
        self.max_retries = self.source.max_retries
        
        # レート制限
        self.last_request_time = 0
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        if self.session:
            self.session.close()
        if self.driver:
            self.driver.quit()
    
    def log(self, level: str, message: str, url: str = '', **kwargs):
        """ログを記録"""
        if self.job:
            ScrapingLog.objects.create(
                job=self.job,
                level=level,
                message=message,
                url=url,
                **kwargs
            )
        
        getattr(logger, level)(f"[{self.source.name}] {message}")
    
    def respect_rate_limit(self):
        """レート制限を遵守"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            sleep_time = self.delay - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def make_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """HTTPリクエストを実行"""
        self.respect_rate_limit()
        
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()
                
                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                response_time = time.time() - start_time
                
                self.log(
                    'info',
                    f"Request successful: {method} {url}",
                    url=url,
                    response_code=response.status_code,
                    response_time=response_time,
                    data_size=len(response.content)
                )
                
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                self.log(
                    'warning' if attempt < self.max_retries else 'error',
                    f"Request failed (attempt {attempt + 1}/{self.max_retries + 1}): {str(e)}",
                    url=url
                )
                
                if attempt < self.max_retries:
                    # 指数バックオフでリトライ
                    time.sleep(2 ** attempt)
                else:
                    self.log('error', f"Max retries exceeded for {url}", url=url)
                    return None
    
    def get_soup(self, url: str, **kwargs) -> Optional[BeautifulSoup]:
        """BeautifulSoupオブジェクトを取得"""
        response = self.make_request(url, **kwargs)
        if response:
            return BeautifulSoup(response.content, 'html.parser')
        return None
    
    def setup_selenium_driver(self, headless: bool = True) -> webdriver.Chrome:
        """Seleniumドライバーをセットアップ"""
        if self.driver:
            return self.driver
        
        options = Options()
        if headless:
            options.add_argument('--headless')
        
        # 一般的なオプション
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # User-Agent設定
        if self.source.user_agent:
            options.add_argument(f'--user-agent={self.source.user_agent}')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(10)
            return self.driver
        except WebDriverException as e:
            self.log('error', f"Failed to setup Selenium driver: {str(e)}")
            raise
    
    def selenium_get(self, url: str, wait_element: str = None) -> bool:
        """Seleniumでページを取得"""
        if not self.driver:
            self.setup_selenium_driver()
        
        try:
            self.respect_rate_limit()
            start_time = time.time()
            
            self.driver.get(url)
            
            # 特定の要素を待機
            if wait_element:
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_element))
                )
            
            response_time = time.time() - start_time
            self.log(
                'info',
                f"Selenium page loaded: {url}",
                url=url,
                response_time=response_time
            )
            
            return True
            
        except TimeoutException:
            self.log('error', f"Timeout loading page: {url}", url=url)
            return False
        except WebDriverException as e:
            self.log('error', f"Selenium error: {str(e)}", url=url)
            return False
    
    def extract_data_by_selector(self, soup: BeautifulSoup, selector: str, 
                                attribute: str = None) -> List[str]:
        """CSSセレクターでデータを抽出"""
        try:
            elements = soup.select(selector)
            if attribute:
                return [elem.get(attribute, '') for elem in elements if elem.get(attribute)]
            else:
                return [elem.get_text(strip=True) for elem in elements]
        except Exception as e:
            self.log('error', f"Error extracting data with selector '{selector}': {str(e)}")
            return []
    
    def extract_data_by_xpath(self, xpath: str) -> List[str]:
        """XPathでデータを抽出（Selenium使用）"""
        if not self.driver:
            self.log('error', "Selenium driver not initialized for XPath extraction")
            return []
        
        try:
            elements = self.driver.find_elements(By.XPATH, xpath)
            return [elem.text.strip() for elem in elements]
        except WebDriverException as e:
            self.log('error', f"Error extracting data with XPath '{xpath}': {str(e)}")
            return []
    
    def preprocess_data(self, data: str, rules: List[Dict]) -> str:
        """データの前処理を実行"""
        for rule in rules:
            rule_type = rule.get('type')
            
            if rule_type == 'strip':
                data = data.strip()
            elif rule_type == 'replace':
                data = data.replace(rule['old'], rule['new'])
            elif rule_type == 'regex_replace':
                import re
                data = re.sub(rule['pattern'], rule['replacement'], data)
            elif rule_type == 'normalize_space':
                import re
                data = re.sub(r'\s+', ' ', data).strip()
            elif rule_type == 'remove_tags':
                from bs4 import BeautifulSoup
                data = BeautifulSoup(data, 'html.parser').get_text()
        
        return data
    
    def validate_data(self, data: Any, rules: List[Dict]) -> bool:
        """データのバリデーションを実行"""
        for rule in rules:
            rule_type = rule.get('type')
            
            if rule_type == 'required' and not data:
                return False
            elif rule_type == 'min_length' and len(str(data)) < rule['value']:
                return False
            elif rule_type == 'max_length' and len(str(data)) > rule['value']:
                return False
            elif rule_type == 'regex_match':
                import re
                if not re.match(rule['pattern'], str(data)):
                    return False
            elif rule_type == 'numeric' and not str(data).replace('.', '').isdigit():
                return False
        
        return True
    
    @abstractmethod
    def scrape(self, **kwargs) -> Dict[str, Any]:
        """スクレイピング実行（サブクラスで実装）"""
        pass
    
    @abstractmethod
    def get_urls_to_scrape(self, **kwargs) -> List[str]:
        """スクレイピング対象URLのリストを取得（サブクラスで実装）"""
        pass


class RaceDataScraper(BaseScraper):
    """
    レースデータ専用スクレイパー
    """
    
    def validate_race_data(self, data: Dict) -> bool:
        """レースデータの妥当性をチェック"""
        required_fields = ['race_name', 'race_date', 'venue', 'entries']
        
        for field in required_fields:
            if field not in data or not data[field]:
                self.log('warning', f"Missing required field: {field}")
                return False
        
        return True
    
    def normalize_race_data(self, data: Dict) -> Dict:
        """レースデータを正規化"""
        # 馬名の正規化
        if 'entries' in data:
            for entry in data['entries']:
                if 'horse_name' in entry:
                    from apps.core.utils import normalize_horse_name
                    entry['horse_name'] = normalize_horse_name(entry['horse_name'])
                
                if 'jockey_name' in entry:
                    from apps.core.utils import normalize_jockey_name
                    entry['jockey_name'] = normalize_jockey_name(entry['jockey_name'])
        
        return data


class HorseDataScraper(BaseScraper):
    """
    馬データ専用スクレイパー
    """
    
    def validate_horse_data(self, data: Dict) -> bool:
        """馬データの妥当性をチェック"""
        required_fields = ['horse_name', 'birth_date']
        
        for field in required_fields:
            if field not in data or not data[field]:
                self.log('warning', f"Missing required field: {field}")
                return False
        
        return True
    
    def normalize_horse_data(self, data: Dict) -> Dict:
        """馬データを正規化"""
        if 'horse_name' in data:
            from apps.core.utils import normalize_horse_name
            data['horse_name'] = normalize_horse_name(data['horse_name'])
        
        return data
