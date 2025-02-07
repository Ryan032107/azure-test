import unittest
from unittest.mock import patch
from app import app, send_verification_email, generate_token

class EmailTestCase(unittest.TestCase):
    def setUp(self):
        # 設置 Flask 測試客戶端
        self.app = app.test_client()
        self.app.testing = True

    @patch('flask_mail.Mail.send')
    def test_send_verification_email(self, mock_mail_send):
        # 測試 email 發送功能
        email = 'pp657783@gmail.com'
        token = generate_token(email)

        # 使用 app_context() 明確啟用應用上下文
        with app.app_context():
            # 發送驗證郵件
            send_verification_email(email, token)

        # 確認 send 函數是否被呼叫
        mock_mail_send.assert_called_once()

if __name__ == '__main__':
    unittest.main()
