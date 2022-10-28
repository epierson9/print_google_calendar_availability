from __future__ import print_function

import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from IPython import embed
import pytz
from dateutil.parser import isoparse
import sys

# script modified from https://developers.google.com/calendar/api/quickstart/python

tz = pytz.timezone('America/New_York') # timezone to use
START_HOUR = 10 # start time (24 hour time) of availability period
END_HOUR = 17 # end time (24 hour time) of availability period
CALENDAR_IDS = ['primary', 'ep432@cornell.edu'] # Google calendars to draw from
MIN_TIME_INTERVAL_LENGTH_IN_MINUTES = 30 # don't print out availabilities shorter than this
BASE_PATH = '/Users/emmapierson/Desktop/print_google_calendar_availability/' # name of folder where you store script and credentials. 
CREDENTIALS_NAME_DOWNLOADED_FROM_GOOGLE = 'google_calendar_credentials.json' # filename you use for credentials. 
NO_MEETING_DAYS = ['Friday', 'Saturday', 'Sunday']

if len(sys.argv) == 3:
    start_datestring = [int(a) for a in sys.argv[1].split('-')]
    end_datestring = [int(a) for a in sys.argv[2].split('-')]
    START_DATETIME = tz.localize(datetime.datetime(*start_datestring, START_HOUR))
    END_DATETIME = tz.localize(datetime.datetime(*end_datestring, END_HOUR))
else:
    assert len(sys.argv) == 1
    today = datetime.date.today()
    three_weeks_later = today + datetime.timedelta(days=21)
    START_DATETIME = tz.localize(datetime.datetime(today.year, today.month, today.day, START_HOUR))
    END_DATETIME = tz.localize(datetime.datetime(three_weeks_later.year, three_weeks_later.month, three_weeks_later.day, END_HOUR))

print("*****Printing availabilities between %s and %s of at least %i minutes" % ('-'.join(str(START_DATETIME).split('-')[:-1]), '-'.join(str(END_DATETIME).split('-')[:-1]), MIN_TIME_INTERVAL_LENGTH_IN_MINUTES))
print("Drawing from calendars with IDs", CALENDAR_IDS, 'using timezone', tz, 'skipping days', NO_MEETING_DAYS)
print("Feel free to change all these options by changing the relevant variables at the top of the script")
print("Your availabilities are")
# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def main():
    creds = None
    # authenticate for calendar access
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(os.path.join(BASE_PATH, 'token.json')):
        creds = Credentials.from_authorized_user_file(os.path.join(BASE_PATH, 'token.json'), SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if (not creds) or (not creds.valid) or (creds and creds.expired and creds.refresh_token):
        flow = InstalledAppFlow.from_client_secrets_file(
            os.path.join(BASE_PATH, CREDENTIALS_NAME_DOWNLOADED_FROM_GOOGLE), SCOPES)
        creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(os.path.join(BASE_PATH, 'token.json'), 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API and get a list of all events from all calendars. 
        all_events = []
        for calendar_id in CALENDAR_IDS:
            events_result = service.events().list(calendarId=calendar_id, 
                                              timeMin=(START_DATETIME - datetime.timedelta(days=1)).isoformat(),
                                              timeMax=(END_DATETIME + datetime.timedelta(days=1)).isoformat(),
                                              singleEvents=True,
                                              orderBy='startTime').execute()
            all_events = all_events + events_result.get('items', [])

        # parse the Google API response into a single list of datetimes with starts and ends. 
        unified_busy_list = []
        parse_string = "%Y-%m-%dT%H:%M:%S%z"
        for i in range(len(all_events)):
            if 'dateTime' not in all_events[i]['start']:
                # skip these events because they're often multiday events. You may wish to uncomment this. 
                continue
            unified_busy_list.append({'start':datetime.datetime.strptime(all_events[i]['start']['dateTime'] , parse_string), 
                                    'end':datetime.datetime.strptime(all_events[i]['end']['dateTime'] , parse_string)})
        unified_busy_list = sorted(unified_busy_list, key = lambda x:x['start'])

        # generate candidate free intervals by looping over weekdays. Default interval size is 15 min. 
        time_interval_delta = datetime.timedelta(minutes=15)
        all_potential_free_intervals = []
        current_time = START_DATETIME
        while current_time < END_DATETIME:
            if current_time.hour == END_HOUR: # at the end of the day, go to the next day. 
                current_time = current_time + datetime.timedelta(days=1)
                current_time = tz.localize(datetime.datetime(current_time.year, current_time.month, current_time.day, START_HOUR))
            while current_time.strftime("%A") in NO_MEETING_DAYS: 
                current_time = current_time + datetime.timedelta(days=1)
                current_time = tz.localize(datetime.datetime(current_time.year, current_time.month, current_time.day, START_HOUR))
            all_potential_free_intervals.append([current_time, current_time + time_interval_delta])
            current_time = current_time + time_interval_delta

        # filter candidate free intervals for no overlap with start/end events
        confirmed_free_intervals = []
        for interval_start, interval_end in all_potential_free_intervals:
            is_free = True
            assert interval_start < interval_end

            for busy_interval in unified_busy_list:
                assert busy_interval['start'] < busy_interval['end']
                no_overlap = (interval_end <= busy_interval['start']) or (interval_start >= busy_interval['end'])
                if not no_overlap:
                    is_free = False 
                    break
            if is_free:
                confirmed_free_intervals.append([interval_start, interval_end])
        assert sorted(confirmed_free_intervals, key = lambda x:x[0]) == confirmed_free_intervals
        if len(confirmed_free_intervals) == 0:
            print("No free time in this interval, sorry")
            return
        

        # merge together adjacent intervals. 
        merged_intervals = []
        merged_start = confirmed_free_intervals[0][0]
        merged_end = confirmed_free_intervals[0][1]
        for next_interval in confirmed_free_intervals[1:]:
            if next_interval[0] == merged_end:
                merged_end = next_interval[1] # keep extending the interval
            else:
                if (merged_end - merged_start).seconds >= (MIN_TIME_INTERVAL_LENGTH_IN_MINUTES * 60):
                    merged_intervals.append([merged_start, merged_end])
                merged_start, merged_end = next_interval
        if (merged_end - merged_start).seconds >= (MIN_TIME_INTERVAL_LENGTH_IN_MINUTES * 60):
            merged_intervals.append([merged_start, merged_end]) # don't forget to add last interval

        # print out availabilities by day in nice format
        intervals_by_date = {}
        for interval in merged_intervals:
            date = datetime.datetime(interval[0].year, interval[0].month, interval[0].day)
            if date not in intervals_by_date:
                intervals_by_date[date] = []
            intervals_by_date[date].append(interval[0].strftime("%-I:%M") + '-' + interval[1].strftime("%-I:%M"))
            
        for date in sorted(intervals_by_date.keys()):
            datestring = date.strftime("%a, %B %d")
            if len(intervals_by_date[date]) == 1:
                timestrings = intervals_by_date[date][0]
            else:
                if len(intervals_by_date[date]) == 2:
                    comma_string = ' or '
                else:
                    comma_string = ', or '
                timestrings = ', '.join(intervals_by_date[date][:-1]) + comma_string + intervals_by_date[date][-1]
            print(datestring + ': ' + timestrings)

    except HttpError as error:
        print('An error occurred: %s' % error)


if __name__ == '__main__':
    main()