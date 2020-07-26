# -*- coding: utf-8 -*-
import os
import time
import random
import json
import scrapy
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import traceback
from scrapy.http import Request
import requests
from bs4 import BeautifulSoup
from . import cities
base_dir = os.path.dirname(os.path.abspath(__file__))

class GrubhubspiderSpider(scrapy.Spider):
    name = 'grubhubSpider'
    allowed_domains = ['grubhub.com']

    def __init__(self, *args, **kwargs):
        self.result = dict()
        self.url = 'https://www.grubhub.com/'
        
        self.proxy_list = [
        ]
    
        self.cities = cities.cities_list

    def get_random_proxy(self):
        random_idx = random.randint(0, len(self.proxy_list)-1)
        proxy_ip = self.proxy_list[random_idx]
        return proxy_ip

    def set_driver(self):
        
        random_proxy_ip = self.get_random_proxy()        
        webdriver.DesiredCapabilities.CHROME['proxy'] = {
            "httpProxy":random_proxy_ip,
            "ftpProxy":random_proxy_ip,
            "sslProxy":random_proxy_ip,
            "proxyType":"MANUAL",
        } 
          
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) ' \
            'Chrome/80.0.3987.132 Safari/537.36'
        chrome_option = webdriver.ChromeOptions()
        chrome_option.add_argument('--no-sandbox')
        chrome_option.add_argument('--disable-dev-shm-usage')
        chrome_option.add_argument('--ignore-certificate-errors')
        chrome_option.add_argument("--disable-blink-features=AutomationControlled")
        chrome_option.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) ' \
            'Chrome/80.0.3987.132 Safari/537.36')
        # chrome_option.headless = True
        
        driver = webdriver.Chrome(options = chrome_option)
        return driver

    def start_requests(self):
        yield Request("https://www.grubhub.com/", callback=self.parse)
            
    def parse(self, response):
        for city in self.cities:
            try:
                lst = []
                
                self.driver = self.set_driver()
                self.driver.get(self.url)
                time.sleep(15)
                
                # input search key
                input_ = self.driver.find_element_by_xpath('//*[@id="homepage-logged-out-top"]/ghs-welcome-view/div/div[2]/div[2]/div[2]/ghs-start-order-form/div/div[1]/div/ghs-address-input/div/div/div/input')
                input_.send_keys(city.strip())
                time.sleep(15)

                input_.send_keys(Keys.RETURN)
                time.sleep(15)

                while True:
                    try:
                        chiri_modal_close_btn = self.driver.find_element_by_xpath('//*[@id="chiri-modal"]/a[@class="c-modal-close"]')
                        if chiri_modal_close_btn:
                            chiri_modal_close_btn.click()
                            time.sleep(5)
                    except:
                        pass
                        
                    # get restaurants urls
                    rest_items = self.driver.find_elements_by_xpath('//*[@id="ghs-search-results-container"]/div/div/div/div/ghs-search-results/div/div/div[4]/div/ghs-impression-tracker/div/div')
                    for rest_item in rest_items:
                        if 'search-carousel' not in rest_item.get_attribute('class').split():
                            rest_url_tag = rest_item.find_element_by_xpath('//div[contains(@class, "s-card-title")]/a[contains(@class, "restaurant-name")]')
                            if rest_url_tag:
                                rest_url = rest_url_tag.get_attribute('href').strip()
                                if rest_url:
                                    lst.append(rest_url)
                    
                    try:
                        next_page_btn = self.driver.find_element_by_xpath('//*[@id="ghs-search-results-container"]/div/div[2]/div/div/ghs-search-results/div[2]/div/div/ghs-pagination/ul/li/a[@aria-label="Next"]')
                        if next_page_btn:
                            next_page_btn_li = next_page_btn.find_element_by_xpath('..')
                            if next_page_btn_li.is_enabled():
                                next_page_btn.click()
                                time.sleep(15)
                            else:
                                break

                            continue
                        else:
                            break
                    except:
                        break

                self.driver.quit()
            except Exception as e:
                # print(traceback.print_exc())
                print(e)
                print("element not found..")
                self.driver.quit()
            
            print('---------------------------------------------------------')
            print(lst)

            for rest_url in lst:
                    
                try:
                    self.driver = self.set_driver()
                    self.driver.get(rest_url)
                    time.sleep(10)
                    page_source = self.driver.page_source
                    time.sleep(10)
                    result_dict = {
                        "CITY" : city,
                        "RESTNAME" : "",
                        "ADDRESS" : "",
                        # "TIME" : "",
                        "RATINGS" : "",
                        "MENU" : [],
                    }

                    soup = BeautifulSoup(page_source, 'lxml')
                    if soup:
                        rest_name = soup.select_one('div.restaurantSummary-info h1.ghs-restaurant-nameHeader')
                        if rest_name:
                            result_dict["RESTNAME"] = rest_name.text.strip()

                        location = soup.select_one('div.restaurantSummary-info a[itemprop="streetAddress"]')
                        if location:
                            result_dict["ADDRESS"] = location.text.strip()

                        phone_num = soup.select_one('div.restaurantSummary-info span[data-testid="restaurant-phone"]')
                        if phone_num:
                            result_dict["PHONE"] = phone_num.text.strip()

                        # open_time = soup.select_one('div.sc-dcOKER span.hlXfBB')
                        # if open_time:
                        #     result_dict["TIME"] = open_time.text.strip()
                        
                        ratings = soup.select_one('div.restaurantSummary-info span[data-testid="stars"] div.stars')
                        if ratings:
                            
                            temp_dict = dict()
                            try:
                                rating_style_px = int(str(ratings).split('background-position')[1][5:10].split('"')[0].strip().split('px')[0][1:])
                                if rating_style_px < 40 and rating_style_px > 20:
                                    temp_dict["AVERAGE"] = str(1)
                                elif rating_style_px < 60 and rating_style_px > 40:
                                    temp_dict["AVERAGE"] = str(1.5)
                                elif rating_style_px < 80 and rating_style_px > 60:
                                    temp_dict["AVERAGE"] = str(2)
                                elif rating_style_px < 100 and rating_style_px > 80:
                                    temp_dict["AVERAGE"] = str(2.5)
                                elif rating_style_px < 120 and rating_style_px > 100:
                                    temp_dict["AVERAGE"] = str(3)
                                elif rating_style_px < 140 and rating_style_px > 120:
                                    temp_dict["AVERAGE"] = str(3.5)
                                elif rating_style_px < 160 and rating_style_px > 140:
                                    temp_dict["AVERAGE"] = str(4)
                                elif rating_style_px < 180 and rating_style_px > 160:
                                    temp_dict["AVERAGE"] = str(4.5)
                                elif rating_style_px < 200 and rating_style_px > 180:
                                    temp_dict["AVERAGE"] = str(5)
                            except:
                                pass
                            
                            rating_text = soup.select_one('div.restaurantSummary-info span[at-star-rating-text="true"]')
                            if rating_text:
                                temp_dict["VOLUME"] = rating_text.text.strip()
                            
                            popular_sec = soup.select_one('div#menuSectionpopularItems')
                            popular_items = list()
                            for popular_item in popular_sec.select('ghs-restaurant-menu-item'):
                                popular_item_dict = dict()
                                pop_menu_name = popular_item.select_one('a[itemprop="name"]')
                                if pop_menu_name:
                                    popular_item_dict["POP_NAME"] = pop_menu_name.text.strip()
                                
                                pop_menu_desc = popular_item.select_one('p[itemprop="description"]')
                                if pop_menu_desc:
                                    popular_item_dict["POP_DESCRIPTION"] = pop_menu_desc.text.strip()

                                pop_menu_price = popular_item.select_one('span[itemprop="price"]')
                                if pop_menu_price:
                                    popular_item_dict["POP_PRICE"] = pop_menu_price.text.strip()

                                popular_items.append(popular_item_dict)
                                temp_dict["POPULAR_ITEMS"] = popular_items
                                result_dict['RATINGS'] = temp_dict

                        
                        menu_items = soup.select('ghs-restaurant-menu-section ghs-restaurant-menu-item')
                        for menu_item in menu_items:
                            menu_dict = dict()
                            menu_name = menu_item.select_one('a[itemprop="name"]')
                            if menu_name:
                                menu_dict["NAME"] = menu_name.text.strip()
                            
                            menu_desc = menu_item.select_one('p[itemprop="description"]')
                            if menu_desc:
                                menu_dict["DESCRIPTION"] = menu_desc.text.strip()

                            menu_price = menu_item.select_one('span[itemprop="price"]')
                            if menu_price:
                                menu_dict["PRICE"] = menu_price.text.strip()

                            menu_img = menu_item.select_one('img')
                            if menu_img:
                                menu_dict["IMAGE"] = menu_img["src"].strip()

                            result_dict["MENU"].append(menu_dict)
                
                    if result_dict["RESTNAME"]:
                        yield result_dict     
                    
                    self.driver.quit()
                except Exception as e:
                    print(e)
                    self.driver.quit()
                    continue
