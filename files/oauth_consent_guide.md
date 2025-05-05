# Google OAuth Consent Screen Configuration Guide

This guide will help you properly configure your Google OAuth consent screen to minimize issues with external users.

## Basic Configuration

### Step 1: Access the OAuth Consent Screen

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to **APIs & Services > OAuth consent screen**

### Step 2: Choose User Type

1. Select **External** (unless you have a Google Workspace organization)
2. Click **Create**

### Step 3: App Information

1. Enter your **App name** (e.g., "Knowledge Base System")
2. Select your **User support email** (use your email address)
3. Enter **Developer contact information** (your email address)
4. Click **Save and Continue**

### Step 4: Scopes

1. Click **Add or Remove Scopes**
2. Add the following scopes:
   - `https://www.googleapis.com/auth/drive.readonly` (for Google Drive access)
   - `https://www.googleapis.com/auth/userinfo.email` (for user email)
   - `https://www.googleapis.com/auth/userinfo.profile` (for user profile)
3. Click **Update**
4. Click **Save and Continue**

### Step 5: Test Users

1. Click **Add Users**
2. Enter the email addresses of your test users (up to 100)
3. Click **Save and Continue**

### Step 6: Summary

1. Review your settings
2. Click **Back to Dashboard**

## Publishing Status

Your app will initially be in **Testing** mode, which means:

- Only you (the project owner) and your test users can access it
- There's a limit of 100 test users
- Test users will see a warning that the app is unverified, but they can proceed

## Verification Process (For Production Apps)

If you want to make your app available to all users, you'll need to go through Google's verification process:

1. Complete your OAuth consent screen configuration
2. Add a privacy policy URL
3. Add a terms of service URL
4. Submit your app for verification

The verification process can take several weeks and may require additional documentation.

## Handling Unverified App Warnings

Even test users will see warnings about your app being unverified. Here's what they'll experience:

1. They'll see a screen saying "This app isn't verified"
2. They need to click on "Advanced" or "Continue"
3. Then click on "Go to [your app name] (unsafe)"

You may want to provide these instructions to your test users to help them navigate the warnings.

## References

- [Setting up your OAuth consent screen](https://support.google.com/cloud/answer/10311615)
- [Google API verification FAQ](https://support.google.com/cloud/answer/9110914)
- [OAuth 2.0 for Google APIs](https://developers.google.com/identity/protocols/oauth2)
