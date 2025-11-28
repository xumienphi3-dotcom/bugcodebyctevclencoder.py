# BUG CODE BY CTEVCL ENCODER
# COMPLETE VERSION - FIXED TO RUN TARGET TOOLS

import sys
import threading
import traceback
import inspect
import functools
import runpy
import os

# --- PHẦN 1: CẤU HÌNH VÀ HÀM LOGGING ---

if getattr(sys, "_hook_debug_installed", False):
    # Nếu đã cài hook rồi thì không cài lại để tránh lỗi lặp
    pass
else:
    sys._hook_debug_installed = True
    LOG_FILE = "bug.log"

    def safe_repr(obj):
        try:
            return str(obj)
        except Exception:
            try:
                return repr(obj)
            except Exception:
                return f"<{type(obj).__name__} object>"

    def log_output(msg: str):
        """Ghi log ra màn hình và file"""
        try:
            print(msg, file=sys.stderr)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

    def log_with_trace(prefix, detail=""):
        """Ghi log kèm stack trace để biết code nào gọi request"""
        stack = "".join(traceback.format_stack(limit=6))
        log_output(f"{prefix} {detail}\n[STACKTRACE]\n{stack}")

    _local_ctx = threading.local()
    _local_ctx.in_chuyenhuong = False

    def in_chuyenhuong():
        return getattr(_local_ctx, "in_chuyenhuong", False)

    def skip_url(url):
        """Bỏ qua các URL không cần thiết (như facebook tracking)"""
        try:
            url_lower = (url or "").lower()
            if "facebook.com" in url_lower and "web.facebook.com" not in url_lower:
                return True
            if "web.facebook.com" in url_lower:
                return True
            return False
        except Exception:
            return False

    # --- PHẦN 2: CÀI ĐẶT HOOK CHO REQUESTS ---
    try:
        import requests
    except Exception:
        requests = None

    if requests is not None:
        try:
            _old_request = requests.Session.request

            def _hook_request(self, method, url, *a, **k):
                try:
                    if skip_url(url):
                        return _old_request(self, method, url, *a, **k)
                    
                    tag = " [ở đây]" if in_chuyenhuong() else ""
                    log_with_trace(f"[HOOK][requests][REQ]{tag}", f"{safe_repr(method)} {safe_repr(url)} args={safe_repr(a)}, kwargs={safe_repr(k)}")
                    
                    r = _old_request(self, method, url, *a, **k)
                    
                    try:
                        status = getattr(r, "status_code", None)
                        headers = dict(getattr(r, "headers", {}) or {})
                        body = getattr(r, "text", None)
                    except Exception:
                        status = headers = body = None
                    
                    log_output(f"[HOOK][requests][RESP]{tag} status={status} headers={headers} body={safe_repr(body)}")
                    return r
                except Exception as e:
                    log_output(f"[HOOK][requests][ERROR] {e}\n{traceback.format_exc()}")
                    return _old_request(self, method, url, *a, **k)

            requests.Session.request = _hook_request

            # Hook thêm các method tắt như requests.get, requests.post...
            for _m in ["get", "post", "put", "delete", "head", "options", "patch"]:
                if hasattr(requests, _m):
                    _old = getattr(requests, _m)
                    def _wrap(func, name):
                        def f(*a, **k):
                            try:
                                url = k.get("url") or (a[0] if a else "")
                                if skip_url(url):
                                    return func(*a, **k)
                                tag = " [ở đây]" if in_chuyenhuong() else ""
                                log_with_trace(f"[HOOK][requests.{name}][REQ]{tag}", f"args={safe_repr(a)}, kwargs={safe_repr(k)}")
                                r = func(*a, **k)
                                try:
                                    status = getattr(r, "status_code", None)
                                    headers = getattr(r, "headers", None)
                                    body = getattr(r, "text", None)
                                except Exception:
                                    status = headers = body = None
                                log_output(f"[HOOK][requests.{name}][RESP]{tag} status={status} headers={headers} body={safe_repr(body)}")
                                return r
                            except Exception as e:
                                log_output(f"[HOOK][requests.{name}][ERROR] {e}\n{traceback.format_exc()}")
                                return func(*a, **k)
                        return f
                    setattr(requests, _m, _wrap(_old, _m))

            log_output("[bugcodebyctevclencoder] requests hook installed")
        except Exception:
            log_output("[bugcodebyctevclencoder] failed to install requests hook\n" + traceback.format_exc())

    # --- PHẦN 3: CÀI ĐẶT HOOK CHO HTTP.CLIENT ---
    try:
        import http.client as http_client
    except Exception:
        http_client = None

    if http_client is not None:
        try:
            _old_http_req = http_client.HTTPConnection.request

            def _hook_http_request(self, method, url, body=None, headers=None, *a, **k):
                try:
                    host = getattr(self, "host", "")
                    full_url = f"{host}{url}"
                    if skip_url(full_url):
                        return _old_http_req(self, method, url, body, headers, *a, **k)
                    tag = " [ở đây]" if in_chuyenhuong() else ""
                    log_with_trace(f"[HOOK][http.client]{tag}", f"{safe_repr(method)} host={safe_repr(host)} url={safe_repr(url)} body={safe_repr(body)} headers={safe_repr(headers)}")
                    return _old_http_req(self, method, url, body, headers, *a, **k)
                except Exception as e:
                    log_output(f"[HOOK][http.client][ERROR] {e}\n{traceback.format_exc()}")
                    return _old_http_req(self, method, url, body, headers, *a, **k)

            http_client.HTTPConnection.request = _hook_http_request
            log_output("[bugcodebyctevclencoder] http.client hook installed")
        except Exception:
            log_output("[bugcodebyctevclencoder] failed to install http.client hook\n" + traceback.format_exc())

    # --- PHẦN 4: CÀI ĐẶT HOOK CHO CURL_CFFI ---
    try:
        from curl_cffi import requests as curl_requests  # type: ignore
    except Exception:
        curl_requests = None

    if curl_requests is not None:
        try:
            _old_curl_request = curl_requests.Session.request

            def _hook_curl_request(self, method, url, *a, **k):
                try:
                    if skip_url(url):
                        return _old_curl_request(self, method, url, *a, **k)
                    tag = " [ở đây]" if in_chuyenhuong() else ""
                    log_with_trace(f"[HOOK][curl_cffi][REQ]{tag}", f"{safe_repr(method)} {safe_repr(url)} args={safe_repr(a)}, kwargs={safe_repr(k)}")
                    r = _old_curl_request(self, method, url, *a, **k)
                    try:
                        status = getattr(r, "status_code", None)
                        headers = getattr(r, "headers", None)
                        body = getattr(r, "text", None)
                    except Exception:
                        status = headers = body = None
                    log_output(f"[HOOK][curl_cffi][RESP]{tag} status={status} headers={headers} body={safe_repr(body)}")
                    return r
                except Exception as e:
                    log_output(f"[HOOK][curl_cffi][ERROR] {e}\n{traceback.format_exc()}")
                    return _old_curl_request(self, method, url, *a, **k)

            curl_requests.Session.request = _hook_curl_request
            log_output("[bugcodebyctevclencoder] curl_cffi.requests hook installed")
        except Exception:
            log_output("[bugcodebyctevclencoder] failed to install curl_cffi hook\n" + traceback.format_exc())

    # --- PHẦN 5: HELPER FUNCTION ---
    def hook_class_methods(cls):
        try:
            for name, method in inspect.getmembers(cls, inspect.isfunction):
                if getattr(method, "_is_chuyenhuong_wrapped", False):
                    continue
                @functools.wraps(method)
                def wrapper(*args, __method=method, __name=name, **kwargs):
                    _local_ctx.in_chuyenhuong = True
                    try:
                        return __method(*args, **kwargs)
                    finally:
                        _local_ctx.in_chuyenhuong = False
                wrapper._is_chuyenhuong_wrapped = True
                setattr(cls, name, wrapper)
            return cls
        except Exception:
            log_output("[bugcodebyctevclencoder] hook_class_methods failed\n" + traceback.format_exc())
            return cls

    try:
        log_output(">> BUG CODE BY CTEVCL ENCODER INSTALLED <<")
    except Exception:
        pass


