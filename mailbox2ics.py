#!/usr/bin/python
#!/usr/bin/env python
# mailbox2ics.py

# Import system modules
import configparser
import imaplib
import email
import getpass
import sys
import re
import traceback
from datetime import datetime
import email, smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import mysql.connector
from mysql.connector import errorcode

# --- TODO --- #
# [] update the streak data 
# ---------------------------------------------------------------
# [X] delete emails after processing, or move into a subdirectory
# [X] get email address of the sender ? Probably in the msg
# [X] change all the print statements to use the {:s} .format() system
# [X] respond to email with "SC Bot processed your email, #keyword...
# [X] move password, username, smtp server, etc into the DB or config file. 
# [X] Add in a DB configuration into the config file
# [X] read from DB
# [X] deal with reading keywords.
# [X] update the DB actions for the users registration email.
# [X] update the DB actions for the users update email.
# [X] modify Live DB: ALTER TABLE Participants ADD COLUMN Email VARCHAR(255) ;


# Method to read config file settings
def read_config():
    config = configparser.ConfigParser()
    config.read('configurations.ini')
    return config

config = read_config()

# Data Setup & config data
email_ptrn = re.compile("<([^>]+)>")
emailDate = ""
emailSubject = ""
emailSender = ""
now = datetime.now()
today = now.strftime("%m/%d/%Y %H:%M:%S")
TLS_port = config['SMTP']['TLS_port']
port = config['SMTP']['SMTP_port']
smtp_hostname = config['SMTP']['smtp_server']
sender_email = config['SMTP']['sender_email']
smtp_user = config['SMTP']['username']
smtp_password = config['SMTP']['password']
smtp_mailbox =  config['SMTP']['mailbox']
to_folder = config['SMTP']['processed']
db_name = config['MYSQL']['DB_NAME']
db_user = config['MYSQL']['DB_USER']
db_host = config['MYSQL']['DB_HOST']
db_password = config['MYSQL']['DB_PASSWORD']

def db_connect ():
    try:
        cnx = mysql.connector.connect(user=db_user, password=db_password,host=db_host,database=db_name)
        return cnx
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)

# --------------------------------------------------

def SendEmail (emailSubject, emailSender):
    receiver_email = emailSender
    messagep1 = """\
From: Super Challenge Bot <superchallenge2023_test@anki-tv.co.uk>
Date:  """
    messagep2 =  today + "\n"
    messagep3 = """\
Subject: Hi there

Your message has been received and processed.\n\n"""

    message = messagep1 + messagep2 + messagep3 + emailSubject + "\n\nthe Super Challenge Bot\n"
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    with smtplib.SMTP(smtp_hostname, port) as server:
        server.ehlo()  # Can be omitted
        server.starttls(context=context)
        server.ehlo()  # Can be omitted
        server.login(smtp_user, smtp_password)
        server.sendmail(sender_email, receiver_email, message)

# --------------------------------------------------

def Registration (emailSubject, baseSenderEmail, emailSender, cnx):
    ParticpantUsername = re.findall("^#register\s+(\w+)\s+#.*", emailSubject)
    PUsername = ParticpantUsername[0]
    RegistrationLanguages = []
    for token in emailSubject.split():
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
        update_query = ("UPDATE Participants SET EMail='{:s}' WHERE UserName='{:s}'".format(baseSenderEmail,PUsername))
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
            query = ("INSERT INTO Entries (UserName, LanguageCode) VALUES ('{:s}','{:s}')".format(PUsername,lang))
            cursor.execute(query)

    cnx.commit()
    cursor.close()
    SendEmail(emailSubject,emailSender)

# --------------------------------------------------

def Update (emailSubject, baseSenderEmail, emailSender, cnx ):
    #print (to_folder, smtp_mailbox)
    actionCodes = ['inc_minuteswatched','inc_pagesread','edt_minuteswatched','del_minuteswatched','undo', 'edt_pagesread', 'del_pagesread']
    cursor = cnx.cursor()
    tmp = re.findall('.*\s+"([\w\s]+)"\s+.*', emailSubject)
    title = tmp[0]
    tmp = re.findall(".*#.*\s+(\d+)\s+.*", emailSubject)
    number = int(tmp[0])
    tmp = re.findall('.*#(\w{1,3})\s+.*',emailSubject)
    language = tmp[0]
    now = datetime.now()
    tmstamp = now.strftime("%Y/%m/%d %H:%M:%S")

    query = ("SELECT UserName FROM Participants WHERE Email='{:s}'".format(baseSenderEmail))
    cursor.execute(query)
    results = cursor.fetchone()
    if results != None :
        PUsername = results[0]
    else:
        print("Unregistered User: {:s}".format(baseSenderEmail))
        return

    query = ("SELECT Id FROM Entries WHERE UserName='{:s}' and LanguageCode='{:s}'".format(PUsername,language))
    cursor.execute(query)
    results = cursor.fetchone()
    if results != None :
        entryId = results[0]

    for token in emailSubject.split():
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
    exit(0)
    SendEmail(emailSubject,emailSender)

# --------------------------------------------------

def main():
    cnx = db_connect()
    mail_server = imaplib.IMAP4_SSL(smtp_hostname)
    (typ, [login_response]) = mail_server.login(smtp_user, smtp_password)
    try:
        (typ, [num_messages]) = mail_server.select(smtp_mailbox, readonly=False)
        if typ == 'NO':
            raise RuntimeError('Could not find mailbox %s: %s' %
                               (smtp_mailbox, num_messages))
        num_messages = int(num_messages)
        if not num_messages:
            print ("No Messages\n")
            exit(0)
        (typ, [message_ids]) = mail_server.search(None, 'ALL')
        for num in message_ids.split():          # Get a Message object
            typ, message_parts = mail_server.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(message_parts[0][1])
            emailDate =  msg["Date"]
            emailSubject = msg["Subject"].lower()
            emailSender =  msg["From"]
            x = re.findall(email_ptrn, emailSender)
            baseSenderEmail = x[0]
            if re.search(".*#register.*", emailSubject):
                if re.search("^#register\s+\w+\s+#.*", emailSubject):
                    Registration(emailSubject, baseSenderEmail, emailSender, cnx)
                else:
                    print ("Malformed Subject")
            elif  re.search(".*#[a-zA-Z]+.*\d+", emailSubject):
                Update (emailSubject,baseSenderEmail, emailSender, cnx )

            result = mail_server.copy(num, to_folder)
            if result[0] == 'OK':
                mov, data = mail_server.store( num, '+FLAGS', r'(\Deleted)')

    finally:
        # Disconnect from the IMAP server
        if mail_server.state != 'AUTH':
            mail_server.close()
        mail_server.logout()

    #print ("Disconnected\n")
    return 0

if __name__ == '__main__':
    try:
        exit_code = main()
    except Exception:
        traceback.print_exc()
        exit_code = 1
    sys.exit(exit_code)

