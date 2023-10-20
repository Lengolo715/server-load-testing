import json
import requests
import time
import threading
import concurrent.futures
import datetime
import random

response_total_api_time = 0
api_requests_total = 0
timed_out_requests_total = 0
passed_request_total = 0
max_workers = 400 # for threading
base_capacity = 32  #change to meet the base capacity of the redshift server
average_time = 0
test_runs_total = 0
account_number_list = []
x_api_key = os.environ.get("X_API_KEY")
x_apigw_api_id = os.environ.get("X_APIGW_API_ID")
# Update file paths with relative paths
api_call_logs_path = "api_call_logs.json"
test_logs_path = "test_logs.txt"

#----------------------------------------------------------------------------------

def random_snapshot_date():
    start = datetime.date(2020, 1, 1)
    end = datetime.date(2023, 4, 30)
    days_range = (end-start).days
    random_days = random.randint(0, days_range)
    random_date = str(start + datetime.timedelta(days=random_days))
    return random_date
#----------------------------------------------------------------------------------

def api_request(account_number):

    snap_shot_date = random_snapshot_date()
    # snap_shot_date = "2020-07-01"
    response = None

    url = f"https://vpce.amazonaws.com/sdlc/redshift/?account_number={account_number}&snap_shot_date={snap_shot_date}"
    payload = {}
    headers = {
        'x-api-key': x_api_key,
        'x-apigw-api-id': x_apigw_api_id
    }
    try:
        response = requests.request("GET", url, headers=headers, data=payload)
        response_time = response.elapsed.total_seconds()
    except Exception as e:
        print(e)
    return account_number, snap_shot_date, response.text, response_time
#----------------------------------------------------------------------------------

def read_from_api_log():
    try:
        with open(api_call_logs_path, 'r') as file:
            existing_data = json.load(file)
    except FileNotFoundError as e:
        print("Read from file method failed: \r", e)
    return existing_data
#----------------------------------------------------------------------------------

def write_to_api_log(account_number, snap_shot_date, response_time):

    existing_data = read_from_api_log()
    api_call = f"API call for account number: {account_number} and snapshot date: {snap_shot_date} response time is {response_time} seconds."
    existing_data["api_request_response_time"].append(api_call)
    try:
        with open(api_call_logs_path, 'w') as file:
            json.dump(existing_data, file, indent=4)
    except Exception as e:
        print("Write to file method failed: \r", e)

#----------------------------------------------------------------------------------

def read_from_test_log():
    test_number = 0
    try:
        with open(test_logs_path, "r") as file:
            for line in file:
                # Check if the line starts with "Test Number"
                if line.startswith("Test Number"):
                    # Split the line by ":" and get the second part, which is the test number
                    test_number += 1
                else:
                    test_number = test_number
    except FileNotFoundError as e:
        print("Read from file method failed: \r", e)
    return test_number
#----------------------------------------------------------------------------------

def write_test_results():
    test_number =  read_from_test_log() + 1
    global base_capacity
    global max_workers
    if timed_out_requests_total > 0 :
        test_status = "Fail"
    else:
        test_status = "Pass"
    test_results = \
f"""
Date:                               {datetime.date.today()}
Test Number:                        {test_number}
Test Case (GET API):                {base_capacity} RPU base capacity tested with {api_requests_total} API requests using {max_workers} threads.
---------------------------
Results
---------------------------
Status:                             {test_status}
Total Requests:                     {api_requests_total}
Passed Requests:                    {passed_request_total}
Failed Requests:                    {timed_out_requests_total}
Average Response Time (s):          {average_time}
>>>>>>>>>>>>>>>>>
"""
    with open('Your Path', 'a') as file:
        file.write(test_results)
    return print(test_results)
#----------------------------------------------------------------------------------

def main():
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(api_request, account_number) for account_number in account_number_list]
        concurrent.futures.wait(futures)
        for future in concurrent.futures.as_completed(futures):
            results = future.result()
            account_number = results[0]
            snap_shot_date = results[1]
            api_response_text = results[2]
            response_time = results[3]
            global timed_out_requests_total
            global response_total_api_time
            global api_requests_total
            global passed_request_total
            response_total_api_time += response_time
            api_requests_total += 1
            if "Endpoint request timed out" in api_response_text:
                # print(api_response_text)
                timed_out_requests_total += 1
            elif  "HTTPSConnectionPool" in api_response_text:
                # print(api_response_text)
                timed_out_requests_total += 1
            else:
                passed_request_total += 1
                # print(api_response_text)
            write_to_api_log(account_number, snap_shot_date, response_time)

    except Exception as e:
        print("Error in main: ", e)
#----------------------------------------------------------------------------------
if __name__ == "__main__":
    main()
    average_time = int(response_total_api_time)/api_requests_total
    write_test_results()
