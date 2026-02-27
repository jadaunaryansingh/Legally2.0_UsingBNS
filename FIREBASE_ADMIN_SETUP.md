# Firebase Admin SDK Setup Guide

To enable the admin dashboard with real Firebase data, you need to set up Firebase Admin SDK credentials.

## Step 1: Download Service Account Key

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: **legally-ee5f9**
3. Click the **⚙️ gear icon** (Settings) → **Project settings**
4. Navigate to the **Service accounts** tab
5. Click **Generate new private key**
6. Click **Generate key** in the confirmation dialog
7. A JSON file will be downloaded (e.g., `legally-ee5f9-firebase-adminsdk-xxxxx.json`)

## Step 2: Place the Credentials File

**Option A: Local Development (Recommended)**
1. Rename the downloaded file to `firebase-credentials.json`
2. Move it to: `/home/aryanjadaun/Projects@Me/Legally2.0/admin-backend/firebase-credentials.json`

**Option B: Environment Variables (Production)**
If you prefer not to use a file, extract values from the JSON and add them to `.env`:
```env
FIREBASE_TYPE=service_account
FIREBASE_PROJECT_ID=legally-ee5f9
FIREBASE_PRIVATE_KEY_ID=your_private_key_id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@legally-ee5f9.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your_client_id
FIREBASE_CLIENT_X509_CERT_URL=your_cert_url
```

## Step 3: Restart the Backend

The admin backend will automatically detect the credentials and initialize Firebase Admin SDK.

## Security Notes

⚠️ **IMPORTANT**: 
- Never commit `firebase-credentials.json` to Git (already in .gitignore)
- Never share your service account key publicly
- Use environment variables for production deployments

## Verification

Once configured, the backend will show:
```
✓ Firebase Admin SDK initialized successfully from file
```

And your admin dashboard will display real user and chat data from Firebase Realtime Database.

## Current Firebase Project Details
- **Project ID**: legally-ee5f9
- **Database URL**: https://legally-ee5f9-default-rtdb.firebaseio.com
