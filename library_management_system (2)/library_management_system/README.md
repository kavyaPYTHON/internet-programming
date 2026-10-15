# Library Management System

A local college-library web app built with Flask, SQLite, HTML, CSS and Bootstrap.

## Features
- Student registration/login, profile updates and borrowing history
- Public catalog search and book detail pages
- Admin dashboard, book CRUD, issue/return workflow and overdue fines
- Study material upload, year/semester listing and protected downloads
- Contact form
- Password hashing and role-protected admin routes

## Run in VS Code
1. Install Python 3.10+ and VS Code's Python extension.
2. Open this folder in VS Code.
3. Create and activate a virtual environment:
   - Windows PowerShell: `py -m venv .venv` then `.venv\Scripts\Activate.ps1`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install packages: `python -m pip install -r requirements.txt`
5. Run: `python app.py`
6. Open `http://127.0.0.1:5000`

## Demo admin
- Email: `admin@library.local`
- Password: `Admin@123`

Change the demo password and `SECRET_KEY` before deploying anywhere beyond your own computer. The demo admin account is created automatically when the database is first initialized. Delete `library.db` only if you want to reset all local data.

## Fine rule
The app calculates ₹5 per overdue day when a librarian records a return. Active loans show their due dates; this starter version records the final fine on return.

## Project structure
```text
library_management_system/
├── app.py
├── requirements.txt
├── README.md
├── library.db              # created automatically when app starts
├── uploads/                # created automatically; uploaded materials live here
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── register.html
    ├── book_detail.html
    ├── student.html
    ├── profile.html
    ├── admin.html
    ├── manage_books.html
    ├── book_form.html
    ├── issue_book.html
    ├── manage_materials.html
    ├── students.html
    ├── contact.html
    └── error.html
```

## Important
This is a student-project starter. Before public deployment, add CSRF protection, email verification/password reset, audit logging, database backups, stronger configuration, and malware scanning for uploads. Use a production WSGI server and disable debug mode.
