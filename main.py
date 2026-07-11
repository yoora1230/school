from pathlib import Path

main_py = r'''import math
from datetime import date, timedelta

import pandas as pd
import streamlit as st


# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(
    page_title="방배중 시험 플래너",
    page_icon="📚",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #666;
        margin-bottom: 1.4rem;
    }
    .notice-box {
        padding: 1rem;
        border-radius: 12px;
        background: rgba(120, 120, 120, 0.08);
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]
DEFAULT_SUBJECTS = ["국어", "영어", "수학", "과학", "사회", "역사", "도덕", "기술·가정", "정보"]


def get_day_name(target_date: date) -> str:
    return DAY_NAMES[target_date.weekday()]


def split_topics(raw_text: str) -> list[str]:
    """쉼표 또는 줄바꿈으로 입력된 시험 범위를 목록으로 바꾼다."""
    text = raw_text.replace(",", "\n")
    return [item.strip() for item in text.splitlines() if item.strip()]


def build_task_templates(topics: list[str]) -> list[str]:
    """입력된 시험 범위를 공부 단계별 과제로 확장한다."""
    if not topics:
        return [
            "핵심 개념 정리",
            "교과서·학습지 복습",
            "기본 문제 풀이",
            "틀린 문제 다시 풀기",
            "시험 직전 최종 점검",
        ]

    tasks = []
    for topic in topics:
        tasks.extend(
            [
                f"{topic} 개념 정리",
                f"{topic} 문제 풀이",
                f"{topic} 오답 확인",
            ]
        )
    tasks.append("전체 범위 최종 점검")
    return tasks


def weighted_subject_order(subject_settings: dict) -> list[str]:
    """
    중요도가 높고 자신감이 낮은 과목이 더 자주 나오도록
    과목 목록을 가중치만큼 반복해 만든다.
    """
    order = []
    for subject, setting in subject_settings.items():
        importance = setting["importance"]
        confidence = setting["confidence"]
        weight = max(1, importance + (6 - confidence))
        order.extend([subject] * weight)
    return order


def create_plan(
    start_date: date,
    exam_date: date,
    study_days: list[str],
    weekday_minutes: int,
    weekend_minutes: int,
    session_minutes: int,
    subject_settings: dict,
) -> pd.DataFrame:
    available_dates = []
    current = start_date

    while current < exam_date:
        if get_day_name(current) in study_days:
            available_dates.append(current)
        current += timedelta(days=1)

    if not available_dates:
        return pd.DataFrame()

    subject_order = weighted_subject_order(subject_settings)
    subject_task_index = {subject: 0 for subject in subject_settings}
    subject_templates = {
        subject: build_task_templates(setting["topics"])
        for subject, setting in subject_settings.items()
    }

    rows = []
    order_index = 0

    for study_date in available_dates:
        daily_minutes = weekend_minutes if study_date.weekday() >= 5 else weekday_minutes
        session_count = max(1, math.ceil(daily_minutes / session_minutes))
        minutes_left = daily_minutes

        for session_number in range(1, session_count + 1):
            subject = subject_order[order_index % len(subject_order)]
            order_index += 1

            templates = subject_templates[subject]
            task_index = subject_task_index[subject]
            task = templates[task_index % len(templates)]
            subject_task_index[subject] += 1

            minutes = min(session_minutes, minutes_left)
            minutes_left -= minutes

            rows.append(
                {
                    "완료": False,
                    "날짜": study_date,
                    "요일": get_day_name(study_date),
                    "과목": subject,
                    "공부 내용": task,
                    "공부 시간(분)": minutes,
                }
            )

    # 시험 전 마지막 공부일은 최종 점검 중심으로 수정
    last_date = max(row["날짜"] for row in rows)
    for row in rows:
        if row["날짜"] == last_date:
            row["공부 내용"] = f"{row['과목']} 시험 직전 최종 점검"

    return pd.DataFrame(rows)


# -----------------------------
# 화면 상단
# -----------------------------
st.markdown('<div class="main-title">📚 방배중 시험 플래너</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">시험일까지 남은 시간을 계산해 과목별 공부 계획을 자동으로 만들어 줍니다.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("⚙️ 계획 설정")

    exam_name = st.text_input("시험 이름", value="중간고사")
    today = date.today()

    start_date = st.date_input(
        "공부 시작일",
        value=today,
        min_value=today,
    )
    exam_date = st.date_input(
        "시험 시작일",
        value=today + timedelta(days=14),
        min_value=today + timedelta(days=1),
    )

    subjects = st.multiselect(
        "시험 과목",
        DEFAULT_SUBJECTS,
        default=["국어", "영어", "수학", "과학", "사회"],
    )

    study_days = st.multiselect(
        "공부 가능한 요일",
        DAY_NAMES,
        default=DAY_NAMES,
    )

    weekday_minutes = st.slider(
        "평일 공부 가능 시간",
        min_value=30,
        max_value=300,
        value=120,
        step=10,
        format="%d분",
    )
    weekend_minutes = st.slider(
        "주말 공부 가능 시간",
        min_value=30,
        max_value=480,
        value=180,
        step=10,
        format="%d분",
    )
    session_minutes = st.select_slider(
        "한 번 공부할 시간",
        options=[20, 30, 40, 50, 60],
        value=40,
        format_func=lambda value: f"{value}분",
    )

days_left = (exam_date - today).days
col1, col2, col3 = st.columns(3)
col1.metric("시험", exam_name)
col2.metric("시험까지", f"D-{max(days_left, 0)}")
col3.metric("선택 과목", f"{len(subjects)}개")

st.divider()

# -----------------------------
# 과목별 설정
# -----------------------------
st.subheader("1. 과목별 우선순위와 시험 범위 입력")

if not subjects:
    st.warning("사이드바에서 시험 과목을 한 개 이상 선택해 주세요.")
else:
    subject_settings = {}

    for subject in subjects:
        with st.expander(f"📘 {subject}", expanded=False):
            c1, c2 = st.columns(2)
            importance = c1.slider(
                "중요도",
                1,
                5,
                3,
                key=f"importance_{subject}",
                help="높을수록 계획표에 더 자주 배치됩니다.",
            )
            confidence = c2.slider(
                "현재 자신감",
                1,
                5,
                3,
                key=f"confidence_{subject}",
                help="낮을수록 계획표에 더 자주 배치됩니다.",
            )
            raw_topics = st.text_area(
                "시험 범위",
                placeholder="예: 1단원 문학\n2단원 문법\n교과서 30~75쪽",
                key=f"topics_{subject}",
                height=100,
            )

            subject_settings[subject] = {
                "importance": importance,
                "confidence": confidence,
                "topics": split_topics(raw_topics),
            }

    generate = st.button(
        "✨ 시험 계획표 만들기",
        type="primary",
        use_container_width=True,
    )

    if generate:
        if start_date >= exam_date:
            st.error("공부 시작일은 시험 시작일보다 빨라야 합니다.")
        elif not study_days:
            st.error("공부 가능한 요일을 한 개 이상 선택해 주세요.")
        else:
            plan = create_plan(
                start_date=start_date,
                exam_date=exam_date,
                study_days=study_days,
                weekday_minutes=weekday_minutes,
                weekend_minutes=weekend_minutes,
                session_minutes=session_minutes,
                subject_settings=subject_settings,
            )

            if plan.empty:
                st.error("선택한 기간과 요일에 공부 가능한 날짜가 없습니다.")
            else:
                st.session_state["study_plan"] = plan
                st.success("시험 계획표를 만들었습니다!")

# -----------------------------
# 생성된 계획표
# -----------------------------
if "study_plan" in st.session_state:
    st.divider()
    st.subheader("2. 나의 시험 계획표")

    plan = st.session_state["study_plan"].copy()

    completed_count = int(plan["완료"].sum())
    total_count = len(plan)
    remaining_count = total_count - completed_count
    progress = completed_count / total_count if total_count else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("전체 공부", f"{total_count}개")
    m2.metric("완료", f"{completed_count}개")
    m3.metric("남은 공부", f"{remaining_count}개")
    st.progress(progress, text=f"전체 진행률 {progress * 100:.0f}%")

    today_tasks = plan[plan["날짜"] == today]
    if not today_tasks.empty:
        st.markdown("#### 🔥 오늘 할 공부")
        for _, row in today_tasks.iterrows():
            check = "✅" if row["완료"] else "⬜"
            st.write(
                f"{check} **{row['과목']}** · {row['공부 내용']} "
                f"({row['공부 시간(분)']}분)"
            )
    else:
        st.info("오늘은 계획된 공부가 없습니다. 다음 공부일의 계획을 확인해 보세요.")

    st.markdown("#### 📅 전체 계획")
    edited_plan = st.data_editor(
        plan,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "완료": st.column_config.CheckboxColumn("완료"),
            "날짜": st.column_config.DateColumn("날짜", format="YYYY-MM-DD"),
            "요일": st.column_config.TextColumn("요일", disabled=True),
            "과목": st.column_config.TextColumn("과목", disabled=True),
            "공부 내용": st.column_config.TextColumn("공부 내용"),
            "공부 시간(분)": st.column_config.NumberColumn(
                "공부 시간(분)",
                min_value=10,
                max_value=300,
                step=10,
            ),
        },
        key="plan_editor",
    )
    st.session_state["study_plan"] = edited_plan

    csv_data = edited_plan.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 계획표 CSV로 다운로드",
        data=csv_data,
        file_name=f"{exam_name}_시험계획표.csv",
        mime="text/csv",
        use_container_width=True,
    )

    if st.button("🗑️ 계획표 초기화", use_container_width=True):
        del st.session_state["study_plan"]
        st.rerun()

else:
    st.markdown(
        """
        <div class="notice-box">
        <b>사용 방법</b><br>
        ① 사이드바에서 시험일과 공부 시간을 설정합니다.<br>
        ② 과목별 중요도, 자신감, 시험 범위를 입력합니다.<br>
        ③ ‘시험 계획표 만들기’를 누릅니다.<br>
        ④ 공부를 끝낼 때마다 완료 칸을 체크합니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
'''

requirements_txt = """streamlit>=1.35.0
pandas>=2.0.0
"""

base = Path("/mnt/data/bangbae_exam_planner")
base.mkdir(parents=True, exist_ok=True)

(base / "main.py").write_text(main_py, encoding="utf-8")
(base / "requirements.txt").write_text(requirements_txt, encoding="utf-8")

# Also create a zip for convenience.
import zipfile
zip_path = Path("/mnt/data/bangbae_exam_planner.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(base / "main.py", arcname="main.py")
    zf.write(base / "requirements.txt", arcname="requirements.txt")

print(f"Created: {base / 'main.py'}")
print(f"Created: {base / 'requirements.txt'}")
print(f"Created: {zip_path}")
