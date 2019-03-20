#!/usr/bin/python3.7

import datetime
import random
import time
from telegram.ext import Updater, CommandHandler
from telegram import KeyboardButton, ReplyKeyboardMarkup, ParseMode
import os
import sqlite3
import praw
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
updater = Updater(token=TELEGRAM_TOKEN)
jobqueue = updater.job_queue
dispatcher = updater.dispatcher
button1 = KeyboardButton('/hello')
button2 = KeyboardButton('/time')
button3 = KeyboardButton('/subreddit')
button4 = KeyboardButton('/help')
button5 = KeyboardButton('/settings')
button6 = KeyboardButton('/start')
button7 = KeyboardButton('/timezone')
button8 = KeyboardButton('/stop')
keyboard = [[button1], [button2], [button3], [button4], [button5], 
            [button6], [button7]]
emojis = ['❤', '😘', '😊', '💕', '🐨', '😍']
goodMorningText = (('Good Morning!!! %s') % (random.choice(emojis)))
reddit = praw.Reddit(client_id=os.environ['REDDIT_API_ID'],
                     client_secret=os.environ['REDDIT_API_SECRET'],
                     user_agent='aaaaaaasasalskaslkalska',
                     username=os.environ['REDDIT_USERNAME'],
                     password=os.environ['REDDIT_PASSWORD'])
default_time = "09:00"
default_timezone = "+08:00"
default_subreddit = 'Eyebleach'

# Returns the time of day at which to send the good morning message, calculated from the time and timezone offset 
def get_job_time_from_time_and_timezone(time, timezone):
    time_hour_offset = int(timezone.split(':')[0])
    time_minute_offset = int(timezone.split(':')[1])
    hour = int(time.split(':')[0]) + time_hour_offset
    if hour > 23:
        hour = hour - 24
    elif hour < 0:
        hour = hour + 24
    minute = int(time.split(':')[1]) + time_minute_offset
    if minute > 59:
        minute = minute - 60
    elif minute < 0:
        minute = minute + 60
        if time_hour_offset > 0:
            hour -= 1
        elif time_hour_offset < 0:
            hour += 1
    print('Message should send at ' + str(hour) + ':' + str(minute) + ' UTC')
    return datetime.time(hour, minute)

# When the program starts, the settings persisted in the job queue are used to create the necessary jobs
def add_jobs_from_db():
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    try:
        with connection:
            cursor.execute("""
                SELECT * FROM BotUsers
            """)
            results = cursor.fetchall()
        for item in results:           
            time = get_job_time_from_time_and_timezone(item['time'], item['timezone'])
            stringId = str(item['id'])
            jobqueue.run_once(send_message, when=time, context=stringId)
        connection.close()
    except Exception as e:
        print('Error in add_jobs_from_db:')
        print(e)
        connection.close()

# Returns all of the current jobs for a user in the job queue.
def get_current_jobs_for_user(userId):
    print('get_current_jobs_callback')
    jobs = jobqueue.jobs()
    jobArray = []
    for i in jobs:
        if i.context == userId:
            jobArray.append(i)
    return jobArray

# Returns the settings for a particular user from the database.
def get_user(userId):
    print('get_user callback')
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    try:
        with connection:
            cursor.execute(
                """
                SELECT * FROM BotUsers WHERE id = :id;
                """, 
                {'id':userId}
            ) 
            result = cursor.fetchall()[0]
        connection.close()
        if result:
            return result
        else:
            return False
    except Exception as e:
        print('Error in get_user:')
        print(e)
        connection.close()
        return False

# Alters a database entry when the user wants to change something.
def update_database(userId, thingToUpdate: str, value: str):
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    try:
        if thingToUpdate in ['time', 'timezone', 'subreddit']:
            with connection:
                cursor.execute("""
                    UPDATE BotUsers SET {0} = :value WHERE id = :userId;
                """.format(thingToUpdate), {'value':value, 'userId':userId})
            connection.close()
            return True
        else:
            print('Bad type')
            raise TypeError('Incorrect value passed to thingToUpdate parameter')
    except Exception as e:
        print('Error in update_database:')
        print(e)
        connection.close()
        return False

# Callback for the daily job.
def send_message(bot, job):
    print('Send_message callback')
    try:
        user = get_user(job.context)
        for i in reddit.subreddit(user['subreddit']).top('hour', limit=1):
            title = i.title
            url = i.url
            permalink = 'reddit.com' + i.permalink
        bot.send_message(chat_id=user['id'], text=goodMorningText + " Here's your daily link: \n" + title + '\n' + url + "\nView the comments: \n" + permalink)
        user = get_user(job.context)
        if user:
            stringId = str(user['id'])
            jobqueue.run_once(send_message, when=get_job_time_from_time_and_timezone(user['time'], user['timezone']), context=stringId)
            print('Set the job up again successfully')
    except Exception as e:
        print('Error in send_message:')
        print(e)
        print('Error completing the job for user ' + job.context)

