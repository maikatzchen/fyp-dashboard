importScripts('https://www.gstatic.com/firebasejs/8.10.1/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/8.10.1/firebase-messaging.js');

firebase.initializeApp({
  apiKey: "AIzaSyDV_7UdNmGlyGA2gXShjzUoVDcNVUcD0Zo",
  authDomain: "pivotal-crawler-459812-m5.firebaseapp.com",
  projectId: "pivotal-crawler-459812-m5",
  storageBucket: "pivotal-crawler-459812-m5.appspot.com",
  messagingSenderId: "85676216639",
  appId: "1:85676216639:web:574d48b8f858c867b1038a",
  measurementId: "G-YBDLNQ6C81"
});

const messaging = firebase.messaging();
