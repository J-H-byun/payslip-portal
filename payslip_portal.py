"""
급여명세서 조회 포털 (435명용, 공개 배포)
====================================
- app_push.py(관리자 전용/로컬 실행)와 완전히 분리된 별도 앱입니다.
- 이 앱은 원본 급여 취합 구글시트에는 전혀 접근하지 않습니다.
  app_push.py가 "🚀 435명 공개 포털용 스냅샷 게시" 버튼으로 게시한
  배포 전용 시트(GSHEET_URL_PAYSLIP_SNAPSHOT)만 읽습니다.
- 읽기 전용: 이 앱에서는 어떤 데이터도 수정/삭제하지 않습니다.

인증: 이름 + 생년월일 6자리
세션: 브라우저 세션 동안만 유지 (별도 쿠키/로컬스토리지 저장 없음 -> 브라우저를 완전히 닫으면 재로그인 필요)
잠금: 이름+생년월일 조합 기준 5회 실패 시 10분 잠금
"""

import json
import time
import datetime

import streamlit as st
import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials

from payslip_render import build_payslip_full_html

# =================================================================
# ⚙️ 설정
# =================================================================
# app_push.py의 GSHEET_URL_PAYSLIP_SNAPSHOT과 반드시 동일한 시트 URL이어야 합니다.
SNAPSHOT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Ah8xGXJEBpezYGZMp3k1MjKG1bCXZdLVuzewpMDZAlo/edit?gid=0#gid=0"

MAX_FAIL = 5          # 이 횟수만큼 실패하면 잠금
LOCK_MINUTES = 10      # 잠금 유지 시간(분)
SNAPSHOT_CACHE_TTL = 300  # 스냅샷 데이터를 구글시트에서 다시 읽어오는 주기(초)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

st.set_page_config(page_title="급여명세서 조회", page_icon="📄", layout="centered")


