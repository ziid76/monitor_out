import requests
import time
import logging
import os
from django.conf import settings
from django.utils import timezone
from bs4 import BeautifulSoup
from .models import MonitorTarget, MonitoringLog
from .models import MonitorTarget, MonitoringLog
import json

# --- KakaoWork Notification Internal Functions ---
def get_kakaowork_config():
    return {
        "BASE_URL": "https://api.kakaowork.com/v1",
        "BEARER_TOKEN": os.getenv("KAKAOWORK_TOKEN"),
        "HEADERS": {
            "Authorization": f"Bearer {os.getenv('KAKAOWORK_TOKEN')}",
            "Content-Type": "application/json"
        }
    }

def find_user_id_by_email(email):
    config = get_kakaowork_config()
    if not config["BEARER_TOKEN"]: return None
    api_url = f"{config['BASE_URL']}/users.find_by_email"
    try:
        response = requests.get(api_url, headers=config["HEADERS"], params={'email': email}, verify=False)
        data = response.json()
        return data['user']['id'] if data.get('success') and data.get('user') else None
    except: return None

def open_conversation(user_id):
    config = get_kakaowork_config()
    api_url = f"{config['BASE_URL']}/conversations.open"
    try:
        response = requests.post(api_url, headers=config["HEADERS"], data=json.dumps({'user_id': user_id}), verify=False)
        data = response.json()
        return data['conversation']['id'] if data.get('success') and data.get('conversation') else None
    except: return None

def send_kakao_message(email, text, message_type="box", button_text=None, button_url=None, header_text=None):
    user_id = find_user_id_by_email(email)
    if not user_id: return False
    conv_id = open_conversation(user_id)
    if not conv_id: return False
    
    config = get_kakaowork_config()
    api_url = f"{config['BASE_URL']}/messages.send"
    payload = {
        "conversation_id": conv_id,
        "text": text,
        "blocks": [
            {"type": "header", "text": header_text or "Web Monitor", "style": "blue"},
            {"type": "text", "text": text}
        ]
    }
    if button_text and button_url:
        payload["blocks"].append({
            "type": "button", "text": button_text, "style": "default",
            "action": {"type": "open_system_browser", "value": button_url}
        })
    
    try:
        requests.post(api_url, headers=config["HEADERS"], data=json.dumps(payload), verify=False)
        return True
    except: return False