# --- PHẦN 6: CHẠY TOOL KHÁC (QUAN TRỌNG NHẤT) ---
if __name__ == "__main__":
    # Logic: Nếu file này được chạy trực tiếp, nó sẽ kiểm tra xem người dùng
    # có truyền vào tên file nào khác không để chạy tiếp.
    
    if len(sys.argv) > 1:
        # Lấy tên file script đích (ví dụ: tool_fb.py)
        target_script = sys.argv[1]
        
        # Xóa tên file bugcode... khỏi danh sách tham số để tool đích không bị nhầm
        # sys.argv lúc này sẽ bắt đầu từ tool đích
        sys.argv = sys.argv[1:]
        
        print(f"\n[*] CTEVCL ENCODER: Đang khởi chạy target -> {target_script}")
        print("=" * 60)
        
        try:
            # Lấy đường dẫn tuyệt đối để tránh lỗi
            script_path = os.path.abspath(target_script)
            script_dir = os.path.dirname(script_path)
            
            # Thêm thư mục của script đích vào sys.path để nó import được các module của nó
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)
            
            # CHẠY SCRIPT ĐÍCH TRONG CÙNG PROCESS ĐỂ ĂN HOOK
            runpy.run_path(script_path, run_name="__main__")
            
        except FileNotFoundError:
            print(f"[!] Lỗi: Không tìm thấy file '{target_script}'")
        except Exception as e:
            print(f"[!] Tool đích bị crash hoặc lỗi: {e}")
            # traceback.print_exc() # Bật dòng này nếu muốn xem lỗi chi tiết của tool đích
    else:
        # Nếu không có tham số
        print(">> Hook đã được cài đặt vào môi trường.")
        print(">> Để hook một tool khác, hãy chạy lệnh:")
        print(f"   python3 {sys.argv[0]} <tên_tool_của_bạn.py>")
