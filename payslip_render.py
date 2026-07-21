"""
급여명세서 공통 렌더링 모듈
====================================
- app_push.py (관리자 전용/로컬 실행)와 payslip_portal.py (435명용 공개 포털)가
  "동일한" 명세서 HTML을 만들기 위해 공유하는 모듈입니다.
- 이 파일 하나만 두 프로젝트 폴더에 그대로 복사해서 씁니다.
  (내용이 서로 달라지면 관리자용/포털용 명세서 모양이 어긋나니, 수정 시 양쪽 다 같이 교체하세요.)

원본 로직: app_push.py 내부의 _build_payslip_full_html() 함수를 그대로 옮긴 것이며,
날짜 계산(_ps_pay_period)만 외부에서 pay_year/pay_month로 주입받도록 바꿨습니다.
(포털에서 "보는 시점"이 아니라 "스냅샷을 만든 시점" 기준 급여월을 보여줘야 하기 때문입니다.)
"""


def build_payslip_card_html(member_key: str, data: dict, pay_year: int, pay_month: int) -> str:
    """명세서 카드(HTML 조각)를 만든다. member_key는 '이름+생년월일6자리' 형식(예: 홍길동641107)."""
    total_pay = (
        data["기본급"] + data["주휴수당"]
        + (data["국비_할증"] + data["도비_할증"] + data["시비_할증"])
        + data["gasan_raw"] + data["교통비"] + data["공휴일수당"]
    )
    total_deduct = (
        data["국민연금"] + data["건강보험"] + data["요양보험"]
        + data["고용보험"] + data["소득세"] + data["지방소득세"]
    )
    _m_field = data["국비_실지급액"] + data["도비_실지급액"] + data["시비_실지급액"]
    net_pay = _m_field + data["공휴일수당"]
    _guk_net = data["국비_실지급액"]
    _do_net = data["도비_실지급액"]
    _si_net = data["시비_실지급액"]

    payslip_card_html = f"""
    <div style="background-color:#ffffff; padding:25px; border:2px solid #dee2e6; border-radius:6px; color:#212529; font-family:'Malgun Gothic';">
        <h3 style="text-align:center; margin-bottom:5px;">{pay_year}년 {pay_month}월 급여 명세서</h3>
        <p style="text-align:center; font-size:12px; color:#868e96; margin-bottom:20px;">(사)창원시장애인부모회</p>
        <table style="width:100%; border-collapse:collapse; margin-bottom:15px; font-size:13px;">
            <tr style="background-color:#f8f9fa;">
                <th style="border:1px solid #dee2e6; padding:6px; width:15%;">성 명</th>
                <td style="border:1px solid #dee2e6; padding:6px; width:35%; text-align:center; font-weight:bold;">{member_key[:-6]}</td>
                <th style="border:1px solid #dee2e6; padding:6px; width:15%;">입사일자</th>
                <td style="border:1px solid #dee2e6; padding:6px; width:35%; text-align:center;">{data["입사일"]}</td>
            </tr>
            <tr style="background-color:#f8f9fa;">
                <th style="border:1px solid #dee2e6; padding:6px;">생년월일</th>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:center;">{member_key[-6:]}</td>
                <th style="border:1px solid #dee2e6; padding:6px;">총 근로시간</th>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:center; font-size:12px;">{data["국비시간"]+data["도비시간"]+data["시비시간"]+data["국비할증시간"]+data["도비할증시간"]+data["시비할증시간"]:.1f}H (국:{data["국비시간"]+data["국비할증시간"]:.1f}/도:{data["도비시간"]+data["도비할증시간"]:.1f}/시:{data["시비시간"]+data["시비할증시간"]:.1f})</td>
            </tr>
        </table>
        <div style="display:flex; gap:15px;">
            <div style="flex:1;">
                <div style="background-color:#e3faf2; padding:5px; text-align:center; font-weight:bold; border:1px solid #c3fae8; color:#0ca678; font-size:13px;">■ 지 급 내 역</div>
                <table style="width:100%; border-collapse:collapse; font-size:12px;">
                    <tr><th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">① 기본급 (재원통합)</th><td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["기본급"]:,} 원</td></tr>
                    <tr><th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">② 주휴수당</th><td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["주휴수당"]:,} 원</td></tr>
                    <tr><th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">③ 할증(가산근로)</th><td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["국비_할증"]+data["도비_할증"]+data["시비_할증"]:,} 원</td></tr>
                    <tr><th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">④ 가산수당</th><td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["gasan_raw"]:,} 원</td></tr>
                    <tr><th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">⑤ 교통비 (국비+도비)</th><td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["교통비"]:,} 원</td></tr>
                    <tr><th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">⑥ 법정공휴일 수당</th><td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["공휴일수당"]:,} 원</td></tr>
                    <tr style="background-color:#f1f3f5; font-weight:bold;"><td style="border:1px solid #dee2e6; padding:7px;">지급액 계</td><td style="border:1px solid #dee2e6; padding:7px; text-align:right;">{total_pay:,} 원</td></tr>
                </table>
            </div>
            <div style="flex:1;">
                <div style="background-color:#fff5f5; padding:5px; text-align:center; font-weight:bold; border:1px solid #ffe3e3; color:#e03131; font-size:13px;">■ 공 제 내 역</div>
                <table style="width:100%; border-collapse:collapse; font-size:12px;">
                    <tr><th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">국민연금</th><td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["국민연금"]:,} 원</td></tr>
                    <tr><th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">건강보험</th><td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["건강보험"]:,} 원</td></tr>
                    <tr><th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">장기요양보험</th><td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["요양보험"]:,} 원</td></tr>
                    <tr><th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">고용보험</th><td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["고용보험"]:,} 원</td></tr>
                    <tr><th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">소득세 (원천세)</th><td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["소득세"]:,} 원</td></tr>
                    <tr><th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">지방소득세</th><td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["지방소득세"]:,} 원</td></tr>
                    <tr style="background-color:#f1f3f5; font-weight:bold;"><td style="border:1px solid #dee2e6; padding:7px;">공제액 계</td><td style="border:1px solid #dee2e6; padding:7px; text-align:right; color:#e03131;">{total_deduct:,} 원</td></tr>
                </table>
            </div>
        </div>
        <div style="margin-top:15px; background-color:#e8f5e9; padding:10px; border-radius:4px; display:flex; justify-content:space-between; align-items:center; font-weight:bold; font-size:14px; border:1px solid #c8e6c9;">
            <span>💰 차인 지급액 (실수령액)</span>
            <span style="font-size:16px; color:#2e7d32;">{net_pay:,} 원</span>
        </div>
        <div style="margin-top:20px; background-color:#f1f3f5; padding:5px; text-align:center; font-weight:bold; font-size:13px;">■ 재원별 세부 내역 (국비 / 도비 / 시비)</div>
        <table style="width:100%; border-collapse:collapse; font-size:12px; margin-top:5px; table-layout:fixed;">
            <colgroup>
                <col style="width:22%;"><col style="width:19.5%;"><col style="width:19.5%;"><col style="width:19.5%;"><col style="width:19.5%;">
            </colgroup>
            <tr style="background-color:#f8f9fa;">
                <th style="border:1px solid #dee2e6; padding:6px;">구분</th>
                <th style="border:1px solid #dee2e6; padding:6px;">국비</th>
                <th style="border:1px solid #dee2e6; padding:6px;">도비</th>
                <th style="border:1px solid #dee2e6; padding:6px;">시비</th>
                <th style="border:1px solid #dee2e6; padding:6px;">합계</th>
            </tr>
            <tr>
                <th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">기본급(연차 미포함)</th>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["국비_기본급"]:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["도비_기본급"]:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["시비_기본급"]:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right; font-weight:bold;">{data["국비_기본급"]+data["도비_기본급"]+data["시비_기본급"]:,}</td>
            </tr>
            <tr>
                <th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">주휴수당</th>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["국비_주휴수당"]:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["도비_주휴수당"]:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["시비_주휴수당"]:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right; font-weight:bold;">{data["국비_주휴수당"]+data["도비_주휴수당"]+data["시비_주휴수당"]:,}</td>
            </tr>
            <tr>
                <th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">휴일·심야근로</th>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["국비_할증"]:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["도비_할증"]:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["시비_할증"]:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right; font-weight:bold;">{data["국비_할증"]+data["도비_할증"]+data["시비_할증"]:,}</td>
            </tr>
            <tr>
                <th style="border:1px solid #dee2e6; padding:6px; text-align:left; background-color:#f8f9fa;">연차수당</th>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["국비_연차수당"]:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["도비_연차수당"]:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right;">{data["시비_연차수당"]:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right; font-weight:bold;">{data["국비_연차수당"]+data["도비_연차수당"]+data["시비_연차수당"]:,}</td>
            </tr>
            <tr style="background-color:#f1f3f5;">
                <th style="border:1px solid #dee2e6; padding:6px; text-align:left;">실지급액</th>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right; font-weight:bold;">{_guk_net:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right; font-weight:bold;">{_do_net:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right; font-weight:bold;">{_si_net:,}</td>
                <td style="border:1px solid #dee2e6; padding:6px; text-align:right; font-weight:bold;">{_guk_net+_do_net+_si_net:,}</td>
            </tr>
        </table>
        <div style="margin-top:15px; background-color:#f1f3f5; padding:5px; display:flex; justify-content:space-between; font-size:12px;">
            <span style="font-weight:bold;">퇴직적립금</span>
            <span>{data["퇴직적립금"]:,} 원</span>
        </div>
        <div style="margin-top:20px; background-color:#f1f3f5; padding:5px; text-align:center; font-weight:bold; font-size:13px;">■ 산 출 근 거</div>
        <table style="width:100%; border-collapse:collapse; font-size:11px; margin-top:5px;">
            <tr><th style="border:1px solid #dee2e6; padding:5px; text-align:left; background-color:#f8f9fa; width:18%;">① 기본급</th><td style="border:1px solid #dee2e6; padding:5px;"><i>(근로시간(기본) × 기본임금) + (근로시간(할증) × 할증임금) + (총 근로시간 × 연차수당 단가)</i></td></tr>
            <tr><th style="border:1px solid #dee2e6; padding:5px; text-align:left; background-color:#f8f9fa;">② 주휴수당</th><td style="border:1px solid #dee2e6; padding:5px;"><i>근로시간(기본) × 주휴수당 단가</i></td></tr>
            <tr><th style="border:1px solid #dee2e6; padding:5px; text-align:left; background-color:#f8f9fa;">③ 할증(가산근로)</th><td style="border:1px solid #dee2e6; padding:5px;"><i>근로시간(할증) × 시간당 할증임금 (야간/연장 등 가산근로 해당분)</i></td></tr>
            <tr><th style="border:1px solid #dee2e6; padding:5px; text-align:left; background-color:#f8f9fa;">④ 가산수당</th><td style="border:1px solid #dee2e6; padding:5px;"><i>(근로시간(기본) × 3,300원 + 근로시간(할증) × 4,950원) × 75%</i></td></tr>
            <tr><th style="border:1px solid #dee2e6; padding:5px; text-align:left; background-color:#f8f9fa;">⑤ 교통비</th><td style="border:1px solid #dee2e6; padding:5px;"><i>제공기관 거리 10km 미만: 1회 6,000원 / 10km 이상: 1회 9,000원</i></td></tr>
            <tr><th style="border:1px solid #dee2e6; padding:5px; text-align:left; background-color:#f8f9fa;">⑥ 법정공휴일 수당</th><td style="border:1px solid #dee2e6; padding:5px;"><i>(기본급 시급 × 공휴일 근로시간 × 1.5) + (기본급 × 일일 소정근로시간) − 휴일 산정임금</i></td></tr>
        </table>
    </div>
    """
    return payslip_card_html


def build_payslip_full_html(member_key: str, data: dict, pay_year: int, pay_month: int):
    """(카드 HTML, 다운로드용 완전한 HTML 문서) 튜플을 반환한다."""
    payslip_card_html = build_payslip_card_html(member_key, data, pay_year, pay_month)

    payslip_full_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{member_key[:-6]}_급여명세서</title>
<style>
    @page {{ size: A4; margin: 12mm; }}
    body {{ margin: 0; padding: 16px; background:#f1f3f5; font-family:'Malgun Gothic', sans-serif; }}
    @media print {{
        body {{ background:#ffffff; padding:0; }}
        .print-wrap {{ box-shadow:none !important; }}
    }}
    .print-wrap {{ max-width: 800px; margin: 0 auto; }}
</style>
</head>
<body>
<div class="print-wrap">
{payslip_card_html}
</div>
</body>
</html>"""
    return payslip_card_html, payslip_full_html
