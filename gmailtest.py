import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64

# Gmail API scope for sending email
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def send_email(subject, message_text, to_email):
    """Sends an email using the Gmail API."""
    creds = None

    # Load credentials or prompt user to log in
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save credentials for next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # Build Gmail API service
    service = build('gmail', 'v1', credentials=creds)

    # Create the email
    message = MIMEText(message_text, 'html')
    message['to'] = to_email
    message['from'] = "your-email@gmail.com"  # Replace with your Gmail
    message['subject'] = subject

    # Encode and send
    raw_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
    sent_message = service.users().messages().send(userId="me", body=raw_message).execute()

    print(f"✅ Email sent! Message ID: {sent_message['id']}")

# Test sending an email
send_email(
    subject="🌊 Flood Alert Test Email",
    message_text="<h3>This is a test flood alert from your FYP system.</h3><p>Stay safe!</p>",
    to_email="recipient@example.com"  # Replace with your email for testing
)
