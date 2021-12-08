def get_business_yesterday_date(date):
    weekday = date.strftime("%w")
    yesterday = 1
    if weekday == "5":
        yesterday = 3
    return yesterday
