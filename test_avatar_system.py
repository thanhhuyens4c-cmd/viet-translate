"""
Unit and integration test suite for VietTranslate Avatar System.
Uses standard library unittest.
"""

import os
import io
import unittest
from app import app, db, User, HirerProfile, TranslatorProfile, AVATAR_UPLOAD_FOLDER, save_user_avatar, delete_user_avatar

class TestAvatarSystem(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_user_avatar_url_resolution(self):
        """Test User.avatar_url for various formats."""
        u = User(id=999, name="Test User", email="test_avatar@example.com", role="hirer")
        
        # 1. No avatar
        u.avatar = None
        self.assertIsNone(u.avatar_url)
        
        u.avatar = ""
        self.assertIsNone(u.avatar_url)
        
        # 2. Local uploaded filename
        u.avatar = "avatar_u999_12345.jpg"
        self.assertEqual(u.avatar_url, "/static/uploads/avatars/avatar_u999_12345.jpg")
        
        # 3. External HTTP / HTTPS URL
        u.avatar = "https://images.unsplash.com/photo-1534528741775"
        self.assertEqual(u.avatar_url, "https://images.unsplash.com/photo-1534528741775")
        
        # 4. Leading slash
        u.avatar = "/static/uploads/custom.png"
        self.assertEqual(u.avatar_url, "/static/uploads/custom.png")
        
        # 5. Base64 Data URI
        u.avatar = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY44YAAAAASUVORK5CYII="
        self.assertTrue(u.avatar_url.startswith("data:image/png;base64,"))

    def test_hirer_profile_avatar_url(self):
        """Test HirerProfile.avatar_url resolution logic."""
        u = User(id=888, name="Hirer Test", email="hirer_avatar@example.com", role="hirer", avatar="hirer_u888.jpg")
        p = HirerProfile(user_id=888)
        p.user = u
        
        # Logo is empty, falls back to user avatar
        p.logo = None
        self.assertEqual(p.avatar_url, "/static/uploads/avatars/hirer_u888.jpg")
        
        # Logo is set to filename
        p.logo = "company_logo.png"
        self.assertEqual(p.avatar_url, "/static/uploads/logos/company_logo.png")
        
        # Logo is external URL
        p.logo = "https://example.com/logo.png"
        self.assertEqual(p.avatar_url, "https://example.com/logo.png")

    def test_serve_avatar_routes(self):
        """Test avatar serving routes /static/uploads/avatars/ and /uploads/avatars/."""
        os.makedirs(AVATAR_UPLOAD_FOLDER, exist_ok=True)
        test_filename = "test_route_avatar.jpg"
        file_path = os.path.join(AVATAR_UPLOAD_FOLDER, test_filename)
        
        with open(file_path, "wb") as f:
            f.write(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xFF\xDB")
            
        res1 = None
        res2 = None
        res3 = None
        try:
            # Route 1: /static/uploads/avatars/<filename>
            res1 = self.client.get(f"/static/uploads/avatars/{test_filename}")
            self.assertEqual(res1.status_code, 200)
            self.assertIn("image/", res1.content_type)
            self.assertEqual(res1.headers.get("Cache-Control"), "public, max-age=86400")
            
            # Route 2: /uploads/avatars/<filename>
            res2 = self.client.get(f"/uploads/avatars/{test_filename}")
            self.assertEqual(res2.status_code, 200)
            self.assertIn("image/", res2.content_type)
            
            # Route 3: Non-existent file
            res3 = self.client.get("/static/uploads/avatars/non_existent_avatar_99999.jpg")
            self.assertEqual(res3.status_code, 404)
        finally:
            if res1:
                res1.close()
            if res2:
                res2.close()
            if res3:
                res3.close()
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def test_save_and_delete_user_avatar(self):
        """Test save_user_avatar and delete_user_avatar dual persistence and cleanup."""
        class DummyFile:
            def __init__(self, filename, content):
                self.filename = filename
                self.stream = io.BytesIO(content)
            def read(self, *args):
                return self.stream.read(*args)
            def seek(self, *args):
                return self.stream.seek(*args)
            def tell(self):
                return len(self.stream.getvalue())
            def save(self, dst):
                with open(dst, "wb") as f:
                    f.write(self.stream.getvalue())

        dummy_file = DummyFile("my_photo.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01")
        ok, filename = save_user_avatar(dummy_file, user_id=777)
        self.assertTrue(ok)
        self.assertIsNotNone(filename)
        self.assertTrue(filename.startswith("avatar_u777_"))
        self.assertTrue(filename.endswith(".png"))
        
        target1 = os.path.join(AVATAR_UPLOAD_FOLDER, filename)
        self.assertTrue(os.path.exists(target1))
        
        local_static = os.path.join(app.root_path, 'static', 'uploads', 'avatars')
        target2 = os.path.join(local_static, filename)
        if os.path.abspath(AVATAR_UPLOAD_FOLDER) != os.path.abspath(local_static):
            self.assertTrue(os.path.exists(target2))
            
        deleted = delete_user_avatar(filename)
        self.assertTrue(deleted)
        self.assertFalse(os.path.exists(target1))
        if os.path.exists(target2):
            self.assertFalse(os.path.exists(target2))

if __name__ == "__main__":
    unittest.main()
