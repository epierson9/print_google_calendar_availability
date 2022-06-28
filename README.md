# print_google_calendar_availability

Python script which prints out a summary of your free slots from your Google calendar(s) so you can paste into a scheduling email. Contact Emma Pierson (emma.pierson@cornell.edu) with any questions. 

![Sample usage](sample_usage.png?raw=true "sample usage")

# Setup

1. Clone this repo. 

2. Install the packages you need: `pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib`

3. Get Google credentials. You want to create credentials for a desktop application, as described [in this link](https://developers.google.com/workspace/guides/create-credentials#oauth-client-id) - click on "Desktop app".

4. Change the constants at the [top of the script](https://github.com/epierson9/print_google_calendar_availability/blob/ddb2a171eac7b81cf9e14dc421ea5b032979d262/print_availability.py#L17). 

# Usage
 
Two usages: 

Print availabilities on specific dates: `python print_availability.py 2022-03-05 2022-03-12`

Just print out availability for next three weeks: `python print_availability.py`

I added lines to my .bashrc to alias both these functions so I don't have to cd to the directory: 

```
alias print_availability='python /Users/emmapierson/Desktop/print_google_calendar_availability/print_availability.py'
print_availability_with_dates() {python /Users/emmapierson/Desktop/print_google_calendar_availability/print_availability.py "$1" "$2"}
```

so I can just run `print_availability_with_dates 2022-06-29 2022-06-30` and `print_availability` from the command line. 

# Disclaimer

This seems to work fine for the 4 weeks of my own calendar I tested it on, but open a GitHub issue if you find any bugs and don't get mad if you miss an important meeting :) 