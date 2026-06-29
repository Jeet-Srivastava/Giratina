# AePS (Aadhaar Enabled Payment System) — Troubleshooting Guide

## What is AePS?
AePS allows customers to perform basic banking transactions using their Aadhaar number and biometric authentication (fingerprint). As an Eko retailer, you act as a banking point where customers can withdraw cash, check balance, and more — all authenticated via Aadhaar.

## Common AePS Transaction Errors

### Error: "Biometric Authentication Failed"
**Cause**: The customer's fingerprint did not match with UIDAI records.
**Solution**:
1. Ask the customer to clean and dry their finger
2. Try a different finger (index finger usually works best)
3. Ensure the biometric device lens is clean and dry
4. If repeated failures, the customer may need to update their biometrics at the nearest Aadhaar center
5. Check if the biometric device firmware is up to date

### Error: "Transaction Declined by Bank"
**Cause**: The customer's bank has declined the transaction.
**Solution**:
1. Verify the customer has sufficient balance
2. Check if the customer's Aadhaar is linked to their bank account
3. The customer's bank may have a daily AePS withdrawal limit (typically ₹10,000)
4. Try again after some time — the bank server may be temporarily down
5. If persistent, advise the customer to contact their bank

### Error: "Customer Not Found" / "Invalid Aadhaar"
**Cause**: The Aadhaar number is not linked to any bank account.
**Solution**:
1. Verify the Aadhaar number entered is correct (12 digits)
2. The customer needs to link their Aadhaar to their bank account via their bank branch or net banking
3. Direct customer to UIDAI website (uidai.gov.in) to verify Aadhaar status

### Error: "Transaction Timeout"
**Cause**: The transaction took too long to process, usually due to network issues.
**Solution**:
1. Check your internet connectivity
2. Do NOT retry immediately — wait at least 5 minutes
3. Check transaction status using the Transaction Inquiry feature in Eko Connect
4. If the customer's account was debited, the amount will be auto-reversed within 5 working days (per RBI guidelines)

### Error: "Service Temporarily Unavailable"
**Cause**: The bank's AePS server is down for maintenance.
**Solution**:
1. This is a bank-side issue, not an Eko issue
2. Try again after 30–60 minutes
3. Try with a different bank if the customer has multiple accounts
4. Check the Eko Connect app for any service status notifications

## AePS Transaction Failed But Money Deducted

This is the most common and urgent issue. If an AePS transaction fails but the customer's account shows a debit:

1. **Do NOT retry the transaction** — this may cause a double debit
2. **Note the transaction ID** from the Eko Connect app
3. **Check transaction status** using Transaction Inquiry in Eko Connect
4. **Wait for auto-reversal** — per RBI guidelines, failed AePS transactions are auto-reversed within T+5 working days
5. **If not reversed after 5 working days**, raise a complaint:
   - Email: cs@eko.co.in
   - Include: Your Eko retailer code, customer's Aadhaar (last 4 digits), transaction ID, amount, date
6. **Reassure the customer** that their money is safe and will be returned

## Biometric Device Setup

### Supported Devices
Eko supports most STQC-certified biometric devices including:
- Mantra MFS100
- Morpho MSO 1300 E3
- StarTek FM220U
- Precision PB510

### Setup Steps
1. Connect the biometric device to your phone/computer via USB OTG
2. Install the device driver/app if prompted
3. Open Eko Connect app
4. Go to Settings > Device Setup
5. Select your device model
6. Test the device with your own fingerprint
7. The device status should show "Connected" in the app

### Device Not Detected
1. Try a different USB cable or OTG adapter
2. Restart your phone/computer
3. Ensure the device driver is installed
4. Some devices need their own companion app installed
5. Check if your phone supports USB OTG

## Daily AePS Authentication
As per regulatory requirements, retailers must complete a daily authentication before processing AePS transactions:
1. Open Eko Connect
2. Go to AePS section
3. Complete your own biometric authentication
4. This must be done once every 24 hours before your first AePS transaction of the day
