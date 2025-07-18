import streamlit as st
import json
import os
import smtplib
from email.mime.text import MIMEText

# ------------------------------
# CONFIG
# ------------------------------
GMAIL_USER = "farahsyafawati@gmail.com"  # Your Gmail address
GMAIL_APP_PASSWORD = "dois olth dqbw wiks"  # 16-character app password
SUBSCRIBERS_FILE = "subscribers.json"


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
# SUBSCRIBER MANAGEMENT
# ------------------------------
def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "r") as f:
            return json.load(f)
    return []


def save_subscribers(emails):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(emails, f)


def add_subscriber(email):
    subscribers = load_subscribers()
    if email not in subscribers:
        subscribers.append(email)
        save_subscribers(subscribers)
        return True
    return False


def remove_subscriber(email):
    subscribers = load_subscribers()
    if email in subscribers:
        subscribers.remove(email)
        save_subscribers(subscribers)
        return True
    return False


# ------------------------------
# STREAMLIT UI
# ------------------------------
st.title("🌊 Flood Alert Subscription System")

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

# Show current subscribers (testing only — remove for production)
if st.checkbox("Show current subscribers"):
    st.write(load_subscribers())


# ------------------------------
# FLOOD ALERT TEST BUTTON
# ------------------------------
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
