# EICAR Test File

## What is EICAR?

The EICAR test file is a standard test file used to verify that antivirus software is working correctly. It contains a harmless string that all antivirus engines are programmed to detect as a virus.

## File Contents

The `eicar.txt` file contains the standard EICAR test string:
```
X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*
```

## How to Use

1. **Testing Virus Detection**: Upload the `eicar.txt` file through the file upload interface
2. **Expected Behavior**: The system should detect this as a virus and show the warning message
3. **Verification**: Check that the file is quarantined in the database with `virus_scan_status = "infected"`

## Safety

- This file is completely harmless
- It cannot execute or cause any damage
- It's designed specifically for testing antivirus functionality
- All major antivirus engines recognize this as a test file

## Testing the Frontend

When you upload this file:
1. The backend should detect it as infected
2. The frontend should display the virus warning message
3. The file should be quarantined and not accessible for download

## Note

This file is included for testing purposes only. In a production environment, you might want to remove this file or add it to `.gitignore`.
