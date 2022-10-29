import calendar
from datetime import date, timedelta
import time
import requests
import pandas as pd
import json


# CONFIG ---------------------
# selected_search_type = "passport"
selected_months_look_ahead = 6
selected_start_date = date.today()
# ----------------------------

appointment_dict = {
    "nie": {
        "callback_key": "21108772810824730861_1666730773119",
        "agenda_key": "bkt215127",
        "service_key": "bkt532048",
    },
    "residence_doc": {
        "callback_key": "21108772810824730861_1666730773119",
        "agenda_key": "bkt215127",
        "service_key": "bkt532103",
    },
    "passport": {
        "callback_key": "21109829920575219404_1666802385628",
        "agenda_key": "bkt215292",
        "service_key": "bkt532004",
    },
}


def build_month_list(start_date=date.today(), months_look_ahead=3):
    # Don't look more than 1 year ahead.
    months_look_ahead = months_look_ahead if months_look_ahead <= 12 else 12

    time_delta = timedelta(weeks=months_look_ahead * 4)
    end_date = date.today() + time_delta

    months_to_query = []
    years = list(range(start_date.year, end_date.year + 1))

    for year in years:
        if year < end_date.year:
            last_month = 12
        elif year == end_date.year:
            last_month = end_date.month
        else:
            raise Exception("Looped past end year")

        if year == start_date.year:
            first_month = start_date.month
        elif year > start_date.year:
            first_month = 1
        else:
            raise Exception("Year is somehow before start year")

        months = list(range(first_month, last_month + 1))

        for month in months:
            print(f"Building query month: {year}-{month}")
            _, month_end = calendar.monthrange(year, month)

            months_to_query.append(
                {
                    "year": year,
                    "month": f"{month:02d}",
                    "first_day_of_month": "01",
                    "last_day_of_month": f"{month_end:02d}",
                }
            )

    return months_to_query


def get_time_slots_for_range(range_start_date, range_end_date, search_type):
    callback_code = appointment_dict[search_type]["callback_key"]
    public_key = "28dbd7e6e06b2996c84fa53fbe52091e7"
    agenda_key = appointment_dict[search_type]["agenda_key"]
    service_key = appointment_dict[search_type]["service_key"]
    low_dash_num = "1666730773124"
    base_url = f"https://www.citaconsular.es/onlinebookings/datetime/?callback=jQuery{callback_code}&type=default&publickey={public_key}&lang=es&services%5B%5D={service_key}&agendas%5B%5D={agenda_key}&version=1243&src=https%3A%2F%2Fwww.citaconsular.es%2Fes%2Fhosteds%2Fwidgetdefault%2F28dbd7e6e06b2996c84fa53fbe52091e7%23services&srvsrc=https%3A%2F%2Fcitaconsular.es&start={range_start_date}&end={range_end_date}&selectedPeople=1&_={low_dash_num}"

    print(
        f"Requesting range: {range_start_date} to {range_end_date} for search type: {search_type}"
    )
    r = requests.get(
        url=base_url,
        headers={
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "referer": "https://www.citaconsular.es/",
            "sec-ch-ua": '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "script",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
        },
    )

    if r.status_code == 200 and r.text:
        print(
            f"Request succeeded. Status code: {r.status_code}, Sample: {r.text[0:100]}"
        )
        # print(f"Request succeeded. Status code: {r.status_code}, Sample: {r.text}")
    else:
        raise Exception(f"Bad request: {r.text}")

    raw_data = r.text.replace(f"callback=jQuery{callback_code}(", "").replace(");", "")

    data = json.loads(raw_data)

    month_time_slots = data["Slots"]
    max_days = data["maxDays"]

    return month_time_slots, max_days


def process_time_slots_days(time_slot_days):
    available_time_slots = []

    for day in time_slot_days:
        if len(day["times"]):
            found_date = day["date"]
            print(f"Found time slot on {found_date}")

            times = day["times"].keys()

            for time_slot_id in times:
                new_slot = [
                    day["agenda"],
                    day["date"],
                    day["state"],
                    time_slot_id,
                    day["times"][time_slot_id]["time"],
                ]
                available_time_slots.append(new_slot)

    return available_time_slots


def find_appointments_for_key(months, appointment_key):
    all_available_time_slots = []

    for month in months:
        range_start_date = "-".join(
            [str(month["year"]), str(month["month"]), str(month["first_day_of_month"])]
        )
        range_end_date = "-".join(
            [str(month["year"]), str(month["month"]), str(month["last_day_of_month"])]
        )

        time_slot_days, max_available_days = get_time_slots_for_range(
            range_start_date,
            range_end_date,
            search_type=appointment_key,
        )

        month_available_time_slots = process_time_slots_days(
            time_slot_days=time_slot_days
        )

        if len(month_available_time_slots):
            for slot in month_available_time_slots:
                all_available_time_slots.append(slot)

        time.sleep(1)

    if len(all_available_time_slots):
        print(
            f"Found {len(all_available_time_slots)} available {appointment_key} time slots!"
        )
    else:
        print(f"No {appointment_key} time slots found :(")

    return all_available_time_slots


def send_email(receiver, subject, data_df):
    print(f"Test - receiver: {receiver}, subject: {subject}")


## ------------------ Check all appointment types ------------------

all_appointments_df = pd.DataFrame(
    [],
    columns=["appointment_type", "agenda", "date", "state", "time_slot_id", "time"],
)
month_list = build_month_list(selected_start_date, selected_months_look_ahead)

for appointment_type in appointment_dict.keys():
    appointments = find_appointments_for_key(month_list, appointment_type)

    if len(appointments):
        df = pd.DataFrame(
            appointments,
            columns=["agenda", "date", "state", "time_slot_id", "time"],
        )
        df.insert(0, "appointment_type", appointment_type)

        all_appointments_df = pd.concat([all_appointments_df, df])

print(all_appointments_df)
