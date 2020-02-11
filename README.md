# Good Morning Telegram Bot

A Telegram bot written in Python that sends out a personalised good morning message to each user, daily.

## To use, search for @good_morning_zaoshanghao_bot on Telegram.


### Introduction


I added an SQLite database to record each individual user's settings, and expanded the features of the bot significantly.
I turned the code from what was originally, to be perfectly honest, a bit of a mess, into a more clean and functional setup.
I broke down each task into its own function and labelled them appropriately. This made debugging a breeze because problems could 
easily be isolated to their particular functions. I also increased the efficiency and performance of the bot, and where I was previously
making a GET request to reddit and parsing the HTML to get the daily link, version 2 of the bot simply makes calls to the Reddit API.


### Functionality

The bot will send a message to the user at a particular time (9AM by default), in a particular timezone (UTC +08:00 by default), 
wishing the user a good morning. To go along with this, the bot will also send the user a popular link from a particular subreddit
(r/eyebleach by default) with every good mornning message. To try it out, simply search @good_morning_zaoshanghao_bot on Telegram.
When you start a conversation with the bot, he'll help you get set up.

### Commands

* /start - Upon this command, the bot will check whether you are already registered in the database. If you are not, it will 
put you in there with the default settings. If you are, it will tell you your current settings.

* /time <HH:MM> - This command will change the time of day that the bot sends the message.

* /subreddit <subreddit> - This command will change the subreddit from which the bot requests the current top post for your daily
message.

* /timezone <+/-HH:MM> - This command will change your timezone in the database.

* /help - The bot will send you a message detailing how to use the bot and what all the different commands are for.

* /settings - The bot will check what your current settings are in the database and return them to you.

* /hello - The bot will say hello.

* /daylightsavings_on - The bot will add 1 hour to your timezone offset. This is a shortcut command to account for daylight savings.

* /daylightsavings_off - The bot will subtract 1 hour from your timezone offset. This is a shortcut command to account for daylight savings.

* /stop - This will delete your entry in the database and the bot will stop sending you good morning messages until you send /start again.

* /recommend_subreddits - The bot will give you a list of recommended or popular subreddits that you may be interested in. Handy for users unfamiliar with reddit.

* /recommend_timezones - The bot will return a list of the most common timezones. Handy for users who are not familiar with their timezone in UTC offset format.



