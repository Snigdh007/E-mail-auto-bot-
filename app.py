import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from flask import Flask, render_template_string, request, jsonify
import threading
import time
from datetime import datetime

app = Flask(__name__)

# Store active bots (in-memory, will reset on restart)
active_bots = {}

class EmailBot:
    def __init__(self, user_email, app_password, keywords, reply_message, interval):
        self.user_email = user_email
        self.app_password = app_password
        self.keywords = [k.strip().lower() for k in keywords.split(',')]
        self.reply_message = reply_message
        self.interval = interval
        self.running = False
        self.thread = None
        self.logs = []
        
    def log(self, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        if len(self.logs) > 50:  # Keep only last 50 logs
            self.logs.pop(0)
        print(log_entry)
    
    def send_reply(self, to_email, subject):
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(self.user_email, self.app_password)
            
            msg = MIMEText(self.reply_message)
            msg['From'] = self.user_email
            msg['To'] = to_email
            msg['Subject'] = f"Re: {subject}"
            
            server.send_message(msg)
            server.quit()
            
            self.log(f"✅ Reply sent to: {to_email}")
            return True
        except Exception as e:
            self.log(f"❌ Send failed: {e}")
            return False
    
    def check_emails(self):
        self.log(f"🔍 Checking emails...")
        
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.user_email, self.app_password)
            mail.select('inbox')
            
            status, messages = mail.search(None, 'UNSEEN')
            email_ids = messages[0].split()
            
            self.log(f"Found {len(email_ids)} unread emails")
            
            for email_id in email_ids[-5:]:
                try:
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    email_message = email.message_from_bytes(msg_data[0][1])
                    
                    from_email = email_message['From']
                    subject = email_message['Subject'] or ""
                    
                    if self.user_email.lower() in from_email.lower():
                        continue
                    
                    self.log(f"📩 From: {from_email}")
                    
                    email_body = ""
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            if part.get_content_type() == "text/plain":
                                email_body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                break
                    else:
                        email_body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
                    
                    email_text = f"{subject} {email_body}".lower()
                    
                    keyword_found = False
                    for keyword in self.keywords:
                        if keyword in email_text:
                            self.log(f"🎯 KEYWORD FOUND: {keyword}")
                            self.send_reply(from_email, subject)
                            keyword_found = True
                            break
                    
                    if not keyword_found:
                        self.log(f"No keywords found in this email")
                        
                except Exception as e:
                    self.log(f"❌ Error processing email: {e}")
                    continue
            
            mail.logout()
            
        except Exception as e:
            self.log(f"❌ Email check failed: {e}")
    
    def run(self):
        self.running = True
        self.log(f"🚀 Bot started! Checking every {self.interval} seconds")
        self.log(f"🎯 Keywords: {', '.join(self.keywords)}")
        
        while self.running:
            try:
                self.check_emails()
                time.sleep(self.interval)
            except Exception as e:
                self.log(f"❌ Error in bot loop: {e}")
                time.sleep(10)
    
    def start(self):
        if not self.running:
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()
            return True
        return False
    
    def stop(self):
        self.running = False
        self.log("🛑 Bot stopped by user")

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Email Auto-Reply Bot</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        .card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        input, textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        textarea {
            resize: vertical;
            min-height: 80px;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .btn-stop {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            margin-top: 10px;
        }
        .status {
            text-align: center;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            font-weight: 600;
        }
        .status.active {
            background: #d4edda;
            color: #155724;
        }
        .status.inactive {
            background: #f8d7da;
            color: #721c24;
        }
        .logs {
            background: #1e1e1e;
            color: #00ff00;
            padding: 20px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
            margin-top: 20px;
        }
        .logs div {
            margin-bottom: 5px;
        }
        .warning {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        .info {
            background: #d1ecf1;
            border-left: 4px solid #17a2b8;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        @media (max-width: 600px) {
            .header h1 { font-size: 1.8em; }
            .card { padding: 20px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📧 Email Auto-Reply Bot</h1>
            <p>Automate your email responses effortlessly</p>
        </div>

        <div class="card">
            <div class="info">
                <strong>ℹ️ How to get Gmail App Password:</strong><br>
                1. Go to Google Account → Security<br>
                2. Enable 2-Factor Authentication<br>
                3. Search "App Passwords"<br>
                4. Generate password for "Mail"<br>
                5. Copy the 16-character password
            </div>

            <form id="botForm">
                <div class="form-group">
                    <label>📧 Your Gmail Address</label>
                    <input type="email" id="email" placeholder="youremail@gmail.com" required>
                </div>

                <div class="form-group">
                    <label>🔑 Gmail App Password</label>
                    <input type="password" id="password" placeholder="xxxx xxxx xxxx xxxx" required>
                </div>

                <div class="form-group">
                    <label>⏱️ Check Interval (seconds)</label>
                    <input type="number" id="interval" value="60" min="30" required>
                </div>

                <div class="form-group">
                    <label>🎯 Keywords (comma-separated)</label>
                    <input type="text" id="keywords" placeholder="sponsorship, collaboration, partnership" required>
                </div>

                <div class="form-group">
                    <label>💬 Auto-Reply Message</label>
                    <textarea id="reply" placeholder="Thank you for your email! We'll get back to you soon." required></textarea>
                </div>

                <button type="submit" class="btn" id="startBtn">🚀 Start Bot</button>
                <button type="button" class="btn btn-stop" id="stopBtn" style="display:none;">🛑 Stop Bot</button>
            </form>

            <div id="status"></div>
        </div>

        <div class="card" id="logsCard" style="display:none;">
            <h3>📊 Bot Activity Logs</h3>
            <div class="logs" id="logs"></div>
        </div>
    </div>

    <script>
        let botId = null;
        let logInterval = null;

        document.getElementById('botForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const data = {
                email: document.getElementById('email').value,
                password: document.getElementById('password').value,
                interval: parseInt(document.getElementById('interval').value),
                keywords: document.getElementById('keywords').value,
                reply: document.getElementById('reply').value
            };

            document.getElementById('startBtn').disabled = true;
            document.getElementById('startBtn').textContent = '⏳ Starting...';

            try {
                const response = await fetch('/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (result.success) {
                    botId = result.bot_id;
                    document.getElementById('startBtn').style.display = 'none';
                    document.getElementById('stopBtn').style.display = 'block';
                    document.getElementById('logsCard').style.display = 'block';
                    showStatus('Bot is running! 🎉', 'active');
                    
                    // Start fetching logs
                    logInterval = setInterval(fetchLogs, 2000);
                } else {
                    alert('Error: ' + result.error);
                    document.getElementById('startBtn').disabled = false;
                    document.getElementById('startBtn').textContent = '🚀 Start Bot';
                }
            } catch (error) {
                alert('Error starting bot: ' + error);
                document.getElementById('startBtn').disabled = false;
                document.getElementById('startBtn').textContent = '🚀 Start Bot';
            }
        });

        document.getElementById('stopBtn').addEventListener('click', async () => {
            if (!botId) return;

            try {
                const response = await fetch('/stop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ bot_id: botId })
                });

                const result = await response.json();

                if (result.success) {
                    clearInterval(logInterval);
                    document.getElementById('startBtn').style.display = 'block';
                    document.getElementById('startBtn').disabled = false;
                    document.getElementById('startBtn').textContent = '🚀 Start Bot';
                    document.getElementById('stopBtn').style.display = 'none';
                    showStatus('Bot stopped', 'inactive');
                    botId = null;
                }
            } catch (error) {
                alert('Error stopping bot: ' + error);
            }
        });

        async function fetchLogs() {
            if (!botId) return;

            try {
                const response = await fetch(`/logs?bot_id=${botId}`);
                const result = await response.json();

                if (result.logs) {
                    const logsDiv = document.getElementById('logs');
                    logsDiv.innerHTML = result.logs.map(log => `<div>${log}</div>`).join('');
                    logsDiv.scrollTop = logsDiv.scrollHeight;
                }
            } catch (error) {
                console.error('Error fetching logs:', error);
            }
        }

        function showStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = message;
            statusDiv.className = 'status ' + type;
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start', methods=['POST'])
def start_bot():
    try:
        data = request.json
        
        # Create bot instance
        bot = EmailBot(
            user_email=data['email'],
            app_password=data['password'],
            keywords=data['keywords'],
            reply_message=data['reply'],
            interval=data['interval']
        )
        
        # Test connection first
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(data['email'], data['password'])
            mail.logout()
        except Exception as e:
            return jsonify({'success': False, 'error': f'Login failed: {str(e)}'})
        
        # Generate bot ID and start
        bot_id = f"{data['email']}_{int(time.time())}"
        active_bots[bot_id] = bot
        bot.start()
        
        return jsonify({'success': True, 'bot_id': bot_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/stop', methods=['POST'])
def stop_bot():
    try:
        data = request.json
        bot_id = data['bot_id']
        
        if bot_id in active_bots:
            active_bots[bot_id].stop()
            del active_bots[bot_id]
            return jsonify({'success': True})
        
        return jsonify({'success': False, 'error': 'Bot not found'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/logs', methods=['GET'])
def get_logs():
    try:
        bot_id = request.args.get('bot_id')
        
        if bot_id in active_bots:
            return jsonify({'logs': active_bots[bot_id].logs})
        
        return jsonify({'logs': []})
        
    except Exception as e:
        return jsonify({'logs': [], 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
