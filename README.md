# ✍️ DevJourney - Personal Blog

A modern, lightweight, and extensible personal blog web application built with **Python**, **Flask**, and **Filesystem Storage (JSON)**.

---

## 🌟 Features

- **Filesystem Storage**: Articles are stored directly on disk as clean, human-readable JSON files in `articles/` without requiring any heavy external database.
- **Server-Side Rendering (SSR)**: Instant page loads with Jinja2 templating and zero client-side JavaScript bundle overhead.
- **Admin Dashboard & Editor**: Protected administrative panel to compose, publish, edit, and delete blog posts.
- **Session Authentication**: Secure session-based admin authentication with custom decorator (`@admin_required`).
- **Rich Content & Markdown Support**: Headings (`#`, `##`, `###`), bold text (`**`), inline code (`` ` ``), bullet/numbered lists, and syntax-highlighted code blocks.
- **Search & Tag Filtering**: Real-time article search across titles, summaries, and content, plus tag-based filtering.
- **Modern Responsive Design**: Dark-mode-first aesthetic with glassmorphism touches, fluid typography, and mobile-friendly layout.
- **Automated Test Suite**: 13 unit tests verifying storage CRUD operations, session auth, and all web routes.

---

## 📁 Project Structure

```
Personal Blog/
├── app.py                  # Main Flask application and URL routing
├── storage.py              # Filesystem storage manager (CRUD operations)
├── auth.py                 # Authentication helpers & @admin_required decorator
├── test_blog.py            # Automated unit tests
├── requirements.txt        # Python dependencies
├── articles/               # JSON storage directory for blog posts
│   ├── welcome-to-my-personal-blog.json
│   ├── getting-started-with-python-web-development.json
│   └── mastering-clean-code-and-filesystem-storage.json
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Layout with navbar, alerts, and footer
│   ├── index.html          # Homepage with article feed, search & tag filter
│   ├── article.html        # Single article reader view
│   ├── login.html          # Admin login page
│   ├── 404.html            # Custom 404 Not Found page
│   ├── 500.html            # Custom 500 Internal Error page
│   └── admin/
│       ├── dashboard.html  # Admin panel listing all articles
│       └── editor.html     # Compose & edit form
└── static/
    └── css/
        └── style.css       # Clean, modern CSS design system
```

---

## 🚀 Getting Started

### 1. Requirements
- Python 3.8+
- Flask (`pip install Flask` or `pip install -r requirements.txt`)

### 2. Run the Application
Navigate to the `Personal Blog` folder and run:
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔐 Admin Authentication

To access the admin area and create or edit articles:
1. Click **Admin Login** in the navigation bar (or visit `/login`).
2. Log in with the default credentials:
   - **Username**: `admin`
   - **Password**: `admin123`

*(You can customize these by setting the `ADMIN_USERNAME` and `ADMIN_PASSWORD` environment variables).*

---

## 🧪 Running Automated Tests

Run the test suite from the `Personal Blog` directory:
```bash
python -m unittest test_blog.py
```

---

## 📝 Article Data Schema

Each post in `articles/<slug>.json` uses the following structure:

```json
{
  "title": "My Post Title",
  "slug": "my-post-title",
  "date": "2026-08-13",
  "summary": "Short excerpt for feed cards",
  "content": "Full post body with **markdown** formatting...",
  "tags": ["Python", "WebDev"],
  "reading_time": 2,
  "updated_at": "2026-08-13T20:00:00"
}
```
