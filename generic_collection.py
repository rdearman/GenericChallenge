import imaplib
import email
import re
import mysql.connector

def check_registration_emails(email_address, password):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_address, password)
    mail.select("inbox")
    result, data = mail.search(None, "ALL")
    mail_ids = data[0]
    id_list = mail_ids.split()
    for i in reversed(id_list):
        result, data = mail.fetch(i, "(RFC822)")
        for response in data:
            if isinstance(response, tuple):
                msg = email.message_from_bytes(response[1])
                subject = msg["subject"]
                if subject == "Participant Registration":
                    email_body = msg.get_payload()
                    name, language = parse_registration_email(email_body)
                    insert_participant(name, language)
                    return
    return None

def parse_registration_email(email_body):
    lines = email_body.split("\n")
    name = None
    language = None
    for line in lines:
        if line.startswith("Name:"):
            name = line[6:].strip()
        if line.startswith("Primary Language:"):
            language = line[17:].strip()
    return name, language

def insert_participant(name, language):
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="password",
        database="activity_challenge"
    )
    cursor = connection.cursor()
    sql = "INSERT INTO Participants (name, primary_language) VALUES (%s, %s)"
    values = (name, language)
    cursor.execute(sql, values)
    connection.commit()
    connection.close()
