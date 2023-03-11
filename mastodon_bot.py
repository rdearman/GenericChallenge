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

def store_message_and_sender_info(cnx, content, sender):
    # Store the message and sender information in the database
    now = datetime.now()
    tmstamp = now.strftime("%Y/%m/%d %H:%M:%S")
    cursor = cnx.cursor()
    query = "INSERT INTO messages (sender_id, sender_username, text, timestamp) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (sender[0], sender[1], content, tmstamp ))
    cnx.commit()
    cursor.close()

def scrub_message(string):
    # parse the message and remove extra rubbish
    clean = re.compile('<.*?>')
    tmp = re.findall('\'content\': \'(.*)\', \'filtered\'', string)
    tmp = ''.join(str(x) for x in tmp)
    return re.sub(clean, '', tmp)


def get_sender(string,msgId):
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
    sender_info.append(msgId)
    atname = re.findall('\'acct\': \'(.*)\', \'display_name\'', string)
    atname = ''.join(str(x) for x in atname)
    sender_info.append(atname)
    return sender_info

# --------------------------------------------------

def Registration(mastodon, content, cnx, sender):
    PUsername = sender[0]
    RegistrationLanguages = []
    for token in content.split():
        if token == "#register" or re.search(".*#.*", token) == None :
            continue
        else:
            RegistrationLanguages.append(token.replace('#',''))

    cursor = cnx.cursor()
    query = ("SELECT UserName FROM Participants WHERE UserName='{:s}'".format(PUsername))
    cursor.execute(query)
    results = cursor.fetchone()
    if results[0].lower() == PUsername :
        PUsername = results[0]
        update_query = ("UPDATE Participants SET AccountType='mastodon' WHERE UserName='{:s}'".format(PUsername))
        cursor.execute(update_query)
    else:
        print ("ERROR")

        
    query = ("SELECT LanguageCode FROM Entries WHERE UserName='{:s}'".format(PUsername))
    cursor.execute(query)
    results = cursor.fetchall()
    newLang = []
    for val in RegistrationLanguages :
        for res in results :
            if str(val) != str(res[0]) :
                newLang.append(val)

    if len(newLang) > 0 :
        for lang in newLang :
            if len(lang) == 2: 
                query = ("INSERT INTO Entries (UserName, LanguageCode) VALUES ('{:s}','{:s}')".format(PUsername,lang))
                cursor.execute(query)

    cnx.commit()
    cursor.close()
    content = "Sucessfully updated " + content
    UpdateStatus(mastodon, sender, content)

   
# --------------------------------------------------

def Update (mastodon, content, cnx, sender ):
    actionCodes = ['inc_minuteswatched','inc_pagesread','edt_minuteswatched','del_minuteswatched','undo', 'edt_pagesread', 'del_pagesread']
    cursor = cnx.cursor()
    tmp = re.findall('"(.*)"', content)
    title = tmp[0]
    tmpnum = re.findall(".*#.*\s+(\d+)\s+.*", content)
    number = int(tmpnum[0])

    tmp = re.findall('.*#(\w{1,3})( |$)',content)
    language = list(tmp[0])[0]
    now = datetime.now()
    tmstamp = now.strftime("%Y/%m/%d %H:%M:%S")
    
    query = ("SELECT UserName FROM Participants WHERE AccountType='mastodon' AND UserName='{:s}'".format(sender[1]))
    cursor.execute(query)
    results = cursor.fetchone()
    if results != None :
        PUsername = results[0]
    else:
        print("Unregistered User: {:s} ".format(sender[1]))
        msg = content.replace('@langchallenge', '')
        UpdateStatus(mastodon, sender, "Account is not registered when processing message " + msg + " please send a registration message.")
        return 

    query = ("SELECT Id FROM Entries WHERE UserName='{:s}' and LanguageCode='{:s}'".format(PUsername,language))
    cursor.execute(query)
    results = cursor.fetchone()
    if results != None :
        entryId = results[0]
        
    for token in content.split():
        if token == "#read" or token == "#reading" :
            query = ("INSERT INTO Actions (EntryId, ActionCode, Time, AmountData, TextData) VALUES ('{:d}', '{:s}' , '{:s}', '{:d}', '{:s}')".format(entryId, actionCodes[1], tmstamp, number, title)  )
            cursor.execute(query)
            query = ("UPDATE Entries SET PagesRead=(SELECT sum(AmountData) FROM Actions WHERE ActionCode='{:s}' AND EntryId='{:d}') where Id='{:d}'".format(actionCodes[1],entryId,entryId ) )
            cursor.execute(query)
        elif token == "#watch" or token == "#watched" or token == "#watching":
            query = ("INSERT INTO Actions (EntryId, ActionCode, Time, AmountData, TextData) VALUES ('{:d}', '{:s}' , '{:s}', '{:d}', '{:s}')".format(entryId, actionCodes[0], tmstamp, number, title))
            cursor.execute(query)
            query = ("UPDATE Entries SET MinutesWatched=(SELECT sum(AmountData) FROM Actions WHERE ActionCode='{:s}' AND EntryId='{:d}') where Id='{:d}'".format(actionCodes[0],entryId,entryId ) )
            cursor.execute(query)
        else:
            continue

    cnx.commit()
    cursor.close()
    content = "Sucessfully updated " + content
    UpdateStatus(mastodon, sender, content)
        
# --------------------------------------------------

def UpdateStatus(mastodon, sender, content):
    content = content.replace('@langchallenge','')
    content = "@" + sender[4] + " " + content
    mastodon.status_post(content, visibility='Direct')

# --------------------------------------------------
        
# main function
def main():
    mastodon = connect_to_mastodon()
    cnx = connect_to_database()
    messages = mastodon.conversations()
    
    for message in messages:
        #get message id
        msgId = message['id']
        #get message
        content = scrub_message(str(message['last_status']))
        # check it is to the bot.
        if not re.search(".*@langchallenge*", content):
            continue
        
        #get sender indormation
        sender = get_sender(str(message['accounts']),msgId)

        #determine if message is a registration or an update
        if re.search(".*#register.*", content):
            Registration(mastodon, content, cnx, sender)
        elif  re.search(".*#[a-zA-Z]+.*\d+", content):
            Update (mastodon, content, cnx, sender )
        else:
            #it isn't related to our bot so remove it and move on.
            print ("Continuing")
            continue
            
        # store message and sender's profile information
#        store_message_and_sender_info(cnx, content, sender)
        
        # follow the sender
        mastodon.account_follow(sender[0])

        #remove direct message from inbox
        #mastodon.status_delete(sender[3])        

        
    print ("Disconnected\n")
    return 0
        
if __name__ == '__main__':
    try:
        exit_code = main()
    except Exception:
        traceback.print_exc()
        exit_code = 1
    sys.exit(exit_code)

