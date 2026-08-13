"""Personal Blog - Main Flask Application.

A lightweight, server-side rendered personal blog with filesystem storage,
Jinja2 templating, and session-based admin authentication.
"""

from __future__ import annotations

import html
import os
import re
from datetime import datetime
from typing import Any, Dict, List

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from markupsafe import Markup

from auth import (
    admin_required,
    is_authenticated,
    login_admin,
    logout_admin,
    verify_credentials,
)
from storage import StorageManager, slugify

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-secret-key-personal-blog-98234710"
)

# Initialize storage manager
storage = StorageManager()


# ---------------------------------------------------------------------------
# Custom Jinja Template Filters
# ---------------------------------------------------------------------------


@app.template_filter("format_date")
def format_date_filter(date_str: str) -> str:
    """Format an ISO date string (YYYY-MM-DD) to a human-readable date."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%B %d, %Y")
    except ValueError:
        return date_str


@app.template_filter("render_content")
def render_content_filter(raw_text: str) -> Markup:
    """Render article content with paragraphs, headings, bold, bullet points, and code."""
    if not raw_text:
        return Markup("")

    # Escape HTML first to prevent XSS vulnerabilities
    escaped = html.escape(raw_text)

    # Process blocks
    blocks = re.split(r"\n\s*\n", escaped)
    rendered_blocks: List[str] = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Code block (starts and ends with ```)
        if block.startswith("```") and block.endswith("```"):
            lines = block.splitlines()
            code_lines = lines[1:-1] if len(lines) > 1 else []
            code_content = "\n".join(code_lines)
            rendered_blocks.append(f"<pre><code>{code_content}</code></pre>")
            continue

        # Headings (###, ##, #)
        if block.startswith("### "):
            rendered_blocks.append(f"<h3>{block[4:]}</h3>")
            continue
        elif block.startswith("## "):
            rendered_blocks.append(f"<h2>{block[3:]}</h2>")
            continue
        elif block.startswith("# "):
            rendered_blocks.append(f"<h1>{block[2:]}</h1>")
            continue

        # Bullet list (lines starting with - or * )
        lines = block.splitlines()
        if all(
            line.strip().startswith(("- ", "* ", "1. ", "2. ", "3. ", "4. ", "5. "))
            for line in lines
        ):
            is_ordered = lines[0].strip()[0].isdigit()
            tag = "ol" if is_ordered else "ul"
            list_items = []
            for line in lines:
                clean_line = re.sub(r"^(\*|-|\d+\.)\s+", "", line.strip())
                # Inline bold / code in list items
                clean_line = re.sub(
                    r"\*\*(.+?)\*\*", r"<strong>\1</strong>", clean_line
                )
                clean_line = re.sub(r"`(.+?)`", r"<code>\1</code>", clean_line)
                list_items.append(f"<li>{clean_line}</li>")
            rendered_blocks.append(f"<{tag}>\n" + "\n".join(list_items) + f"\n</{tag}>")
            continue

        # Regular paragraph with inline markdown: bold, code, quotes
        p_text = block
        p_text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p_text)
        p_text = re.sub(r"`(.+?)`", r"<code>\1</code>", p_text)
        p_text = p_text.replace("\n", "<br>")
        rendered_blocks.append(f"<p>{p_text}</p>")

    return Markup("\n".join(rendered_blocks))


@app.context_processor
def inject_global_context() -> Dict[str, Any]:
    """Inject global variables into all Jinja templates."""
    return {
        "current_year": datetime.now().year,
        "is_admin": is_authenticated(),
        "admin_username": session.get("username", "Admin"),
    }


# ---------------------------------------------------------------------------
# Public Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index() -> str:
    """Home page displaying articles with optional tag and search filtering."""
    tag = request.args.get("tag", "").strip()
    query = request.args.get("q", "").strip().lower()

    articles = storage.get_all_articles(tag=tag if tag else None)

    if query:
        articles = [
            a
            for a in articles
            if query in a.get("title", "").lower()
            or query in a.get("summary", "").lower()
            or query in a.get("content", "").lower()
        ]

    # Collect all available tags across all articles for sidebar/filter pill list
    all_articles = storage.get_all_articles()
    all_tags = sorted(list({t for a in all_articles for t in a.get("tags", []) if t}))

    return render_template(
        "index.html",
        articles=articles,
        active_tag=tag,
        search_query=query,
        all_tags=all_tags,
    )


@app.route("/article/<slug>")
def article_detail(slug: str) -> str:
    """Display a single article by slug."""
    article = storage.get_article(slug)
    if not article:
        abort(404)
    return render_template("article.html", article=article)


@app.route("/tag/<tag_name>")
def tag_view(tag_name: str) -> Any:
    """Filter articles by tag."""
    return redirect(url_for("index", tag=tag_name))


# ---------------------------------------------------------------------------
# Authentication Routes
# ---------------------------------------------------------------------------


@app.route("/login", methods=["GET", "POST"])
def login() -> Any:
    """Admin login page."""
    if is_authenticated():
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        next_url = request.args.get("next") or url_for("admin_dashboard")

        if verify_credentials(username, password):
            login_admin(username)
            flash("Welcome back, Administrator!", "success")
            return redirect(next_url)
        else:
            flash("Invalid username or password. Please try again.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout() -> Any:
    """Log out the current admin user."""
    logout_admin()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Admin Dashboard & Article Management Routes
# ---------------------------------------------------------------------------


@app.route("/admin")
@admin_required
def admin_dashboard() -> str:
    """Admin dashboard overview listing all articles with management actions."""
    articles = storage.get_all_articles()
    return render_template("admin/dashboard.html", articles=articles)


@app.route("/admin/new", methods=["GET", "POST"])
@admin_required
def admin_new_article() -> Any:
    """Create a new article."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip()
        date = request.form.get("date", "").strip()
        summary = request.form.get("summary", "").strip()
        content = request.form.get("content", "").strip()
        tags_raw = request.form.get("tags", "")

        if not title:
            flash("Article title is required.", "danger")
            return render_template(
                "admin/editor.html",
                article={
                    "title": title,
                    "slug": slug,
                    "date": date or datetime.now().strftime("%Y-%m-%d"),
                    "summary": summary,
                    "content": content,
                    "tags": [t.strip() for t in tags_raw.split(",") if t.strip()],
                },
                mode="create",
            )

        if not content:
            flash("Article content cannot be empty.", "danger")
            return render_template(
                "admin/editor.html",
                article={
                    "title": title,
                    "slug": slug,
                    "date": date or datetime.now().strftime("%Y-%m-%d"),
                    "summary": summary,
                    "content": content,
                    "tags": [t.strip() for t in tags_raw.split(",") if t.strip()],
                },
                mode="create",
            )

        # Check if slug already exists
        target_slug = slugify(slug) if slug else slugify(title)
        if storage.get_article(target_slug):
            flash(
                f"An article with the slug '{target_slug}' already exists. Please choose a different title or slug.",
                "warning",
            )
            return render_template(
                "admin/editor.html",
                article={
                    "title": title,
                    "slug": slug,
                    "date": date,
                    "summary": summary,
                    "content": content,
                    "tags": [t.strip() for t in tags_raw.split(",") if t.strip()],
                },
                mode="create",
            )

        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        saved = storage.save_article(
            title=title,
            content=content,
            slug=target_slug,
            date=date,
            summary=summary,
            tags=tags,
        )

        flash(f"Article '{saved['title']}' published successfully!", "success")
        return redirect(url_for("article_detail", slug=saved["slug"]))

    # GET: display empty form with today's date
    default_article = {
        "title": "",
        "slug": "",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "summary": "",
        "content": "",
        "tags": [],
    }
    return render_template("admin/editor.html", article=default_article, mode="create")