# =================================================================
# 📡 구글시트 연결 및 스냅샷 로딩
# =================================================================
@st.cache_resource(show_spinner=False)
def _get_gspread_client():
    """Streamlit Cloud 배포 시 st.secrets['gcp_service_account']에
    서비스 계정 JSON 키를 넣어두어야 합니다. (README.md 참고)
    이 서비스 계정은 배포 전용 시트에만 '뷰어' 권한을 부여하는 것을 강력히 권장합니다."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_data(ttl=SNAPSHOT_CACHE_TTL, show_spinner=False)
def load_snapshot():
    """배포 시트에서 (member_key -> payroll dict) / 급여월 / 갱신시각을 읽어온다.
    대소문자 구분 없이 찾을 수 있도록 정규화 인덱스(norm_index)도 함께 만든다.
    (영문 이름이 섞여 있을 때 'LISHUNHUA' / 'lishunhua' / 'Lishunhua'를 모두 같은 사람으로 인식하기 위함)"""
    gc = _get_gspread_client()
    sh = gc.open_by_url(SNAPSHOT_SHEET_URL)

    ws_snap = sh.worksheet("스냅샷")
    rows = ws_snap.get_all_values()[1:]  # 헤더 행 제외
    data = {}
    norm_index = {}  # 정규화(공백 제거 + 대문자)된 키 -> 원본 키
    for row in rows:
        if len(row) < 2 or not row[0].strip():
            continue
        try:
            original_key = row[0].strip()
            data[original_key] = json.loads(row[1])
            norm_index["".join(original_key.split()).upper()] = original_key
        except (json.JSONDecodeError, IndexError):
            continue

    ws_meta = sh.worksheet("메타")
    meta_rows = ws_meta.get_all_values()
    if len(meta_rows) < 2:
        raise RuntimeError("메타 정보가 없습니다. 관리자에게 스냅샷 재게시를 요청하세요.")
    meta = meta_rows[1]
    pay_year = int(meta[0])
    pay_month = int(meta[1])
    updated_at = meta[2] if len(meta) > 2 else "-"
    return data, norm_index, pay_year, pay_month, updated_at


# =================================================================
# 🔒 로그인 실패 잠금 (앱 프로세스 메모리에 공유 저장, 이름+생년월일 조합 기준)
# =================================================================
@st.cache_resource
def _login_attempt_store():
    return {}


def _check_lock(login_key: str):
    store = _login_attempt_store()
    rec = store.get(login_key)
    if rec and rec.get("locked_until") and time.time() < rec["locked_until"]:
        return True, int(rec["locked_until"] - time.time())
    return False, 0


def _register_fail(login_key: str):
    store = _login_attempt_store()
    rec = store.setdefault(login_key, {"fails": 0, "locked_until": None})
    rec["fails"] += 1
    if rec["fails"] >= MAX_FAIL:
        rec["locked_until"] = time.time() + LOCK_MINUTES * 60
        rec["fails"] = 0


def _register_success(login_key: str):
    store = _login_attempt_store()
    store[login_key] = {"fails": 0, "locked_until": None}


def render_image_download_button(card_html: str, filename: str):
    """명세서 카드를 PNG 이미지로 변환해서 다운로드하는 버튼을 그린다.
    브라우저 자체 기능(html2canvas)으로 변환하므로 서버 쪽에 별도 프로그램 설치가 필요 없다.
    (모바일에서 다운로드하면 보통 '다운로드' 폴더나 갤러리 앱에서 바로 확인 가능)"""
    safe_filename = json.dumps(filename)  # JS 문자열 리터럴로 안전하게 넣기 위해 이스케이프
    component_html = f"""
    <div style="text-align:center;">
        <button id="save-img-btn" style="
            width:100%; padding:12px; font-size:15px; font-weight:600;
            background-color:#0ca678; color:white; border:none; border-radius:6px;
            cursor:pointer;">
            🖼️ 이미지로 저장 (PNG, 갤러리에 바로 보관 가능)
        </button>
        <div id="save-img-status" style="margin-top:8px; font-size:12px; color:#868e96;"></div>
    </div>
    <div id="capture-wrapper" style="position:absolute; left:-9999px; top:-9999px;">
        {card_html}
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <script>
        document.getElementById('save-img-btn').addEventListener('click', function() {{
            var statusEl = document.getElementById('save-img-status');
            statusEl.innerText = '이미지 생성 중...';
            html2canvas(document.getElementById('capture-wrapper'), {{
                scale: 2,
                backgroundColor: '#ffffff'
            }}).then(function(canvas) {{
                var link = document.createElement('a');
                link.download = {safe_filename};
                link.href = canvas.toDataURL('image/png');
                link.click();
                statusEl.innerText = '다운로드 완료! (갤러리/다운로드 폴더 확인)';
            }}).catch(function(err) {{
                statusEl.innerText = '이미지 생성 실패: ' + err;
            }});
        }});
    </script>
    """
    components.html(component_html, height=110)


# =================================================================
# 🖥️ 화면
# =================================================================
if "authed_member" not in st.session_state:
    st.session_state["authed_member"] = None

st.title("📄 급여명세서 조회")

if not SNAPSHOT_SHEET_URL or SNAPSHOT_SHEET_URL.startswith("여기에"):
    st.error("이 포털이 아직 설정되지 않았습니다. 관리자에게 문의해주세요.")
    st.stop()

# ---------- 로그인 전 ----------
if st.session_state["authed_member"] is None:
    st.markdown("이름과 생년월일 6자리(예: 641107)를 입력해주세요.")

    with st.form("login_form"):
        name_input = st.text_input("이름")
        birth_input = st.text_input("생년월일 6자리", max_chars=6, placeholder="예: 641107")
        submitted = st.form_submit_button("조회하기", use_container_width=True)

    if submitted:
        name_clean = name_input.strip()
        birth_clean = "".join(ch for ch in birth_input.strip() if ch.isdigit())

        if not name_clean or len(birth_clean) != 6:
            st.error("이름과 생년월일 6자리를 정확히 입력해주세요.")
        else:
            # 대소문자·공백 차이를 무시하고 비교하기 위해 정규화(공백 제거 + 대문자)한 키로 처리
            login_key_norm = "".join(f"{name_clean}{birth_clean}".split()).upper()
            locked, remain_sec = _check_lock(login_key_norm)

            if locked:
                mm, ss = divmod(remain_sec, 60)
                st.error(f"🔒 5회 연속 조회 실패로 잠겼습니다. {mm}분 {ss}초 후 다시 시도해주세요.")
            else:
                try:
                    data, norm_index, pay_year, pay_month, updated_at = load_snapshot()
                except Exception as e:
                    st.error("데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
                    st.caption(f"(관리자 확인용: {e})")
                    st.stop()

                original_key = norm_index.get(login_key_norm)
                if original_key is not None:
                    _register_success(login_key_norm)
                    st.session_state["authed_member"] = original_key
                    st.rerun()
                else:
                    _register_fail(login_key_norm)
                    st.error("입력하신 정보와 일치하는 급여명세서를 찾을 수 없습니다. 이름과 생년월일을 다시 확인해주세요.")

    st.caption("⚠️ 5회 연속 실패 시 10분간 조회가 제한됩니다. 다른 사람의 정보로 조회를 시도하지 마세요.")

# ---------- 로그인 후 ----------
else:
    member_key = st.session_state["authed_member"]

    try:
        data, norm_index, pay_year, pay_month, updated_at = load_snapshot()
    except Exception as e:
        st.error("데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
        st.caption(f"(관리자 확인용: {e})")
        st.stop()

    if member_key not in data:
        st.warning("데이터가 갱신되어 더 이상 조회할 수 없습니다. 다시 로그인해주세요.")
        st.session_state["authed_member"] = None
        if st.button("다시 로그인하기"):
            st.rerun()
        st.stop()

    col1, col2 = st.columns([4, 1])
    with col1:
        st.caption(f"데이터 기준 시각: {updated_at}")
    with col2:
        if st.button("🔓 로그아웃", use_container_width=True):
            st.session_state["authed_member"] = None
            st.rerun()

    card_html, full_html = build_payslip_full_html(member_key, data[member_key], pay_year, pay_month)
    st.markdown(card_html, unsafe_allow_html=True)

    st.download_button(
        "📥 이 명세서 다운로드 (HTML, 브라우저에서 열어 'Ctrl+P'로 PDF 저장 가능)",
        data=full_html.encode("utf-8"),
        file_name=f"{member_key[:-6]}_급여명세서_{pay_year}{pay_month:02d}.html",
        mime="text/html",
        use_container_width=True,
    )

    render_image_download_button(
        card_html,
        f"{member_key[:-6]}_급여명세서_{pay_year}{pay_month:02d}.png",
    )

    st.caption(f"조회 시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
