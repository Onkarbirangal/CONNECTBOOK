# ConnectBook Backup & Disaster Recovery Guide

**Platform:** ConnectBook Social Network  
**Environment:** Windows 11 / Django 5.2 / SQLite  
**Database:** `db.sqlite3`  

---

## 1. Overview

ConnectBook uses a single-file SQLite database (`db.sqlite3`) and Django media storage (`media/`). This architecture simplifies backups, replication, and disaster recovery.

---

## 2. Automated & Manual Backup Protocols

### A. Pre-Upgrade Database Snapshot
Before running migrations or making system modifications, create a timestamped backup copy:

```powershell
# PowerShell backup command
Copy-Item -Path "db.sqlite3" -Destination "db.sqlite3.v3_$(Get-Date -Format 'yyyyMMdd_HHmmss').bak"
```

### B. Media Assets Backup
Archive all uploaded media (avatars, covers, post media, marketplace images):

```powershell
Compress-Archive -Path "media" -DestinationPath "backups\media_$(Get-Date -Format 'yyyyMMdd').zip" -Force
```

---

## 3. Restoration Procedure

If database corruption or accidental deletion occurs:

1. **Stop the Running Server:**
   Terminate any running `manage.py runserver` or Daphne worker processes.

2. **Restore Database File:**
   ```powershell
   Copy-Item -Path "db.sqlite3.v3_20261124.bak" -Destination "db.sqlite3" -Force
   ```

3. **Verify Database Integrity:**
   ```powershell
   python -c "import sqlite3; con = sqlite3.connect('db.sqlite3'); print(con.execute('PRAGMA integrity_check;').fetchone()[0])"
   ```
   *Expected Output:* `ok`

4. **Run System Checks & Migrations:**
   ```powershell
   python manage.py check
   python manage.py migrate
   ```

5. **Restart Server:**
   ```powershell
   python manage.py runserver 127.0.0.1:8002
   ```
