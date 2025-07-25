import time

from selenium.webdriver import Keys
from selenium.webdriver.common.by import By


def login_grafana(driver, region_config):
    for idx, region in enumerate(region_config):
        driver.get(region['url'])
        time.sleep(2)

        driver.find_element(By.XPATH, '//*[@id="pageContent"]/div[3]/div/div/div/div[2]/div/div[2]/a').click()

        if idx == 0 :
            driver.find_element(By.ID, 'username').send_keys('9502701')
            driver.find_element(By.ID, 'password').send_keys('Acro@0720' + Keys.RETURN)

        time.sleep(3)


    return None