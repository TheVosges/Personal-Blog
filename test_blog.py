"""Automated test suite for Personal Blog.

Tests filesystem storage CRUD operations, authentication, and web routes.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app import app
from auth import verify_credentials
from storage import StorageManager, slugify


class StorageManagerTestCase(unittest.TestCase):
    """Test storage manager CRUD functionality."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.storage = StorageManager(storage_dir=self.test_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_slugify(self) -> None:
        self.assertEqual(slugify("Hello World!"), "hello-world")
        self.assertEqual(slugify("Python 3.11 & Modern Web"), "python-311-modern-web")
        self.assertEqual(slugify("   Trim   Spaces   "), "trim-spaces")

    def test_save_and_get_article(self) -> None:
        article = self.storage.save_article(
            title="My First Test Post",
            content="This is the content of my test article.\n\nSecond paragraph.",
            tags=["Python", "Testing"],
        )

        self.assertEqual(article["title"], "My First Test Post")
        self.assertEqual(article["slug"], "my-first-test-post")
        self.assertIn("Python", article["tags"])

        # Fetch it back
        fetched = self.storage.get_article("my-first-test-post")
        self.assertIsNotNone(fetched)
        assert fetched is not None
        self.assertEqual(fetched["title"], "My First Test Post")
        self.assertIn("Second paragraph", fetched["content"])

    def test_get_all_articles_sorted(self) -> None:
        self.storage.save_article(
            title="Older Post",
            content="Old content",
            date="2026-01-01",
            tags=["Old"],
        )
        self.storage.save_article(
            title="Newer Post",
            content="New content",
            date="2026-08-01",
            tags=["New"],
        )

        articles = self.storage.get_all_articles()
        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0]["title"], "Newer Post")
        self.assertEqual(articles[1]["title"], "Older Post")

    def test_filter_by_tag(self) -> None:
        self.storage.save_article(
            title="Python Post", content="Content", tags=["Python", "Code"]
        )
        self.storage.save_article(
            title="Design Post", content="Content", tags=["Design", "UI"]
        )

        python_posts = self.storage.get_all_articles(tag="Python")
        self.assertEqual(len(python_posts), 1)
        self.assertEqual(python_posts[0]["title"], "Python Post")

    def test_update_and_slug_rename(self) -> None:
        self.storage.save_article(
            title="Original Title", content="Original content", slug="orig-slug"
        )
        self.assertIsNotNone(self.storage.get_article("orig-slug"))

        # Update with new slug
        self.storage.save_article(
            title="Updated Title",
            content="Updated content",
            slug="new-slug",
            old_slug="orig-slug",
        )

        # Old slug should be gone, new slug present
        self.assertIsNone(self.storage.get_article("orig-slug"))
        updated = self.storage.get_article("new-slug")
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated["title"], "Updated Title")

    def test_delete_article(self) -> None:
        self.storage.save_article(
            title="Delete Me", content="To be deleted", slug="delete-me"
        )
        self.assertTrue(self.storage.delete_article("delete-me"))
        self.assertIsNone(self.storage.get_article("delete-me"))
        self.assertFalse(self.storage.delete_article("delete-me"))


class FlaskRoutesTestCase(unittest.TestCase):
    """Test Flask web routes and authentication."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["SECRET_KEY"] = "test-secret"

        # Point app storage to test dir
        self.orig_storage = app.view_functions["index"].__globals__["storage"]
        self.test_storage = StorageManager(storage_dir=self.test_dir)
        app.view_functions["index"].__globals__["storage"] = self.test_storage

        # Seed an article
        self.test_storage.save_article(
            title="Seeded Post",
            content="Hello world test content",
            slug="seeded-post",
            tags=["Testing"],
        )

        self.client = app.test_client()

    def tearDown(self) -> None:
        app.view_functions["index"].__globals__["storage"] = self.orig_storage
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_index_page(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Seeded Post", response.data)

    def test_article_detail_page(self) -> None:
        response = self.client.get("/article/seeded-post")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Hello world test content", response.data)

    def test_article_not_found(self) -> None:
        response = self.client.get("/article/non-existent-slug")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"404 - Article Not Found", response.data)

    def test_search_and_filter(self) -> None:
        response = self.client.get("/?q=Seeded")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Seeded Post", response.data)

        response_empty = self.client.get("/?q=NonExistentTerm")
        self.assertEqual(response_empty.status_code, 200)
        self.assertIn(b"No Articles Found", response_empty.data)

    def test_admin_route_protection(self) -> None:
        # Accessing /admin without login should redirect to /login
        response = self.client.get("/admin", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_admin_login_and_logout(self) -> None:
        # Failed login
        resp = self.client.post(
            "/login",
            data={"username": "admin", "password": "wrongpassword"},
            follow_redirects=True,
        )
        self.assertIn(b"Invalid username or password", resp.data)

        # Successful login
        resp = self.client.post(
            "/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Admin Dashboard", resp.data)

        # Access protected admin new page
        resp_new = self.client.get("/admin/new")
        self.assertEqual(resp_new.status_code, 200)
        self.assertIn(b"Write New Article", resp_new.data)

        # Logout
        resp_logout = self.client.get("/logout", follow_redirects=True)
        self.assertIn(b"logged out", resp_logout.data)

    def test_admin_create_and_delete_article(self) -> None:
        # Log in
        self.client.post("/login", data={"username": "admin", "password": "admin123"})

        # Create article
        resp_create = self.client.post(
            "/admin/new",
            data={
                "title": "Brand New Post",
                "slug": "brand-new-post",
                "date": "2026-08-13",
                "summary": "Short summary",
                "content": "Full content body text",
                "tags": "Python, Flask",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp_create.status_code, 200)
        self.assertIn(b"Brand New Post", resp_create.data)

        # Check post exists in storage
        post = self.test_storage.get_article("brand-new-post")
        self.assertIsNotNone(post)
        assert post is not None
        self.assertEqual(post["title"], "Brand New Post")

        # Delete post
        resp_delete = self.client.post(
            "/admin/delete/brand-new-post", follow_redirects=True
        )
        self.assertEqual(resp_delete.status_code, 200)
        self.assertIsNone(self.test_storage.get_article("brand-new-post"))


if __name__ == "__main__":
    unittest.main()
