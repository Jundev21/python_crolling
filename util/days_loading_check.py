from datetime import timedelta, datetime
import sys

def days_loading_check(days,args):
    result =[]
    current_data = datetime.today()
    pick_time_AM = "08:00:00 ~ 10:00:00"
    pick_time_PM = "16:00:00 ~ 19:00:00"
    if args.peak_time and args.peak_type is None:
        print("please insert peak_type")
        return None
    #
    # if args.peak_type != "AM" or args.peak_type != "PM":
    #     print("please insert peak type AM or PM")
    #     return sys.exit()

    if args.peak_time:
        print("피크타임 검색 시작")
        if args.peak_type == "AM":
            print(f"피크타임 시간대 08:00:00 ~ 10:00:00 { args.peak_type}")
        elif args.peak_type == "PM":
            print(f"피크타임 시간대 {pick_time_PM} { args.peak_type}")
    else:
        print("일반 일일점검 검색 시작")
    for day in range(days, 0, -1):
        from_yesterday_data = ""
        to_yesterday_data = ""
        change_day = current_data-timedelta(day)

        if args.peak_time:
            if args.peak_type == "PM":
                from_yesterday_data = change_day.strftime("%Y-%m-%d 16:00:00")
                to_yesterday_data = change_day.strftime("%Y-%m-%d 19:00:00")
            elif args.peak_type == "AM":
                from_yesterday_data = change_day.strftime("%Y-%m-%d 08:00:00")
                to_yesterday_data = change_day.strftime("%Y-%m-%d 10:00:00")
            else:
                raise ValueError("peak_type must be 'pm' or 'am'")
        else:
            from_yesterday_data = change_day.strftime("%Y-%m-%d 00:00:00")
            to_yesterday_data = change_day.strftime("%Y-%m-%d 23:59:59")

        result.append({
            "from_yesterday_data" : from_yesterday_data ,
            "to_yesterday_data" : to_yesterday_data

        })

    return result


def single_day_loading(day,args):
    result =[]
    current_data = datetime.today()
    pick_time_AM = "08:00:00 ~ 10:00:00"
    pick_time_PM = "16:00:00 ~ 19:00:00"
    if args.peak_time and args.peak_type is None:
        print("please insert peak_type")
        return None

    if args.peak_time:
        print("피크타임 검색 시작")
        if args.peak_type == "AM":
            print(f"피크타임 시간대 {pick_time_AM} { args.peak_type}")
        elif args.peak_type == "PM":
            print(f"피크타임 시간대 {pick_time_PM} { args.peak_type}")
    else:
        print("일반 일일점검 검색 시작")

    if args.peak_time:
        if args.peak_type == "PM":
            from_yesterday_data = f"{day} 16:00:00"
            to_yesterday_data = f"{day} 19:00:00"
        elif args.peak_type == "AM":
            from_yesterday_data = f"{day} 08:00:00"
            to_yesterday_data = f"{day} 10:00:00"
        else:
            raise ValueError("peak_type must be 'pm' or 'am'")
    else:
        from_yesterday_data = f"{day} 00:00:00"
        to_yesterday_data = f"{day} 23:59:59"

    result.append({
        "from_yesterday_data": from_yesterday_data,
        "to_yesterday_data": to_yesterday_data

    })

    return result