from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def Driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # ヘッドレスモード
    chrome_options.add_argument('--disable-gpu')  # GPUハードウェアアクセラレーションを無効化
    chrome_options.add_argument('--no-sandbox')  # サンドボックスモードを無効化
    chrome_options.add_argument('--disable-dev-shm-usage')  # 共有メモリファイルの使用を無効化
    chrome_options.add_argument('--disable-extensions')  # 拡張機能を無効化
    chrome_options.add_argument('--disable-browser-side-navigation')  # ブラウザサイドナビゲーションを無効化
    chrome_options.add_argument('--disable-infobars')  # 情報バーを無効化
    chrome_options.add_argument('--disable-notifications')  # 通知を無効化
    chrome_options.add_argument('--disable-popup-blocking')  # ポップアップブロックを無効化
    chrome_options.add_argument('--disk-cache-size=1')
    chrome_options.add_argument('--media-cache-size=1')
    chrome_options.add_argument('--disk-cache-dir=/dev/null')
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
    prefs = {
        'profile.default_content_setting_values': {
            'images': 2,  # 画像を読み込まない
            'javascript': 1,  # JavaScriptを有効
            'cookies': 2,  # Cookieを無効
            'plugins': 2,  # プラグインを無効
            'popups': 2,  # ポップアップを無効
            'geolocation': 2,  # 位置情報を無効
            'notifications': 2,  # 通知を無効
        }
    }
    chrome_options.add_experimental_option('prefs', prefs)
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    driver = webdriver.Chrome(options=chrome_options)
    return driver