@app.route("/admin/edit/<slug>", methods=["GET", "POST"])
@admin_required
def admin_edit_article(slug: str) -> Any:
    """Edit an existing article."""
    article = storage.get_article(slug)
    if not article:
        flash(f"Article with slug '{slug}' not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        new_slug = request.form.get("slug", "").strip()
        date = request.form.get("date", "").strip()
        summary = request.form.get("summary", "").strip()
        content = request.form.get("content", "").strip()
        tags_raw = request.form.get("tags", "")

        if not title or not content:
            flash("Title and Content are both required.", "danger")
            return render_template(
                "admin/editor.html",
                article={
                    "title": title,
                    "slug": new_slug or slug,
                    "date": date,
                    "summary": summary,
                    "content": content,
                    "tags": [t.strip() for t in tags_raw.split(",") if t.strip()],
                },
                mode="edit",
                original_slug=slug,
            )

        target_slug = slugify(new_slug) if new_slug else slugify(title)

        # If slug changed, ensure no collision with another post
        if target_slug != slug and storage.get_article(target_slug):
            flash(
                f"Cannot rename slug to '{target_slug}' because an article with that slug already exists.",
                "warning",
            )
            return render_template(
                "admin/editor.html",
                article={
                    "title": title,
                    "slug": new_slug,
                    "date": date,
                    "summary": summary,
                    "content": content,
                    "tags": [t.strip() for t in tags_raw.split(",") if t.strip()],
                },
                mode="edit",
                original_slug=slug,
            )

        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        saved = storage.save_article(
            title=title,
            content=content,
            slug=target_slug,
            date=date,
            summary=summary,
            tags=tags,
            old_slug=slug if target_slug != slug else None,
        )

        flash(f"Article '{saved['title']}' updated successfully!", "success")
        return redirect(url_for("article_detail", slug=saved["slug"]))

    return render_template(
        "admin/editor.html", article=article, mode="edit", original_slug=slug
    )


@app.route("/admin/delete/<slug>", methods=["POST"])
@admin_required
def admin_delete_article(slug: str) -> Any:
    """Delete an article."""
    if storage.delete_article(slug):
        flash(f"Article '{slug}' has been permanently deleted.", "info")
    else:
        flash(f"Article '{slug}' could not be found or deleted.", "warning")
    return redirect(url_for("admin_dashboard"))


# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------


@app.errorhandler(404)
def page_not_found(e: Any) -> Any:
    """Render custom 404 error page."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e: Any) -> Any:
    """Render custom 500 error page."""
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
