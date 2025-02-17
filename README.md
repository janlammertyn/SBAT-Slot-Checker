
# Exam Availability Checker

This Python script checks for available timeslots between two specified dates on the [rijbewijs.sbat.be](https://rijbewijs.sbat.be) API.  
It then posts any found timeslots to a specified Discord channel via a webhook.
This was made for any desperate last-minute booking. 

## How It Works

1.  **JWT Authentication**
    -   The script stores a JWT in `token.txt`. If no valid token is found or the existing token is expired, it automatically re-authenticates using credentials you provide.
2.  **Single Request Per Center**
    -   For each configured exam center, the script sends a `POST /praktijk/api/exam/available` request (with a `startDate` in the body).
3.  **Filtering**
    -   Locally filters all returned timeslots so that **only** those within your specified **start** and **end** date range are included.
4.  **Discord Notification**
    -   If it finds any matching slots, the script compiles a message listing exam centers and times and posts it to your Discord webhook.

## Requirements

-   Python 3
-   Dependencies:
    -   `requests` (`pip install requests`)
    -   `pyjwt` (`pip install pyjwt`)

## Configuration

Inside the script, you **must replace** certain variables with values that match your situation:

1.  **`LOGIN_DATA`**
    -   Replace the `"username"` and `"password"` fields with **your** login credentials.
    -   Example: `LOGIN_DATA = { "username": "your_email@example.com", "password": "YOUR_PASSWORD" }`
2. **`DISCORD_WEBHOOK_URL`**
	-   Replace with your own Discord webhook URL from the channel where you want notifications.
	-   Example: `DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/123456/ABCDEF"`
3. **`REQUEST_BODY_DATE`**
	- Time you want the API request to start searching from.
    - Is now set to the date/time of running
    - Replace with specific date/time if you wish:
	-   Example: `REQUEST_BODY_DATE = "2025-02-06T00:00"`
4. **`START_DATE` and `END_DATE`**
	-   Replace these with the date range you want to filter on _after_ receiving data from the API.
	-   Example: `START_DATE = datetime(2025, 2, 21, 0, 0, 0) END_DATE = datetime(2025, 2, 27, 23, 59, 59)`
## Scheduling (Example: cron)
To run the script every 20 minutes, add a line to your crontab:
`crontab -e`
`*/20 * * * * /absolute/path/to/main.py >> /absolute/path/to/logfile 2>&1`
