
import mastodon
import configparser
import mysql.connector
from mysql.connector import Error
from mysql.connector import errorcode
import time

def connect_to_mastodon():
    # Read the configuration file
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    # Connect to the Mastodon API using the credentials in the configuration file
    mastodon = Mastodon(
        client_id=config['MASTODON']['CLIENT_ID'],
        client_secret=config['MASTODON']['CLIENT_SECRET'],
        access_token=config['MASTODON']['ACCESS_TOKEN'],
        api_base_url=config['MASTODON']['API_BASE_URL']
    )
    
    return mastodon

def connect_to_database():
    # Read the configuration file
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    # Connect to the MySQL database using the credentials in the configuration file
    cnx = mysql.connector.connect(
        host=config['MYSQL']['HOST'],
        user=config['MYSQL']['USER'],
        password=config['MYSQL']['PASSWORD'],
        database=config['MYSQL']['DATABASE']
    )
    
    return cnx

def get_last_check_time(cnx):
    # Get the timestamp of the last time the program ran from the database
    cursor = cnx.cursor()
    query = "SELECT value FROM settings WHERE name = 'last_check_time'"
    cursor.execute(query)
    result = cursor.fetchone()
    last_check_time = result[0] if result else None
    cursor.close()
    
    return last_check_time

def set_last_check_time(cnx, last_check_time):
    # Update the timestamp of the last time the program ran in the database
    cursor = cnx.cursor()
    query = "UPDATE settings SET value = %s WHERE name = 'last_check_time'"
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


def respond_to_message(mastodon, message):
    # Respond to the message with a thank you message
    response = "Thank you for your message!"
    mastodon.status_post(status=response, in_reply_to_id=message["id"], visibility="direct")

    
# main function
def main():
    # connect to Mastodon API
    mastodon = connect_to_mastodon()
    cnx = connect_to_database()
    # check for new direct messages
    messages = get_direct_messages(mastodon)
    
    # process each direct message
    for message in messages:
        # store message and sender's profile information
        store_message_and_sender_info(message)
        
        # follow the sender
        follow_sender(mastodon, message['account']['id'])
        
        # reply to the direct message
        respond_to_message(mastodon, message)

if __name__ == '__main__':
    main()
