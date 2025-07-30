from typing import Dict

import xlwings as xw


def main(full_path , all_results: Dict[str, Dict], header_names, index, day_header):
    print("report 파일에 데이터 병합중...")
    app = xw.App(visible=False)
    wb = app.books.open(full_path)
    ws = wb.sheets[2]
    STATUS_THRESHOLD = 70.0
    data_row = ws.range("B"+str(ws.cells.last_cell.row)).end("up").row
    start_col = 2

    for display_name, internal_name in header_names.items():
        block_end_col = start_col + 9
        cpu_start_col, cpu_end_col = start_col, start_col + 4
        mem_start_col, mem_end_col = start_col + 5, start_col + 9

        cpu_data = all_results.get("CPU Usage", {}).get(internal_name, {})

        if cpu_data:
            ws.cells[data_row, cpu_start_col].value  = round(cpu_data.get('min', 0), 3)
            ws.cells[data_row, cpu_start_col + 1].value  = round(cpu_data.get('max', 0), 3)
            ws.cells[data_row, cpu_start_col + 2].value  = round(cpu_data.get('avg', 0), 3)
            status_cell = ws.cells[data_row, cpu_start_col + 3]

            if cpu_data.get('max', 0) > STATUS_THRESHOLD:
                status_cell.value = "Fail"
            else:
                status_cell.value= "Pass"

            ws.cells[data_row, cpu_start_col + 4].value ="이상없음"

        mem_data = all_results.get("Memory Usage", {}).get(internal_name, {})

        if mem_data:
            ws.cells[data_row, mem_start_col].value =round(mem_data.get('min', 0), 3)
            ws.cells[data_row, mem_start_col + 1].value =round(mem_data.get('max', 0), 3)
            ws.cells[data_row, mem_start_col + 2].value =round(mem_data.get('avg', 0), 3)
            status_cell = ws.cells[data_row, mem_start_col + 3]

            if mem_data.get('max', 0) > STATUS_THRESHOLD:
                status_cell.value= "Fail"
            else:
                status_cell.value = "Pass"

            ws.cells[data_row, mem_start_col + 4].value ="이상없음"

        start_col = block_end_col + 1


    # B6 행에 실제 날짜
    ws.cells[data_row,1].value =day_header[0:10]

    wb.save(full_path)
    wb.close()
    app.quit()

    print(f"\n✅ 엑셀 보고서가 성공적으로 병합되었습니다: {full_path}")