def pin_target_response(target):
    """
    Copies the current last_response of a target to the pinned_responses folder.
    Returns the pinned filename if successful, None otherwise.
    """
    import shutil
    try:
        safe_name = "".join([c for c in target.name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_')
        src_filename = f"last_response_{target.id}_{safe_name}.html"
        src_path = os.path.join(settings.BASE_DIR, 'logs', 'monitoring_debug', src_filename)
        
        if not os.path.exists(src_path):
            return None
            
        pin_dir = os.path.join(settings.BASE_DIR, 'logs', 'pinned_responses')
        if not os.path.exists(pin_dir):
            os.makedirs(pin_dir)
            
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        dst_filename = f"auto_pinned_{target.id}_{timestamp}_{safe_name}.html"
        dst_path = os.path.join(pin_dir, dst_filename)
        
        shutil.copy2(src_path, dst_path)
        return dst_filename
    except Exception as e:
        logger.error(f"Failed to auto-pin response for {target.name}: {str(e)}")
        return None

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# Standard user agent to avoid bot blocking
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
}

def validate_signatures_requests(html, target):
    """
    Validate site content using BeautifulSoup for requests-based check.
    Returns (is_valid, reason)
    """
    # lxml 파서가 html.parser보다 훨씬 빠르고 CPU를 적게 사용함
    soup = BeautifulSoup(html, 'lxml')
    
    # Title check
    if target.signature_title:
        page_title = soup.title.string if soup.title else ""
        if target.signature_title not in (page_title or ""):
            return False, f"Title mismatch: expected '{target.signature_title}', got '{page_title}'"
            
    # Text check
    if target.signature_text:
        text_sigs = [t.strip() for t in target.signature_text.split(',') if t.strip()]
        for text in text_sigs:
            if text not in html:
                return False, f"Text not found: '{text}'"
                
    # DOM check
    if target.signature_dom:
        dom_sigs = [d.strip() for d in target.signature_dom.split(',') if d.strip()]
        for selector in dom_sigs:
            if not soup.select(selector):
                return False, f"DOM Selector not found: '{selector}'"
            
    return True, ""

def save_response_debug(target, content):
    """
    Save the raw HTML response for debugging.
    Keeps only the latest result per target to avoid disk bloat.
    """
    try:
        debug_dir = os.path.join(settings.BASE_DIR, 'logs', 'monitoring_debug')
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
            
        safe_name = "".join([c for c in target.name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_')
        filename = f"last_response_{target.id}_{safe_name}.html"
        filepath = os.path.join(debug_dir, filename)
        
        # CPU 부하를 줄이기 위해 너무 큰 파일(예: 1MB 이상)은 디버그 파일로 저장하지 않음
        if len(content) > 1024 * 1024:
            content = content[:1024 * 512] + "\n... [Content truncated due to size] ..."
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
    except Exception as e:
        logger.error(f"Failed to save debug response for {target.name}: {str(e)}")

def run_check_requests(target):
    start_time = time.time()
    try:
        # stream=True를 사용하여 헤더를 먼저 읽고 본문 크기를 제한함
        response = requests.get(target.url, timeout=20, verify=False, headers=DEFAULT_HEADERS, stream=True)
        
        # 파일 크기 제한 (최대 2MB까지만 허용, 그 이상은 CPU/메모리 보호 차원에서 차단)
        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > 2 * 1024 * 1024:
            return "DOWN", "Response too large (>2MB)", time.time() - start_time

        # 실제 본문 읽기 (가장 많은 CPU/메모리 사용 시점)
        html_content = response.text
        response_time = time.time() - start_time
        
        # 한글 깨짐 방지: 무조건 apparent_encoding을 돌리지 않고, ISO-8859-1일 때만 제한적으로 사용
        if response.encoding == 'ISO-8859-1':
            # apparent_encoding은 전체 텍스트를 분석하므로 큰 파일에서 CPU 킬러가 됨
            # 여기서는 본문의 앞부분만으로 추측하도록 최적화 가능하지만, 인코딩이 명시 안된 경우에만 수행
            if len(html_content) < 500 * 1024: # 500KB 미만일 때만 수행
                response.encoding = response.apparent_encoding
                html_content = response.text
            else:
                response.encoding = 'utf-8' # 큰 파일은 그냥 utf-8로 가정
                html_content = response.text

        # 응답 결과 파일 저장 (디버깅용)
        save_response_debug(target, html_content)

        if response.status_code != 200:
            error_detail = f"HTTP Status {response.status_code}"
            return "DOWN", error_detail, response_time
            
        is_valid, reason = validate_signatures_requests(html_content, target)
        if is_valid:
            return "UP", "", response_time
        else:
            return "DOWN", reason, response_time
            
    except requests.exceptions.Timeout:
        return "DOWN", "Connection Timeout (20s)", time.time() - start_time
    except requests.exceptions.ConnectionError as e:
        return "DOWN", f"Connection Error: {str(e)}", time.time() - start_time
    except Exception as e:
        logger.exception(f"Unexpected error checking {target.name}")
        return "DOWN", f"Unexpected Error: {str(e)}", time.time() - start_time

def notify_users(target, event_type, error_msg=""):
    """
    Send KakaoWork message to selected recipients using common.message_views.send_kakao_message
    """
    recipients = target.recipients.all()
    if not recipients:
        return
        
    status_emoji = "🚨" if event_type == "DOWN" else "✅"
    title = f"{status_emoji} 장애 발생" if event_type == "DOWN" else f"{status_emoji} 서비스 복구"
    
    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    
    message_content = f"사이트: {target.name}\nURL: {target.url}\n시간: {timestamp}"
    if event_type == "DOWN" and error_msg:
        message_content += f"\n❗ 원인: {error_msg}"
        
    for user in recipients:
        if user.email:
            send_kakao_message(
                email=user.email,
                text=message_content,
                message_type="box",
                button_text="상세보기",
                button_url=target.url, # Or link to dashboard
                header_text=title
            )

def perform_monitoring(target_id):
    try:
        target = MonitorTarget.objects.get(id=target_id)
    except MonitorTarget.DoesNotExist:
        return

    # --- Retry Logic ---
    # Attempts: 1 (initial) + 3 (retries) = 4 total
    max_retries = 3
    attempts = 0
    status, error_msg, response_time = "DOWN", "Pending initial check", 0
    pinned_filename = None
    
    while attempts <= max_retries:
        attempts += 1
        status, error_msg, response_time = run_check_requests(target)
        
        if status == "UP":
            if attempts > 1:
                logger.info(f"Monitoring [UP] {target.name} confirmed after {attempts-1} retries.")
            break
        else:
            # If this is the FIRST failure in the cycle, pin the response for evidence
            if pinned_filename is None:
                pinned_filename = pin_target_response(target)
                if pinned_filename:
                    logger.info(f"Auto-pinned first failure response for {target.name}: {pinned_filename}")

            if attempts <= max_retries:
                # transient failure, wait and retry
                log_msg = f"Monitoring attempt {attempts}/{max_retries+1} failed for {target.name}: {error_msg}. Retrying in 3s..."
                print(log_msg)
                logger.warning(log_msg)
                time.sleep(3)
            else:
                # All retries exhausted
                logger.error(f"Monitoring [DOWN] {target.name} failed after all {attempts} attempts.")

    # --- Post-Check Processing ---
    prev_status = target.last_status
    now = timezone.now()
    
    if prev_status != status:
        target.last_status_changed_at = now

    # Save target status
    target.last_status = status
    target.last_checked_at = now
    target.save()
    
    if status == "DOWN":
        summary_log = f"Monitoring [DOWN] {target.name}: {error_msg} (After {attempts} attempts)"
        print(summary_log)
        logger.error(summary_log)
    else:
        summary_log = f"Monitoring [UP] {target.name} ({response_time:.3f}s)"
        if attempts > 1:
            summary_log += f" [Recovered after {attempts-1} retries]"
        print(summary_log)
        logger.info(summary_log)

    # Create detailed log
    log = MonitoringLog.objects.create(
        target=target,
        status=status,
        response_time=response_time,
        error_message=summary_log[:500],
        pinned_file=pinned_filename # Store the pinned file if any attempt failed
    )
    
    # Notification logic (only on actual status change)
    if prev_status and prev_status != status:
        if status == "DOWN":
            notify_users(target, "DOWN", error_msg)
        elif status == "UP" and prev_status == "DOWN":
            notify_users(target, "RECOVERED")
    elif not prev_status and status == "DOWN":
        notify_users(target, "DOWN", error_msg)
        
    return log
