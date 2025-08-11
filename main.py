import argparse
import os
import re
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from config import region_config
from excel import append_to_exisiting_excel_report, new_excel_report, daily_append_excel_report
from util.days_loading_check import days_loading_check, single_day_loading

TARGETS_CONFIG = [
    {
        "panel_id": "4",
        "panel_name": "CPU Usage",
    },
    {
        "panel_id": "6",
        "panel_name": "Memory Usage",
    }
]

STATUS_THRESHOLD = 70.0

# respost 저장 폴더
OUTPUT_DIR = ""

# CONFIG
TARGETS_CONFIG = [
    {
        "panel_id": "4",
        "panel_name": "CPU Usage",
        "identifiers": [
            "gss-interface",
            "gss-place-google",
            "gss-place-here",
            "gss-api-mcp",
            "gss-api-mmi"
        ]
    },
    {
        "panel_id": "6",
        "panel_name": "Memory Usage",
        "identifiers": [
            "gss-interface",
            "gss-place-google",
            "gss-place-here",
            "gss-api-mcp",
            "gss-api-mmi"
        ]
    }
]

def _clean_text_to_float(text: str) -> Optional[float]:
    if not text:
        return None
    match = re.search(r'[\d.]+', text)
    if match:
        return float(match.group())
    return None

def _get_header_map(table_element: BeautifulSoup) -> Dict[str, int]:
    header_map = {}
    headers = table_element.find_all('th')

    for i, th in enumerate(headers):
        text = th.get_text(strip=True).lower()
        title = (th.get('title') or "").lower()

        if 'min' in text or 'minimum' in title:
            header_map['min'] = i
        elif 'max' in text or 'maximum' in title:
            header_map['max'] = i
        elif 'mean' in text or 'avg' in text or 'average' in title:
            header_map['avg'] = i

    return header_map

def parse_panel_for_all_services(get_html, panel_id: str, service_identifiers: List[str]) -> Dict[str, Dict[str, float]]:
    final_results = {}

    soup = BeautifulSoup(get_html, 'lxml')

    if not (panel := soup.find('div', attrs={'data-panelid': panel_id})): return final_results
    if not (table := panel.find('table')): return final_results
    if not all(k in (header_map := _get_header_map(table)) for k in ['min', 'max', 'avg']): return final_results

    for identifier in service_identifiers:
        data = _extract_data_for_identifier(table, header_map, identifier)
        if data["min_values"]:
            final_results[identifier] = {
                "min": min(data["min_values"]),
                "max": max(data["max_values"]),
                "avg": sum(data["avg_values"]) / len(data["avg_values"])
            }
    return final_results

def _extract_data_for_identifier(table_element: BeautifulSoup, header_map: Dict[str, int], row_identifier: str) -> Dict[str, List[float]]:

    collected_data = {"min_values": [], "max_values": [], "avg_values": []}
    tbody = table_element.find('tbody')
    if not tbody:
        return collected_data
        
    rows = tbody.find_all('tr')
    for row in rows:
        button = row.find('button', title=lambda t: t and t.startswith(row_identifier))
        if not button:
            continue

        cells = row.find_all('td')
        try:
            min_val = _clean_text_to_float(cells[header_map['min']].get_text())
            max_val = _clean_text_to_float(cells[header_map['max']].get_text())
            avg_val = _clean_text_to_float(cells[header_map['avg']].get_text())

            if all(v is not None for v in [min_val, max_val, avg_val]):
                collected_data["min_values"].append(min_val)
                collected_data["max_values"].append(max_val)
                collected_data["avg_values"].append(avg_val)

        except (IndexError, AttributeError, KeyError):
            # 오류가 있는 행은 건너뜀
            continue
            
    return collected_data

def parse_panel_for_multiple_targets(file_path: str, panel_id: str, identifiers: List[str]) -> Dict[str, Dict[str, float]]:

    final_results = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), 'lxml')
    except FileNotFoundError:
        print(f"❌ 오류: '{file_path}' 파일을 찾을 수 없습니다.")
        return final_results

    panel = soup.find('div', attrs={'data-panelid': panel_id})
    if not panel:
        print(f"❌ 오류: data-panelid='{panel_id}'인 패널을 찾을 수 없습니다.")
        return final_results

    table = panel.find('table')
    if not table:
        print(f"❌ 오류: 패널 ID '{panel_id}' 내에서 <table>을 찾을 수 없습니다.")
        return final_results

    header_map = _get_header_map(table)
    if not all(k in header_map for k in ['min', 'max', 'avg']):
        print(f"❌ 오류: 테이블에서 Min, Max, Mean/Avg 헤더를 모두 찾을 수 없습니다.")
        return final_results
    
    print(f"✅ 패널(ID: {panel_id}) 및 테이블 분석 완료. 데이터 추출을 시작합니다.\n")
    
    # 설정된 모든 식별자에 대해 반복 작업 수행
    for identifier in identifiers:
        data = _extract_data_for_identifier(table, header_map, identifier)
        
        if not data["min_values"]:
            continue

        # 데이터가 있으면 최종 계산 수행
        calculated = {
            "min": min(data["min_values"]),
            "max": max(data["max_values"]),
            "avg": round(sum(data["avg_values"]) / len(data["avg_values"]))
        }
        final_results[identifier] = calculated
        
    return final_results

