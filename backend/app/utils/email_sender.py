import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from jinja2 import Environment, BaseLoader

logger = logging.getLogger(__name__)

# 优先级标签映射
PRIORITY_LABELS = {
    'low': '低',
    'medium': '中',
    'high': '高',
    'urgent': '紧急',
    'normal': '普通',
}

# 简单模板（内联，避免文件路径问题）
TEMPLATES = {
    "task_assigned": {
        "subject": "【ODMS】新任务分配: {{ task_title }}",
        "body": """
<h3>您好, {{ assignee_name }}</h3>
<p><strong>{{ assigner_name }}</strong> 给您分配了一个新任务：</p>
<div style="background:#f5f5f5;padding:16px;border-radius:4px;margin:12px 0;">
  <p><strong>任务名称：</strong>{{ task_title }}</p>
  <p><strong>所属事项：</strong>{{ matter_title }}</p>
  <p><strong>优先级：</strong>{{ priority_label }}</p>
  {% if due_time %}<p><strong>截止时间：</strong>{{ due_time }}</p>{% endif %}
</div>
<p>请登录系统查看详情。</p>
<p style="color:#999;font-size:12px;">此邮件由 ODMS 系统自动发送，请勿回复。</p>
"""
    },
    "node_advanced": {
        "subject": "【ODMS】流程推进: {{ matter_title }} → {{ node_name }}",
        "body": """
<h3>您好, {{ owner_name }}</h3>
<p>事项 <strong>{{ matter_title }}</strong> 已推进到 <strong>{{ node_name }}</strong> 阶段，需要您处理。</p>
<p>请登录系统查看并推进流程。</p>
<p style="color:#999;font-size:12px;">此邮件由 ODMS 系统自动发送，请勿回复。</p>
"""
    },
    "due_soon": {
        "subject": "【ODMS】到期预警: {{ matter_title }}",
        "body": """
<h3>您好, {{ owner_name }}</h3>
<p>以下事项即将到期，请及时处理：</p>
<div style="background:#fff3cd;padding:16px;border-radius:4px;margin:12px 0;border:1px solid #ffc107;">
  <p><strong>事项名称：</strong>{{ matter_title }}</p>
  <p><strong>截止日期：</strong>{{ due_date }}</p>
  <p><strong>剩余天数：</strong>{{ days_remaining }} 天</p>
</div>
<p style="color:#999;font-size:12px;">此邮件由 ODMS 系统自动发送，请勿回复。</p>
"""
    },
    "overdue": {
        "subject": "【ODMS】逾期提醒: {{ matter_title }}",
        "body": """
<h3>您好, {{ owner_name }}</h3>
<p>以下事项已逾期，请尽快处理：</p>
<div style="background:#f8d7da;padding:16px;border-radius:4px;margin:12px 0;border:1px solid #dc3545;">
  <p><strong>事项名称：</strong>{{ matter_title }}</p>
  <p><strong>截止日期：</strong>{{ due_date }}</p>
  <p><strong>已逾期：</strong>{{ days_overdue }} 天</p>
</div>
<p style="color:#999;font-size:12px;">此邮件由 ODMS 系统自动发送，请勿回复。</p>
"""
    },
    "comment_added": {
        "subject": "【ODMS】新评论: {{ matter_title }}",
        "body": """
<h3>您好, {{ user_name }}</h3>
<p><strong>{{ commenter_name }}</strong> 在事项 <strong>{{ matter_title }}</strong> 中添加了评论：</p>
<div style="background:#f5f5f5;padding:16px;border-radius:4px;margin:12px 0;">
  <p>{{ comment_content }}</p>
</div>
<p style="color:#999;font-size:12px;">此邮件由 ODMS 系统自动发送，请勿回复。</p>
"""
    },
    "daily_digest": {
        "subject": "【ODMS】每日工作摘要 ({{ date }})",
        "body": """
<h3>{{ user_name }}，您好</h3>
<p>以下是您今日的工作摘要：</p>
<div style="background:#f5f5f5;padding:16px;border-radius:4px;margin:12px 0;">
  <p><strong>待办任务：</strong>{{ pending_tasks }} 个</p>
  <p><strong>逾期事项：</strong>{{ overdue_count }} 个</p>
  <p><strong>今日完成：</strong>{{ completed_today }} 个</p>
  <p><strong>新通知：</strong>{{ unread_notifications }} 条</p>
</div>
<p>请登录系统查看详情。</p>
<p style="color:#999;font-size:12px;">此邮件由 ODMS 系统自动发送，请勿回复。</p>
"""
    },
}

# Jinja2 env
env = Environment(loader=BaseLoader())


class EmailSender:
    def __init__(self):
        from app.config import get_settings
        settings = get_settings()
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_addr = settings.SMTP_FROM_ADDR or settings.SMTP_USERNAME
        self.from_name = settings.SMTP_FROM_NAME
        self.use_tls = settings.SMTP_USE_TLS

    def _render_template(self, template_name: str, context: dict) -> tuple:
        tpl = TEMPLATES.get(template_name)
        if not tpl:
            raise ValueError(f"Template not found: {template_name}")

        subject_tpl = env.from_string(tpl["subject"])
        body_tpl = env.from_string(tpl["body"])

        subject = subject_tpl.render(**context)
        body = body_tpl.render(**context)
        return subject, body

    async def send(self, to_email: str, template_name: str, context: dict, cc: list = None):
        """发送邮件"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._send_sync, to_email, template_name, context, cc
        )

    def _send_sync(self, to_email: str, template_name: str, context: dict, cc: list = None):
        subject, body_html = self._render_template(template_name, context)

        msg = MIMEMultipart('alternative')
        msg['From'] = f"{Header(self.from_name, 'utf-8')} <{self.from_addr}>"
        msg['To'] = to_email
        msg['Subject'] = Header(subject, 'utf-8')
        if cc:
            msg['Cc'] = ', '.join(cc)

        msg.attach(MIMEText(body_html, 'html', 'utf-8'))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as smtp:
                if self.use_tls:
                    smtp.starttls()
                smtp.login(self.username, self.password)
                smtp.sendmail(
                    self.from_addr, [to_email] + (cc or []), msg.as_string()
                )
            return True
        except (smtplib.SMTPException, ConnectionError, TimeoutError, OSError) as exc:
            logger.warning("Email send failed to %s: %s", to_email, exc)
            return False

    def send_sync(self, to_email: str, template_name: str, context: dict, cc: list = None):
        """同步发送邮件（供 Celery 任务等同步上下文使用）"""
        return self._send_sync(to_email, template_name, context, cc)


email_sender = EmailSender()
