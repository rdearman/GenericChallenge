#!/usr/bin/python
#!/usr/bin/env python

#from  mastodon import Mastodon
from mastodon import Mastodon
import configparser
import mysql.connector
from mysql.connector import Error
from mysql.connector import errorcode
import time
import getpass
import sys
import re
import traceback
from datetime import datetime
from mysql.connector import errorcode
import subprocess


# -------------------
# INSERT INTO Preferences (Name,Value) Values ('last_mastodon_check_time', now());
# -------------------

# Method to read config file settings
def read_config():
    config = configparser.ConfigParser()
    config.read('configurations.ini')
    return config

config = read_config()

client_id=config['MASTODON']['CLIENT_ID']
client_secret=config['MASTODON']['CLIENT_SECRET']
access_token=config['MASTODON']['ACCESS_TOKEN']
api_base_url=config['MASTODON']['API_BASE_URL']


def connect_to_mastodon():
    # Connect to the Mastodon API using the credentials in the configuration file
    mastodon = Mastodon(
        client_id,
        client_secret,
        access_token,
        api_base_url
    )
    return mastodon

def connect_to_database():
    # Connect to the MySQL database using the credentials in the configuration file
    cnx = mysql.connector.connect(
        host=config['MYSQL']['DB_HOST'],
        user=config['MYSQL']['DB_USER'],
        password=config['MYSQL']['DB_PASSWORD'],
        database=config['MYSQL']['DB_NAME']
    )
    
    return cnx

def get_last_check_time(cnx):
    # Get the timestamp of the last time the program ran from the database
    cursor = cnx.cursor()
    query = "SELECT Value FROM Preferences WHERE Name = 'last_mastodon_check_time'"
    cursor.execute(query)
    result = cursor.fetchone()
    last_check_time = result[0] if result else None
    cursor.close()
    
    return last_check_time

def set_last_check_time(cnx, last_check_time):
    # Update the timestamp of the last time the program ran in the database
    cursor = cnx.cursor()
    query = "UPDATE Preferences SET Value = %s WHERE Name = 'last_mastodon_check_time'"
    cursor.execute(query, (last_check_time,))
    cnx.commit()
    cursor.close()

def store_message_and_sender_info(cnx, message, sender):
    # Store the message and sender information in the database
    cursor = cnx.cursor()
    query = "INSERT INTO messages (sender_id, sender_username, text, timestamp) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (sender['id'], sender['username'], message['text'], message['timestamp']))
    cnx.commit()
    cursor.close()

def follow_sender(mastodon, cnx, sender):
    # Follow the sender of the message if they are not already being followed
    cursor = cnx.cursor()
    query = "SELECT COUNT(*) FROM followers WHERE user_id = %s"
    cursor.execute(query, (sender['id'],))
    result = cursor.fetchone()
    if result[0] == 0:
        mastodon.follow(sender['id'])
        query = "INSERT INTO followers (user_id, username, display_name) VALUES (%s, %s, %s)"
        cursor.execute(query, (sender['id'], sender['username'], sender['display_name']))
        cnx.commit()
    cursor.close()


def get_direct_messages(mastodon):
    # Get all status messages from the user's timeline
    #statuses = mastodon.timeline_home()
    statuses = mastodon.timeline()
    print(statuses)
    # Filter the status messages to only include direct messages
    direct_messages = [status for status in statuses if status["visibility"] == "direct"]
    
    return direct_messages


def respond_to_message(mastodon, message):
    # Respond to the message with a thank you message
    response = "Thank you for your message!"
    mastodon.status_post(status=response, in_reply_to_id=message["id"], visibility="direct")



# main function
def main():
    mastodon = connect_to_mastodon()
    cnx = connect_to_database()
    messages = get_direct_messages(mastodon)
    
    # print("process each direct message")
    for message in messages:
        # store message and sender's profile information
        store_message_and_sender_info(message)
        
        # follow the sender
        follow_sender(mastodon, message['account']['id'])
        
        #print("{:s}".format(message))
        respond_to_message(mastodon, message)

    print ("Disconnected\n")
    return 0
        
if __name__ == '__main__':
    try:
        exit_code = main()
    except Exception:
        traceback.print_exc()
        exit_code = 1
    sys.exit(exit_code)