# Changes the message time.
def update_dailymsg_time(bot, update, args):
    print('update_dailymsg_time callback')
    try:
        time = args[0]
        datetime.time.fromisoformat(time)
        success = update_database(update.message.chat_id, 'time', time)
        if success:
            user = get_user(update.message.chat_id)
            current_jobs = get_current_jobs_for_user(user['id'])
            for i in current_jobs:
                i.schedule_removal()
            jobqueue.run_once(send_message, when=get_job_time_from_time_and_timezone(user['time'], user['timezone']), context=user['id'])
            bot.send_message(chat_id=update.message.chat_id, text="Set the message time to " + time + " successfully.")
        else:
            raise TypeError('Error while updating database')
    except Exception as e:
        print('Error in update_dailymsg_time:')
        print(e)
        bot.send_message(chat_id=update.message.chat_id, text="Invalid time, try again.")

# Says hello to the user
def sayHello(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Hello! " + random.choice(emojis))

# On command /start, a user is added to the database with default settings, and a job is created for them.
def start_reply(bot, update):
    print('Start_reply callback')
    user = get_user(update.message.chat_id)
    if user:
        bot.send_message(chat_id=update.message.chat_id, text="You are already in the database. Your settings: " + 
                            "\nMessage time: " + user['time'] + "\nSubreddit: " + user['subreddit'] + "\nTimezone: " + 
                            user['timezone'] + "\nFor instructions on how to change your settings, use the /help command.")
    else:
        connection = sqlite3.connect('database.db')
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        try:
            with connection:
                cursor.execute("""
                    INSERT INTO BotUsers (id, time, subreddit, timezone)
                        VALUES (:id, :time, :subreddit, :timezone);
                """, {
                    'id':update.message.chat_id,
                    'time': default_time,
                    'subreddit':default_subreddit,
                    'timezone':default_timezone
                })
            time = get_job_time_from_time_and_timezone(default_time, default_timezone)
            jobqueue.run_once(send_message, when=time, context=update.message.chat_id)
            bot.send_message(chat_id=update.message.chat_id, text="Added you to the database with the default settings: " + 
                                                                "\nMessage time: " + default_time + "\nSubreddit: " + default_subreddit + "\nTimezone: " + 
                                                                default_timezone + "\n For instructions on how to change your settings, use the /help command.")
            connection.close()
        except Exception as e:
            print('Error in start_reply:')
            print(e)
            connection.close()
            print('Error when trying to set up a new user in the database')

# Sends a help message to the user
def help_reply(bot, update):
    bot.send_message(
        chat_id=update.message.chat_id,
        text="This bot will send you a good morning message at a time of your choosing, accompanied by a post from a subreddit of your choosing." +
        "\n\nTo view your current settings, use the /settings command." + "\n\nTo change the time of day you receive your message, use the /time command in the format /time HH:MM."
        + """\nFor example, to change the message time to 9AM, you would send the following message to the bot (without quotation marks): "/time 09:00" """
        + "\n\nBy default, the bot sends messages according to AWST (UTC +08:00, Perth, Taipei, Beijing). If this is not your timezone, you can use the /timezone command"
        +  "in the format /timezone +/-HH:MM. \nFor example, to change the timezone to Sydney time, you would send the following message to the bot (without quotation marks):"
        +  """ "/timezone +10:00" """
        + "\n\nUse the commands /daylightsavings_on and /daylightsavings_off respectively to quickly add or remove an hour from your timezone to account for daylight savings."
        + "\n\nTo change the subreddit from which the bot finds links for you, you can use the /subreddit command in the format /subreddit <subreddit>."
        + """\nFor example, to change the subreddit to r/pics, you would send the following message to the bot (without quotation marks): "/subreddit pics" """
        + "\n\nTo stop the bot from sending you any more good morning messages, use the /stop command. You can start again with /start."
    )

# Changes the user's subreddit
def change_subreddit(bot, update, args):
    try: 
        for i in reddit.subreddit(args[0]).top('day', limit=1):
            print(i.url)
        success = update_database(update.message.chat_id, 'subreddit', args[0])
        if success:
            user = get_user(update.message.chat_id)
            current_jobs = get_current_jobs_for_user(user['id'])
            for i in current_jobs:
                i.schedule_removal()
            jobqueue.run_once(send_message, when=get_job_time_from_time_and_timezone(user['time'], user['timezone']), context=user['id'])
            bot.send_message(chat_id=update.message.chat_id, text="Set your subreddit to r/" + args[0] + " successfully.")
        else:
            raise ValueError
    except Exception as e:
        print('Error in change_subreddit:')
        print(e)
        bot.send_message(chat_id=update.message.chat_id, text="Invalid subreddit, try again.")

# Sends a summary of the user's current settings to them
def view_settings(bot, update):
    try:
        user = get_user(update.message.chat_id)
        print(get_current_jobs_for_user(user['id']))
        bot.send_message(chat_id=user['id'], text="Here are your current settings: \
            \nTime: " + user['time'] + "\nSubreddit: " + user['subreddit'] + "\nTimezone: "
            + user['timezone'])
    except Exception as e:
        print(e)
        bot.send_message(chat_id=update.message.chat_id, text="Couldn't find any settings for you. Try /start to get set up with the default settings.")

# Changes the user's timezone
def change_timezone(bot, update, args):
    try:
        timezone = args[0]
        if timezone[0] not in ['-', '+'] or len(timezone) != 6:
            raise ValueError('1')
        datetime.time.fromisoformat(timezone[1:])
        success = update_database(update.message.chat_id, 'timezone', timezone)
        if success:
            user = get_user(update.message.chat_id)
            current_jobs = get_current_jobs_for_user(user['id'])
            for i in current_jobs:
                i.schedule_removal()
            jobqueue.run_once(send_message, when=get_job_time_from_time_and_timezone(user['time'], user['timezone']), context=user['id'])
            bot.send_message(chat_id=update.message.chat_id, text="Set your timezone offset to " + timezone + " successfully.")
        else:
            raise ValueError('2')
    except Exception as e:
        print('Error in change_timezone:')
        print(e)
        bot.send_message(chat_id=update.message.chat_id, text="Invalid time, try again.")

# Deletes the user's information from the database and stops any jobs associated with them in the queue.
def stop_jobs(bot, update):
    try:
        connection = sqlite3.connect('database.db')
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        with connection:
            cursor.execute("""
                DELETE FROM BotUsers WHERE id = :id;
            """, {'id':update.message.chat_id})
        for job in get_current_jobs_for_user(update.message.chat_id):
            job.schedule_removal()
        bot.send_message(chat_id=update.message.chat_id, text="Deleted your settings from the database successfully. You won't receive good morning messages anymore. \
                                                                To start again, use /start.")
        connection.close()
    except Exception as e:
        print('Error in stop_jobs:')
        print(e)
        connection.close()
        bot.send_message(chat_id=update.message.chat_id, text="There was an issue trying to delete your settings.")

# Adds an hour to the timezone for the user, to account for daylight savings.
def daylightsavings_on(bot, update):
    try:
        user = get_user(update.message.chat_id)
        newTime = int(user['timezone'][1:3]) + 1
        if newTime > 23:
            newTime = newTime - 24
        elif newTime < 10:
            newTime = "0" + str(newTime)
        newTimezone = user['timezone'][0] + str(newTime) + ':' + user['timezone'][4:]
        change_timezone(bot, update, [newTimezone])
    except Exception as e:
        print('Error in daylightsavings_on:')
        print(e)
        bot.send_message(chat_id=update.message.chat_id, text="Invalid timezone, try again.")

# Subtracts an hour from the timezone for the user, to account for daylight savings.
def daylightsavings_off(bot, update):
    try:
        user = get_user(update.message.chat_id)
        newTime = int(user['timezone'][1:3]) - 1
        if newTime < 0:
            newTime = newTime + 24
        if newTime < 10:
            newTime = "0" + str(newTime)
        newTimezone = user['timezone'][0] + str(newTime) + ':' + user['timezone'][4:]
        change_timezone(bot, update, [newTimezone])
    except Exception as e:
        print('Error in daylightsavings_off:')
        print(e)
        bot.send_message(chat_id=update.message.chat_id, text="Invalid timezone, try again.")

# Tell the user about some potential subreddits
def recommend_subreddits(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=(
        "Here's a list of some of the most active subreddits (excluding NSFW subreddits): "
        + "\n*Wallpapers* - Wallpapers"
        + "\n*EarthPorn* - Amazing images of light and landscape"
        + "\n*News* - All news, US and international."
        + "\n*Pics* - Reddit pics"
        + "\n*Videos* - /r/videos"
        + "\n*NBA* - NBA"
        + "\n*Aww* - A subreddit for cute and cuddly pictures"
        + "\n*Hiphopheads* - Hiphop music news and discussion"
        + "\n*Politics* - Political news and discussion. US-centric"
        + "\n*Worldnews* - International news"
        + "\n*Australia* - Australian news, politics and misc. content"
        ), parse_mode=ParseMode.MARKDOWN)
    

# List some common timezones
def recommend_timezones(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=(
        "Here's a list of some of the most common timezones: "
        + "\n*-12:00* - Baker Island, Howland Island"
        + "\n*-11:00* - American Samoa, US Minor Outlying Islands, Niue"
        + "\n*-10:00* - French Polynesia, Cook Islands, Aleutian Islands, Hawaii, Johnston Atoll"
        + "\n*-09:30* - Marquesas Islands (France)"
        + "\n*-09:00* - Gambier Islands (France), Alaska"
        + "\n*-08:00* - Los Angeles, Vancouver, Tijuana"
        + "\n*-07:00* - Phoenix, Edmonton, Juarez"
        + "\n*-06:00* - Chicago, Mexico City, Winnipeg"
        + "\n*-05:00* - New York, Lima, Toronto, Bogota, Havana"
        + "\n*-04:00* - Santiago, Caracas, La Paz, Halifax"
        + "\n*-03:30* - Newfoundland and Labrador"
        + "\n*-03:00* - Sao Paulo, Buenos Aires, Montevideo"
        + "\n*-02:00* - Fernando de Noronha, South Georgia and South Sandwich Islands"
        + "\n*-01:00* - Cabo Verde, Greenland, Azores Islands"
        + "\n*-00:00* - London, Accra, Dakar, Dublin, Lisbon"
        + "\n*+01:00* - Lagos, Kinsasha, Casablanca, Berlin, Rome, Paris, Madrid, Warsaw"
        + "\n*+02:00* - Cairo, Khartoum, Johannesburg, Kiev, Bucharest, Jerusalem, Athens, Kaliningrad"
        + "\n*+03:00* - Moscow, Istanbul, Riyadh, Baghdad, Nairobi, Minsk, Doha"
        + "\n*+03:30* - Tehran"
        + "\n*+04:00* - Dubai, Baku, Samara"
        + "\n*+04:30* - Kabul"
        + "\n*+05:00* - Karachi, Tashkent, Yekaterinburg"
        + "\n*+05:30* - Delhi, Colombo"
        + "\n*+05:45* - Nepal"
        + "\n*+06:00* - Almaty, Dhaka, Omsk"
        + "\n*+06:30* - Myanmar"
        + "\n*+07:00* - Jakarta, Bangkok, Ho Chi Minh City, Krasnoyarsk"
        + "\n*+08:00* (default) - China, Hong Kong, Kuala Lumpur, Singapore, Taipei, Perth, Manila, Makassar, Irkutsk"
        + "\n*+08:45* - Eucla"
        + "\n*+09:00* - Tokyo, Seoul, Pyongyang, Ambon, Yakutsk"
        + "\n*+09:30* - Adelaide, Darwin, Broken Hill"
        + "\n*+10:00* - Sydney, Melbourne, Brisbane, Port Moresby, Vladivostok"
        + "\n*+10:30* - Lord Howe Island"
        + "\n*+11:00* - New Caledonia, Solomon Islands, Norfolk Island, Bougainville, Vanuatu, Magadan"
        + "\n*+12:00* - New Zealand, Wallis and Futuna, Fiji, Nauru, Tuvalu"
        + "\n*+12:45* - Chatham Island"
        + "\n*+13:00* - Tokelau, Samoa, Tonga"
        + "\n*+14:00* - Line Islands"
        ), parse_mode=ParseMode.MARKDOWN)


dispatcher.add_handler(CommandHandler('time', update_dailymsg_time, pass_args=True))
dispatcher.add_handler(CommandHandler('hello', sayHello))
dispatcher.add_handler(CommandHandler('start', start_reply))
dispatcher.add_handler(CommandHandler('help', help_reply))
dispatcher.add_handler(CommandHandler('subreddit', change_subreddit, pass_args=True))
dispatcher.add_handler(CommandHandler('settings', view_settings))
dispatcher.add_handler(CommandHandler('timezone', change_timezone, pass_args=True))
dispatcher.add_handler(CommandHandler('daylightsavings_on', daylightsavings_on))
dispatcher.add_handler(CommandHandler('daylightsavings_off', daylightsavings_off))
dispatcher.add_handler(CommandHandler('stop', stop_jobs))
dispatcher.add_handler(CommandHandler('recommend_subreddits', recommend_subreddits))
dispatcher.add_handler(CommandHandler('recommend_timezones', recommend_timezones))

def main():
    updater.start_polling()
    add_jobs_from_db()
    

if __name__ == '__main__':
    main()