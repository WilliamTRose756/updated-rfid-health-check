import os
import pymongo
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from pymongo.errors import ConnectionFailure

class ReaderCheck:
    """
    A class representing a MongoDB (DocumentDB) database collection containing device data.
    """

    def __init__(self, connection_string):
        try:
            self.client = pymongo.MongoClient(connection_string, tls=True, tlsCAFile='rds-combined-ca-bundle.pem')
            self.client.admin.command('ismaster')  # Check if the connection is established
            print("Connected to the document DB cluster successfully!")
        except ConnectionFailure as e:
            print(f"Connection to the document DB cluster failed: {e}")
            self.client = None

    def get_offline_devices(self):
        if not self.client:
            print("Failed to get offline devices due to connection failure.")

        try:
            profiles_collection = self.client.test.profiles # This line targets the actual collection, update accordingly
            offline_devices = list(profiles_collection.find({'status': 'inactive'}))
            if offline_devices:
                return offline_devices
            else:
                print('There are no offline devices for this collection')
        except Exception as e:
            print(f"Failed to get offline devices due to an error: {e}")
            return []

class SESEmail:
    """
    A class representing an email sender using the Amazon SES service.
    """
    def __init__(self, smtp_server, port, smtp_username, smtp_password, from_email):
        self.smtp_server = smtp_server
        self.port = port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email

    def send_email(self, recipient, subject, body):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_server, self.port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.from_email, recipient, msg.as_string())
        except Exception as e:
            print(f"Failed to send the email due to an error: {e}")
    
def generate_email_body(offline_devices):
    body = 'The following devices are currently offline:\n\n'
    for device in offline_devices:
        body += str(device) + '\n'
    return body

def lambda_handler(event, context):
    CONNECTION_STRING = os.environ['CONNECTION_STRING']
    SENDER_EMAIL = os.environ['SENDER_EMAIL']
    RECIPIENT_EMAIL = os.environ['RECIPIENT_EMAIL']
    SMTP_SERVER = 'email-smtp.us-east-1.amazonaws.com'
    PORT = 587
    SMTP_USERNAME = os.environ['SMTP_USERNAME']
    SMTP_PASSWORD = os.environ['SMTP_PASSWORD']

    # Check for offline devices
    device_handler = ReaderCheck(CONNECTION_STRING)
    offline_devices = device_handler.get_offline_devices()

    SUBJECT = 'Offline Devices Report'

    # Generate email body
    EMAIL_BODY = generate_email_body(offline_devices)

    # Send email with offline devices
    email_sender = SESEmail(SMTP_SERVER, PORT, SMTP_USERNAME, SMTP_PASSWORD, SENDER_EMAIL)
    email_sender.send_email(RECIPIENT_EMAIL, SUBJECT, EMAIL_BODY)
