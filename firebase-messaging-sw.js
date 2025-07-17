import { initializeApp } from 'firebase/app';
import { getMessaging } from 'firebase/messaging/sw';

const firebaseConfig = {
  apiKey: "AIzaSyDV_7UdNmGlyGA2gXShjzUoVDcNVUcD0Zo",
  authDomain: "pivotal-crawler-459812-m5.firebaseapp.com",
  projectId: "pivotal-crawler-459812-m5",
  storageBucket: "pivotal-crawler-459812-m5.appspot.com",
  messagingSenderId: "85676216639",
  appId: "1:85676216639:web:574d48b8f858c867b1038a",
  measurementId: "G-YBDLNQ6C81"
};

const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);

// Handle background messages
onBackgroundMessage(messaging, (payload) => {
  console.log('[firebase-messaging-sw.js] Received background message:', payload);

  const { title, body, icon } = payload.notification;

  self.registration.showNotification(title, {
    body: body,
    icon: icon || '/firebase-logo.png' // fallback icon if none provided
  });
});
