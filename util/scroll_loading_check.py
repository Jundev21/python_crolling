from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By


def scroll_loading_check(chrome_driver, scroll_id, xpath):
    scroll_container = chrome_driver.find_element(By.CSS_SELECTOR, scroll_id)
    scroll_height = chrome_driver.execute_script("return arguments[0].scrollHeight", scroll_container)
    current_position = 0
    step = 300

    print("start find scroll height")

    while current_position < scroll_height:
        print(scroll_height)
        chrome_driver.execute_script("arguments[0].scrollTop = arguments[1]", scroll_container, current_position)
        current_position += step

        try:
            items = chrome_driver.find_element(By.XPATH, xpath)
            if items.is_displayed():
                break
        except NoSuchElementException:
            continue

        scroll_height = chrome_driver.execute_script("return arguments[0].scrollHeight", scroll_container)

    print("end find scroll height")
def scroll_to_bottom(chrome_driver, scroll_id):
    scroll_container = chrome_driver.find_element(By.CSS_SELECTOR, scroll_id)
    chrome_driver.execute_script(
        "arguments[0].scrollTop = arguments[0].scrollHeight",
        scroll_container
    )