# Digital Document Verification and Approval System
## University No Dues Clearance Module

> **B.Tech Computer Science and Engineering Major Project**  
> **Architecture:** Clean Full-Stack Architecture  
> **Backend:** Python 3.10+, Django 5  
> **Database:** SQLite (default development) / MySQL (production-ready)  
> **PDF & QR Engine:** ReportLab 5.x & QRCode PIL  
> **Frontend:** HTML5, CSS3, Bootstrap 5, Bootstrap Icons, JavaScript, Chart.js  

---

## 1. Project Overview

The **University No Dues Clearance System** is a mission-critical module of the *Digital Document Verification and Approval System*. It transforms the traditional, manual, paper-based university clearance procedure into an automated, transparent, and verifiable digital workflow.

### Problems Solved:
1. **Paper Chase Elimination:** Students no longer need to physically visit 7+ campus departments (Library, Accounts, Labs, Hostel, Sports, T&P, Examination) collecting physical signatures and stamps on paper slips.
2. **Parallel Department Processing:** Rather than sequential queue delays, clearance applications are dispatched to all statutory departments simultaneously.
3. **Transparent Financial Dues:** Itemized fine amounts, missing book lists, or hostel room inventory flags are visible to students in real-time with resolution instructions.
4. **Tamper-Proof Digital Certificates:** Once 100% of departments grant approval, a tamper-evident PDF Certificate is generated using ReportLab, complete with a cryptographically verifiable QR code linking to the University's public verification portal.

---

## 2. Technology Stack & Prerequisites

- **Language:** Python 3.10+
- **Framework:** Django 5.x
- **Database:**
  - **SQLite:** Pre-configured default for zero-setup development and evaluation.
  - **MySQL:** Supported natively via `PyMySQL`.
- **PDF Generation:** ReportLab 5.x (Custom Two-Pass `NumberedCanvas`, University Crest, Security Border, Department Clearance Audit Grid)
- **Security & QR:** Python `qrcode` with PIL engine, SHA-256 UUID token generation.
- **Frontend:** Bootstrap 5.3, Bootstrap Icons 1.11, Chart.js (Analytics), CSS3 custom academic theme.

---

## 3. User Roles and Key Capabilities

### A. Student Portal
1. **Authentication:** Secure registration & sign in with academic credentials.
2. **Profile Management:** View roll number, enrollment number, branch, semester, batch, and residency details.
3. **Application Submission:** Submit No Dues request with purpose (Degree, Migration, Semester, Internship) and supporting documents.
4. **Real-time Pipeline Tracker:** Visual progress stepper showing department-wise clearance statuses (`PENDING`, `APPROVED`, `ACTION_REQUIRED`, `ON_HOLD`, `REJECTED`).
5. **Dues & Remarks Breakdown:** Clear itemized fee breakdown (e.g. Library book fine ₹250, Accounts fee ₹500) and officer instructions.
6. **Certificate Download:** One-click download of the official digitally signed No Dues Certificate in PDF format upon completion.
7. **Notifications:** Real-time inbox for status updates and clearance actions.

### B. Department Staff Portal
1. **Isolated Department Queues:** Staff members only see applications and student records relevant to their assigned department.
2. **Student Bio Inspection:** Inspect student particulars (Hostel vs Day Scholar, Course, Roll No, Application remarks).
3. **Department-Specific Checklist:** Built-in guidance for Library (books/fines), Accounts (tuition/surplus), Hostel (room inventory/keys), Lab (equipment return), Sports, and T&P.
4. **Clearance Decision Matrix:**
   - **Approve:** Grant NIL dues clearance.
   - **Flag Dues / Action Required:** Specify exact outstanding rupee amount and itemized explanation.
   - **Place On Hold:** Hold verification pending physical inspection or return.
   - **Reject:** Reject with mandatory cause explanation.
5. **Audit Trail:** Log all actions with timestamps, officer identity, and historical remarks.

### C. University Administrator Portal
1. **Master Analytics Dashboard:** Executive KPI counters (Total Applications, Completed, In-Progress, Pending Dues, Rejected, Total Dues in ₹).
2. **Interactive Chart.js Visualizations:** Department Clearance Velocity and Application Health Donut.
3. **Department Bottleneck Matrix:** Track department-wise clearance rates and speed.
4. **Department & Staff Management:** Create departments, assign staff, and manage roles.
5. **Master Application Surveillance:** Search and filter across all university applications.
6. **Administrative Override:** Discretionary expedited approval authority with mandatory audit log.
7. **Certificate Registry:** Verifiable index of all issued certificates with revocation capabilities.
8. **Reports Export:** One-click CSV export of university-wide clearance records.

### D. Public Verification Portal
- Accessible at `/verify/` or `/verify/<uuid>/`
- Anyone (employers, verifying institutions, students) can scan the QR code on the certificate or search by Certificate ID to view the cryptographic verification badge and full department clearance audit table.

---

## 4. Quick Start Guide (Run in 2 Minutes)

### Step 1: Clone and Navigate
```bash
cd "c:\mojor project"
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run Database Migrations
```bash
python manage.py migrate
```

### Step 4: Seed Demo Data
Populate all 7 departments, staff accounts, and students in various realistic states:
```bash
python manage.py seed_data
```

### Step 5: Start Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 5. Viva Demo & Evaluation Credentials

The portal features a **1-Click Demo Switcher ribbon** at the top of every page and on the login page for effortless live presentation:

| Role | Username | Password | Purpose / Scenario in Demo |
|---|---|---|---|
| **University Admin** | `admin` | `admin123` | Executive dashboard, analytics, bottlenecks, CSV export, override |
| **Central Library Staff** | `staff_library` | `password123` | Library verification queue, overdue books audit |
| **Accounts Officer** | `staff_accounts` | `password123` | Finance & tuition clearance, dues management |
| **Hostel Warden** | `staff_hostel` | `password123` | Room vacation & mess bill audit |
| **CSE Lab Staff** | `staff_lab` | `password123` | Lab kit return & thesis submission audit |
| **Student (100% Cleared)** | `student_aarav` | `student123` | **Completed state** • Ready to download official PDF certificate & test QR verification |
| **Student (In Progress)** | `student_priya` | `student123` | **In-progress state** • 4 departments cleared, 2 pending review |
| **Student (Has Dues)** | `student_rohan` | `student123` | **Action Required** • Shows ₹750 dues (Library fine ₹250 + Fee ₹500) |
| **Student (Fresh)** | `student_ananya` | `student123` | **Fresh student** • Test live "Apply for No Dues" submission workflow |

---

## 6. How to Switch to MySQL Database

By default, the project runs on **SQLite** for zero-setup execution. To switch to **MySQL**:

1. Ensure MySQL Server is running (e.g. XAMPP, WampServer, or native MySQL).
2. Create the database:
   ```sql
   CREATE DATABASE nodues_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. Set the environment variable in your terminal before running Django:
   ```powershell
   # Windows PowerShell:
   $env:USE_MYSQL="True"
   $env:MYSQL_DB="nodues_db"
   $env:MYSQL_USER="root"
   $env:MYSQL_PASSWORD=""
   $env:MYSQL_HOST="127.0.0.1"
   $env:MYSQL_PORT="3306"
   ```
4. Run migrations on MySQL:
   ```bash
   python manage.py migrate
   python manage.py seed_data
   ```

---

## 7. Automated Test Suite

Run the comprehensive unit and integration test suite:
```bash
python manage.py test
```
The test suite validates:
- Application submission and automatic department clearance creation
- Department review, dues calculation, and approval workflow
- Automatic status recalculation and certificate PDF generation
- Public QR certificate verification
- Admin override authority
