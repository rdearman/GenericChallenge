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
# Fails on DB inserts, need to use the superchallenge DB for now. 


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

def store_message_and_sender_info(cnx, content, sender_id, sender_username, sender_displayname):
    # Store the message and sender information in the database
    now = datetime.now()
    tmstamp = now.strftime("%Y/%m/%d %H:%M:%S")
    cursor = cnx.cursor()
    query = "INSERT INTO messages (sender_id, sender_username, text, timestamp) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (sender_id, sender_username, content, tmstamp ))
    cnx.commit()
    cursor.close()

def follow_sender(mastodon, cnx, sender):
    # Follow the sender of the message if they are not already being followed
    cursor = cnx.cursor()
    query = "SELECT COUNT(*) FROM followers WHERE user_id = %s"
    cursor.execute(query, (sender['id'],))
    result = cursor.fetchone()
    if result[0] == 0:
        mastodon.account_follow(sender)
        query = "INSERT INTO followers (user_id, username, display_name) VALUES (%s, %s, %s)"
        cursor.execute(query, (sender['id'], sender['username'], sender['display_name']))
        cnx.commit()
    cursor.close()


def respond_to_message(mastodon, message):
    # Respond to the message with a thank you message
    response = "Thank you for your message!"
    mastodon.status_post(status=response, in_reply_to_id=message["id"], visibility="direct")


def scrub_message(string):
    # parse the message and remove extra rubbish
    clean = re.compile('<.*?>')
    tmp = re.findall('\'content\': \'(\w+)\', \'filtered\'', string)
    tmp = ''.join(str(x) for x in tmp)
    return re.sub(clean, '', tmp)

def get_sender(string):
    # parse the message and remove extra rubbish
    sender_info = []
    clean = re.compile('<.*?>')
    uid = re.findall('\[\{\'id\': ([\d]+),', string)
    uid = ''.join(str(x) for x in uid)
    sender_info.append(uid)
    uname = re.findall('\'username\': \'([\w]+)\',', string)
    uname = ''.join(str(x) for x in uname)
    sender_info.append(uname)
    dname = re.findall('\'display_name\': \'([\w]+)\',', string)
    dname = ''.join(str(x) for x in dname)
    sender_info.append(dname)
    return sender_info
    #return re.sub(clean, '', tmp)

    
# main function
def main():
    mastodon = connect_to_mastodon()
    cnx = connect_to_database()
    response = "Thank you for your message!"
    messages = mastodon.conversations()
    
    for message in messages:
        #get message id
        msgId = message['id']
        
        #get message
        content = scrub_message(str(message['last_status']))

        #get sender indormation
        sender = get_sender(str(message['accounts']))
        sender_id = sender[0]
        sender_username = sender[1]
        sender_displayname = sender[2]

        # store message and sender's profile information
        store_message_and_sender_info(cnx, content, sender_id, sender_username, sender_displayname)
        
        # follow the sender
        #follow_sender(mastodon, sender)

        
        #respond to sender
        #respond_to_message(mastodon, message)

        #remove direct message from inbox
        #remove_message_from_inbox(msgId)
        
    print ("Disconnected\n")
    return 0
        
if __name__ == '__main__':
    try:
        exit_code = main()
    except Exception:
        traceback.print_exc()
        exit_code = 1
    sys.exit(exit_code)

