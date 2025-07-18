import streamlit as st
import json
import smtplib
from email.mime.text import MIMEText
import firebase_admin
from firebase_admin import credentials, firestore

# ------------------------------
# CONFIG
# ------------------------------
GMAIL_USER = st.secrets["GMAIL_USER"]
GMAIL_APP_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]


# Initialize Firestore
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["FIREBASE_CREDENTIALS"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()

SUBSCRIBERS_COLLECTION = "subscribers"


# ------------------------------
# EMAIL FUNCTION
# ------------------------------
def send_email_smtp(subject, message_html, to_email):
    """Send email using Gmail SMTP."""
    msg = MIMEText(message_html, 'html')
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = to_email

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, [to_email], msg.as_string())
        server.quit()
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")


# ------------------------------
# SUBSCRIBER MANAGEMENT (Firestore)
# ------------------------------
def add_subscriber(email):
    doc_ref = db.collection(SUBSCRIBERS_COLLECTION).document(email)
    if doc_ref.get().exists:
        return False
    doc_ref.set({"email": email})
    return True


def remove_subscriber(email):
    doc_ref = db.collection(SUBSCRIBERS_COLLECTION).document(email)
    if doc_ref.get().exists:
        doc_ref.delete()
        return True
    return False


def load_subscribers():
    docs = db.collection(SUBSCRIBERS_COLLECTION).stream()
    return [doc.id for doc in docs]


# ------------------------------
# STREAMLIT UI
# ------------------------------
st.title("🌊 Flood Alert Subscription System (Firestore)")

email = st.text_input("Enter your email to subscribe/unsubscribe:")

if st.button("Subscribe"):
    if email:
        if add_subscriber(email):
            st.success(f"✅ {email} subscribed successfully!")
        else:
            st.info("ℹ️ You are already subscribed.")
    else:
        st.error("⚠️ Please enter a valid email.")

if st.button("Unsubscribe"):
    if email:
        if remove_subscriber(email):
            st.success(f"❌ {email} unsubscribed successfully.")
        else:
            st.info("ℹ️ This email is not in the subscriber list.")
    else:
        st.error("⚠️ Please enter your email.")

if st.checkbox("Show current subscribers"):
    subscribers = load_subscribers()
    st.write(subscribers)

if st.button("Send Test Flood Alert to All Subscribers"):
    subscribers = load_subscribers()
    if not subscribers:
        st.warning("⚠️ No subscribers found.")
    else:
        for sub_email in subscribers:
            send_email_smtp(
                subject="🌊 Flood Alert!",
                message_html="<h3>Flood predicted in your area. Stay safe!</h3>",
                to_email=sub_email
            )
        st.success("✅ Flood alert sent to all subscribers!")
