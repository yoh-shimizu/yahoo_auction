from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
import time
import requests
import json
from datetime import datetime

WEB_HOOK_URL = ''
USER_NAME = ''
PASSWORD = ''


class YahooAuction():

    def send_slack_message(self, message):
        requests.post(WEB_HOOK_URL, data=json.dumps({
            "text" : message,
        }))

    def get_fbid_page(self):
        try:
            driver = webdriver.Remote(
                command_executor='http://selenium-hub:4444/wd/hub',
                desired_capabilities=DesiredCapabilities.CHROME)
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
            driver.quit()

            return result, session
        except:
            import traceback
            self.send_slack_message("新着情報ページ取得中にエラーが発生しました")
            traceback.print_exc()
            driver.quit()

    def parse_page(self, page):
        try:
            soup = BeautifulSoup(page.text, "html.parser")
            exhibits = soup.find_all('td', class_='decTd06')
            bid_dates = soup.find_all('td', class_='decTd05')

            if len(exhibits)==0:
                return []
            
            targets = []

            for i,v in zip(exhibits, bid_dates):
                link = i.a['href']
                title = i.a.text.replace('初回入札:', '')
                fbid_date = datetime.strptime(v.text.replace(' ', ''), '%Y年%m月%d日%H時%M分')
                targets.append(
                    {
                        'link':link,
                        'title':title,
                        'fbid_date':fbid_date
                    }
                )

            return targets
        except:
            import traceback
            self.send_slack_message("新着情報ページ解析中にエラーが発生しました")
            traceback.print_exc()

    def report_fbid_to_slack(self, targets, session):
        try:
            for i in targets:
                res = requests.post(WEB_HOOK_URL, data=json.dumps({
                    "text" : "商品名：{0}\nリンク:{1}".format(i['title'], i['link']),
                }))
                if res.status_code==200:
                    session.get(i['link'])
        except:
            import traceback
            self.send_slack_message("商品情報送信中にエラーが発生しました")
            traceback.print_exc()


if __name__ == "__main__":
    yahoo_auction = YahooAuction()
    yahoo_auction.send_slack_message("初回入札チェックstart")
    page, session = yahoo_auction.get_fbid_page()
    targets = yahoo_auction.parse_page(page)
    yahoo_auction.report_fbid_to_slack(targets, session)
    yahoo_auction.send_slack_message("初回入札チェックcomplete")