from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
import time
import requests
import json
from datetime import datetime
import sys

#args = sys.argv

# 初回入札通知用
FBID_WEBHOOK_URL = ''
# ログ用
LOG_WEBHOOK_URL = ''
USER_NAME = ''
PASSWORD = ''


class YahooAuction():

    def send_slack_message(self, webhook_url, message):
        return requests.post(webhook_url, data=json.dumps({
            "text" : message,
        }))

    def get_fbid_page(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')

            driver = webdriver.Remote(
                command_executor='http://selenium-hub:4444/wd/hub',
                desired_capabilities=DesiredCapabilities.CHROME,
                options=chrome_options)

            print("start scrape")
            driver.get("https://login.yahoo.co.jp/config/login")
            # javascriptが全て読み込まれるまで待機. 15秒経っても読み込みが終わらなければタイムアウト判定.
            WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located)

            driver.find_element_by_id("username").send_keys(USER_NAME)
            driver.find_element_by_id("btnNext").click()
            time.sleep(5)
            driver.find_element_by_id("passwd").send_keys(PASSWORD)
            driver.find_element_by_id("btnSubmit").click()
            print("login ok")

            session = requests.session()
            #セッションの受け渡し
            for cookie in driver.get_cookies():
                session.cookies.set(cookie["name"], cookie["value"])

            result = session.get("https://auctions.yahoo.co.jp/show/myaucinfo?selectedType=fbid")

            driver.get("https://login.yahoo.co.jp/config/login?logout=1")
            print("logout ok")
            driver.quit()

            return result, session
        except:
            import traceback
            self.send_slack_message(LOG_WEBHOOK_URL, "<!channel>\n新着情報ページ取得中にエラーが発生しました")
            traceback.print_exc()
            driver.quit()
            sys.exit()

    def parse_page(self, page):
        try:
            soup = BeautifulSoup(page.text, "html.parser")
            exhibits = soup.find_all('td', class_='decTd06')

            if len(exhibits)==0:
                return []

            targets = []
            for i in exhibits:
                targets.append(
                    {
                        'link':i.a['href'],
                        'title':i.a.text
                    }
                )

            return targets
        except:
            import traceback
            self.send_slack_message(LOG_WEBHOOK_URL, "<!channel>\n新着情報ページ解析中にエラーが発生しました")
            traceback.print_exc()
            sys.exit()

    def report_fbid_to_slack(self, targets, session):
        try:
            for i in targets:
                res = self.send_slack_message(FBID_WEBHOOK_URL, "商品名：{0}\nリンク：{1}".format(i['title'].replace('初回入札:', ''), i['link'].replace('?notice=fbid', '')))
                if res.status_code==200:
                    session.get(i['link'])
        except:
            import traceback
            self.send_slack_message(LOG_WEBHOOK_URL, "<!channel>\n商品情報送信中にエラーが発生しました")
            traceback.print_exc()
            sys.exit()


if __name__ == "__main__":
    yahoo_auction = YahooAuction()
    page, session = yahoo_auction.get_fbid_page()
    targets = yahoo_auction.parse_page(page)
    yahoo_auction.report_fbid_to_slack(targets, session)
    yahoo_auction.send_slack_message(LOG_WEBHOOK_URL, "初回入札チェックcomplete")