"""
@file    driver.py
@brief   undetected-chromedriver ベースのWebドライバーファクトリ
@version 3.2.0  2026-04-05  UA/ヘッダー/ウィンドウサイズのランダム化でBot検出回避強化

変更理由:
  このLinux環境のIPがnetkeiba.comにブロックされているため、
  Mac（Tailscale: mac）をSOCKS5踏み台として使いIPを迂回する。
  ssh -D 1080 -N -f mac で127.0.0.1:1080にSOCKS5を立ててからChrome経由。
  さらに毎セッションでUA・ヘッダー・解像度をランダム化し指紋を分散させる。
"""
import time
import random
import logging
import subprocess
import socket
import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)

WARMUP_URL = 'https://race.netkeiba.com/top/'  # race.netkeiba.comのセッションCookieを取得するため
WARMUP_WAIT = 5
SOCKS5_HOST = '127.0.0.1'
SOCKS5_PORT = 1080

# 実際のブラウザから収集した本物のUser-Agentプール（Chrome最新系）
_USER_AGENTS = [
    # Windows 10 + Chrome
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    # Windows 11 + Chrome
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.122 Safari/537.36',
    # macOS + Chrome
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
]

# 一般的な画面解像度プール（headlessでもwindow-sizeに影響）
_WINDOW_SIZES = [
    (1280, 800),
    (1366, 768),
    (1440, 900),
    (1536, 864),
    (1600, 900),
    (1920, 1080),
]

# Accept-Languageプール（日本語ユーザーの典型値）
_ACCEPT_LANGUAGES = [
    'ja,en-US;q=0.9,en;q=0.8',
    'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
    'ja,en;q=0.9',
    'ja-JP,ja;q=0.8,en-US;q=0.6,en;q=0.4',
]


def _ensure_socks5_proxy():
    """SOCKS5プロキシ(127.0.0.1:1080)が起動しているか確認し、なければ起動する。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((SOCKS5_HOST, SOCKS5_PORT))
    sock.close()
    if result == 0:
        logger.info('SOCKS5 proxy already running on :1080')
        return
    logger.info('Starting SOCKS5 proxy via mac...')
    subprocess.Popen(
        ['ssh', '-o', 'ConnectTimeout=15', '-D', str(SOCKS5_PORT), '-N', '-f', 'mac'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    logger.info('SOCKS5 proxy started on :1080')


def _set_stealth_headers(driver: uc.Chrome, accept_language: str) -> None:
    """CDP経由でリクエストヘッダーを本物のブラウザに近づける。"""
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': accept_language,
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
    })


def Driver():
    """
    Mac踏み台SOCKS5プロキシ経由でBot検出・IPブロックを回避するChromeドライバーを生成する。
    毎回UA・ウィンドウサイズ・ヘッダーをランダム化して指紋を分散させる。

    Returns:
        uc.Chrome: warmup済みのChromeドライバー
    """
    _ensure_socks5_proxy()

    ua = random.choice(_USER_AGENTS)
    w, h = random.choice(_WINDOW_SIZES)
    accept_lang = random.choice(_ACCEPT_LANGUAGES)
    logger.info(f'[stealth] UA={ua[:60]}... size={w}x{h} lang={accept_lang[:20]}')

    opts = uc.ChromeOptions()
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-notifications')
    opts.add_argument('--blink-settings=imagesEnabled=false')
    opts.add_argument(f'--proxy-server=socks5://{SOCKS5_HOST}:{SOCKS5_PORT}')
    opts.add_argument(f'--user-agent={ua}')
    opts.add_argument(f'--window-size={w},{h}')
    opts.add_argument(f'--lang=ja-JP')

    driver = uc.Chrome(options=opts, headless=True, version_main=145)

    # ページロードタイムアウト設定（無限待機を防ぐ）
    driver.set_page_load_timeout(120)   # 120秒でTimeoutException（プロキシ経由は遅い）
    driver.set_script_timeout(30)       # JS実行タイムアウト

    # CDPでリクエストヘッダーを人間らしく設定
    try:
        _set_stealth_headers(driver, accept_lang)
    except Exception as e:
        logger.warning(f'CDPヘッダー設定失敗（続行）: {e}')

    # Cookie warmup: Mac IPでセッションCookieを取得（失敗しても続行）
    try:
        driver.get(WARMUP_URL)
        time.sleep(random.uniform(3, 7))  # warmup待機もランダム化
        cookies = driver.get_cookies()
        logger.info(f'Cookie warmup完了(proxy経由): {len(cookies)}個取得')
    except TimeoutException:
        logger.warning('Cookie warmupタイムアウト — Cookieなしで続行（プロキシは有効）')

    return driver
