import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import get_config

config = get_config()

def send_email(to_email, subject, html_body):
    """
    Hàm tiện ích để gửi email qua SMTP.
    Returns: (True, "") nếu thành công, (False, error_msg) nếu thất bại.
    """
    if not config.MAIL_USERNAME or not config.MAIL_PASSWORD:
        return False, "Email SMTP chưa được cấu hình. (Thiếu MAIL_USERNAME hoặc MAIL_PASSWORD)"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = config.MAIL_DEFAULT_SENDER
    msg['To'] = to_email

    part = MIMEText(html_body, 'html')
    msg.attach(part)

    try:
        server = smtplib.SMTP(config.MAIL_SERVER, config.MAIL_PORT)
        if config.MAIL_USE_TLS:
            server.starttls()
        server.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
        server.sendmail(config.MAIL_DEFAULT_SENDER, to_email, msg.as_string())
        server.quit()
        return True, ""
    except Exception as e:
        print(f"[Email Error] Gửi email thất bại: {e}")
        return False, str(e)

def send_reset_password_email(to_email, reset_url):
    """
    Gửi email chứa liên kết khôi phục mật khẩu.
    """
    subject = "Khôi phục mật khẩu - VietTranslate"
    
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
          <h2 style="color: #3b82f6;">Khôi phục mật khẩu</h2>
          <p>Chào bạn,</p>
          <p>Chúng tôi đã nhận được yêu cầu khôi phục mật khẩu cho tài khoản liên kết với địa chỉ email này.</p>
          <p>Vui lòng click vào nút bên dưới để đặt lại mật khẩu mới. Liên kết này sẽ hết hạn sau 30 phút.</p>
          <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background-color: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">ĐẶT LẠI MẬT KHẨU</a>
          </div>
          <p>Hoặc bạn có thể sao chép liên kết sau vào trình duyệt:</p>
          <p style="word-break: break-all; color: #666; font-size: 13px;">{reset_url}</p>
          <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
          <p style="font-size: 12px; color: #999;">Nếu bạn không yêu cầu điều này, xin vui lòng bỏ qua email. Mật khẩu của bạn vẫn an toàn.</p>
        </div>
      </body>
    </html>
    """
    
    return send_email(to_email, subject, html_body)

def send_verification_email(to_email, verification_url):
    """
    Gửi email chứa liên kết xác minh email đăng ký.
    """
    subject = "Xác minh địa chỉ email - VietTranslate"
    
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 8px;">
          <h2 style="color: #3b82f6;">Xác minh địa chỉ email</h2>
          <p>Chào bạn,</p>
          <p>Cảm ơn bạn đã đăng ký tài khoản tại VietTranslate.</p>
          <p>Vui lòng click vào nút bên dưới để xác minh địa chỉ email của bạn. Liên kết này sẽ hết hạn sau 24 giờ.</p>
          <div style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}" style="background-color: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">XÁC MINH EMAIL</a>
          </div>
          <p>Hoặc bạn có thể sao chép liên kết sau vào trình duyệt:</p>
          <p style="word-break: break-all; color: #666; font-size: 13px;">{verification_url}</p>
          <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
          <p style="font-size: 12px; color: #999;">Nếu bạn không đăng ký tài khoản, xin vui lòng bỏ qua email này.</p>
        </div>
      </body>
    </html>
    """
    
    return send_email(to_email, subject, html_body)