def create_horizontal_excel_report(all_results: Dict[str, Dict], filename: str, header_names, index, day_header, is_peak_time):

    yesterday = datetime.today()
    report_folder = yesterday.strftime("%m%d")

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    a = os.path.join(BASE_DIR, report_folder)
    full_path = os.path.join(a, filename)

    if is_peak_time:
        peak_time_path = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(peak_time_path):
            daily_append_excel_report.main(peak_time_path, all_results, header_names ,index, day_header)
        else:
            new_excel_report.main(peak_time_path, all_results, header_names, index, day_header)
    elif os.path.exists(full_path):
        append_to_exisiting_excel_report.main(full_path, all_results, header_names ,index, day_header)
    else:
        new_excel_report.main(os.path.join(OUTPUT_DIR, filename), all_results, header_names ,index, day_header)


def main(research_days, args):
    global OUTPUT_DIR
    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    is_peak_time = args.peak_time
    load_dotenv()
    user_name = os.getenv("USERNAME")
    user_password = os.getenv("PASSWORD")

    try:
        for idx, region in enumerate(region_config.region_config):
            driver.get(region['url'])
            driver.set_window_size(1200, 1000)

            driver.find_element(By.XPATH, '//*[@id="pageContent"]/div[3]/div/div/div/div[2]/div/div[2]/a').click()

            if idx == 0:
                driver.find_element(By.ID, 'username').send_keys(user_name)
                driver.find_element(By.ID, 'password').send_keys(user_password + Keys.RETURN)


            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[1]/div/header/div[2]/div[2]/div[3]/div[4]/div[1]/button[1]'))
            )

            calendar = driver.find_element(By.XPATH,'/html/body/div[1]/div[1]/div/header/div[2]/div[2]/div[3]/div[4]/div[1]/button[1]')

            for index, day in enumerate(research_days):
                    calendar.click()
                    input_from_date = driver.find_element(By.XPATH, '/html/body/div[1]/div[1]/div/header/div[2]/div[2]/div[3]/div[4]/div[1]/div/section/div/div[1]/div[2]/div[1]/div[2]/div[1]/div[1]/div[2]/div/div/div[1]/input')
                    input_from_date.clear()
                    input_from_date.send_keys(day["from_yesterday_data"])
                    input_to_date= driver.find_element(By.XPATH, '/html/body/div[1]/div[1]/div/header/div[2]/div[2]/div[3]/div[4]/div[1]/div/section/div/div[1]/div[2]/div[1]/div[2]/div[2]/div[1]/div[2]/div/div/div[1]/input')
                    input_to_date.clear()
                    input_to_date.send_keys(day["to_yesterday_data"])

                    driver.find_element(By.XPATH, '/html/body/div[1]/div[1]/div/header/div[2]/div[2]/div[3]/div[4]/div[1]/div/section/div/div[1]/div[2]/div[1]/div[2]/div[3]/button[3]').click()

                    scroll_container = driver.find_element(By.CSS_SELECTOR, "#page-scrollbar")

                    driver.execute_script("arguments[0].scrollTop = arguments[1]", scroll_container,500)


                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, '/html/body/div[1]/div[1]/div/div[1]/div/main/div[3]/div/div/div/div/div/div/div[8]/div/section/div[3]/div/div[2]/div/div[1]/table')),
                    )

                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH,
                                                        '/html/body/div[1]/div[1]/div/div[1]/div/main/div[3]/div/div/div/div/div/div/div[9]/div/section/div[3]/div/div[2]/div/div[1]/table'))
                    )

                    time.sleep(5)

                    get_html = driver.page_source
                    all_panel_results = {}
                    service_identifiers_to_parse = list(region['header_name'].values())

                    for target_config in TARGETS_CONFIG:
                        panel_id = target_config["panel_id"]
                        panel_name = target_config["panel_name"]

                        print(f"\n>>>>>> '{panel_name}' (Panel ID: {panel_id}) 분석 시작 >>>>>>")
                        results = parse_panel_for_all_services(get_html, panel_id, service_identifiers_to_parse)
                        if results:
                            all_panel_results[panel_name] = results
                            print(f"'{panel_name}'에서 {len(results)}개 서비스 데이터 추출 완료.")
                        else:
                            print(f"'{panel_name}'에서 분석할 데이터를 찾지 못했습니다.")

                    if not all_panel_results:
                        print("\nℹ️ 최종적으로 분석할 데이터가 없습니다.")
                    else:
                        yesterday = datetime.today()-timedelta(days=1)

                        if day.get("searching_single_date"):
                            report_filename = f"{region["region"]}_GSS_Daily-report-{day["searching_single_date"]}.xlsx"
                        else:
                            report_filename = f"{region["region"]}_GSS_Daily-report-{datetime.today().strftime('%Y-%m-%d')}.xlsx"

                        if args.peak_time :
                            report_filename = f"{args.peak_type}_peak_time_" + report_filename
                            OUTPUT_DIR =  "reports/" + args.peak_type + "_Peak_Time"
                        else:
                            OUTPUT_DIR = "reports/" + region["region"]

                        create_horizontal_excel_report(all_panel_results, report_filename,region['header_name'],index+1, day["from_yesterday_data"], is_peak_time)

    except Exception as e:
        print("\n======================================================")
        print(f"[CRITICAL ERROR] 스크립트 실행 중 치명적인 오류가 발생했습니다.")
        print(f"오류 내용: {e}")
        import traceback
        traceback.print_exc()
        print("======================================================")

    finally:
        print("\n모든 작업이 완료되었습니다.")
        input("엔터 키를 누르면 창이 닫힙니다...")

# --- 메인 실행 블록 ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--peak_time", required=False, help="Is it peak time")
    parser.add_argument("--peak_type", required=False, help="Is it AM or PM")
    args = parser.parse_args()
    # research_day = days_loading_check(1,args)
    research_day = single_day_loading("2025-08-09",args)
    main(research_day,args)