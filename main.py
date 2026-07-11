from pathlib import Path
import zipfile

main_code = '''import math
from datetime import date, timedelta

import pandas as pd
import streamlit as st


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
    .guide-box {
        padding: 1rem;
        border-radius: 12px;
        background-color: rgba(120, 120, 120, 0.08);
        margin-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]
DEFAULT_SUBJECTS = [
    "국어",
    "영어",
    "수학",
    "과학",
    "사회",
    "역사",
    "도덕",
    "기술·가정",
    "정보",
]


def get_day_name(target_date):
    return DAY_NAMES[target_date.weekday()]


def split_topics(raw_text):
    text = raw_text.replace(",", "\\n")
    return [topic.strip() for topic in text.splitlines() if topic.strip()]


def make_tasks(topics):
    if not topics:
        return [
            "핵심 개념 정리",
            "교과서와 학습지 복습",
            "기본 문제 풀이",
            "틀린 문제 다시 풀기",
            "전체 범위 최종 점검",
        ]

    tasks = []

    for topic in topics:
        tasks.append(f"{topic} 개념 정리")
        tasks.append(f"{topic} 문제 풀이")
        tasks.append(f"{topic} 오답 확인")

    tasks.append("전체 범위 최종 점검")
    return tasks


def make_subject_order(subject_settings):
    order = []

    for subject, setting in subject_settings.items():
        importance = setting["importance"]
        confidence = setting["confidence"]

        weight = max(1, importance + (6 - confidence))
        order.extend([subject] * weight)

    return order


def create_study_plan(
    start_date,
    exam_date,
    study_days,
    weekday_minutes,
    weekend_minutes,
    session_minutes,
    subject_settings,
):
    available_dates = []
    current_date = start_date

    while current_date < exam_date:
        if get_day_name(current_date) in study_days:
            available_dates.append(current_date)

        current_date += timedelta(days=1)

    if not available_dates:
        return pd.DataFrame()

    subject_order = make_subject_order(subject_settings)
    subject_tasks = {
        subject: make_tasks(setting["topics"])
        for subject, setting in subject_settings.items()
    }
    task_indexes = {subject: 0 for subject in subject_settings}

    rows = []
    subject_index = 0

    for study_date in available_dates:
        if study_date.weekday() >= 5:
            daily_minutes = weekend_minutes
        else:
            daily_minutes = weekday_minutes

        session_count = max(1, math.ceil(daily_minutes / session_minutes))
        remaining_minutes = daily_minutes

        for _ in range(session_count):
            subject = subject_order[subject_index % len(subject_order)]
            subject_index += 1

            tasks = subject_tasks[subject]
            task_index = task_indexes[subject]
            task = tasks[task_index % len(tasks)]
            task_indexes[subject] += 1

            study_minutes = min(session_minutes, remaining_minutes)
            remaining_minutes -= study_minutes

            rows.append(
                {
                    "완료": False,
                    "날짜": study_date,
                    "요일": get_day_name(study_date),
                    "과목": subject,
                    "공부 내용": task,
                    "공부 시간(분)": study_minutes,
                }
            )

    last_study_date = max(row["날짜"] for row in rows)

    for row in rows:
        if row["날짜"] == last_study_date:
            row["공부 내용"] = f"{row['과목']} 시험 직전 최종 점검"

    return pd.DataFrame(rows)


st.markdown(
    '<div class="main-title">📚 방배중 시험 플래너</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="sub-title">시험일까지 남은 기간에 맞춰 공부 계획표를 자동으로 만들어 줍니다.</div>',
    unsafe_allow_html=True,
)

today = date.today()

with st.sidebar:
    st.header("⚙️ 계획 설정")

    exam_name = st.text_input("시험 이름", value="중간고사")

    start_date = st.date_input(
        "공부 시작일",
        value=today,
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
    )

    weekend_minutes = st.slider(
        "주말 공부 가능 시간",
        min_value=30,
        max_value=480,
        value=180,
        step=10,
    )

    session_minutes = st.select_slider(
        "한 번에 공부할 시간",
        options=[20, 30, 40, 50, 60],
        value=40,
        format_func=lambda value: f"{value}분",
    )

days_left = (exam_date - today).days

metric1, metric2, metric3 = st.columns(3)
metric1.metric("시험", exam_name)
metric2.metric("시험까지", f"D-{max(days_left, 0)}")
metric3.metric("선택 과목", f"{len(subjects)}개")

st.divider()
st.subheader("1. 과목별 시험 범위 입력")

if not subjects:
    st.warning("왼쪽 사이드바에서 시험 과목을 한 개 이상 선택해 주세요.")

else:
    subject_settings = {}

    for subject in subjects:
        with st.expander(f"📘 {subject} 설정"):
            column1, column2 = st.columns(2)

            importance = column1.slider(
                "중요도",
                min_value=1,
                max_value=5,
                value=3,
                key=f"importance_{subject}",
                help="높을수록 계획표에 더 자주 배치됩니다.",
            )

            confidence = column2.slider(
                "현재 자신감",
                min_value=1,
                max_value=5,
                value=3,
                key=f"confidence_{subject}",
                help="낮을수록 계획표에 더 자주 배치됩니다.",
            )

            raw_topics = st.text_area(
                "시험 범위",
                placeholder="예: 1단원 문학\\n2단원 문법\\n교과서 30~75쪽",
                key=f"topics_{subject}",
            )

            subject_settings[subject] = {
                "importance": importance,
                "confidence": confidence,
                "topics": split_topics(raw_topics),
            }

    if st.button(
        "✨ 시험 계획표 만들기",
        type="primary",
        use_container_width=True,
    ):
        if start_date >= exam_date:
            st.error("공부 시작일은 시험 시작일보다 빨라야 합니다.")

        elif not study_days:
            st.error("공부 가능한 요일을 한 개 이상 선택해 주세요.")

        else:
            plan = create_study_plan(
                start_date=start_date,
                exam_date=exam_date,
                study_days=study_days,
                weekday_minutes=weekday_minutes,
                weekend_minutes=weekend_minutes,
                session_minutes=session_minutes,
                subject_settings=subject_settings,
            )

            if plan.empty:
                st.error("선택한 기간 안에 공부 가능한 날짜가 없습니다.")

            else:
                st.session_state["study_plan"] = plan
                st.success("시험 계획표를 만들었습니다.")

if "study_plan" in st.session_state:
    st.divider()
    st.subheader("2. 나의 시험 계획표")

    plan = st.session_state["study_plan"].copy()

    completed_count = int(plan["완료"].sum())
    total_count = len(plan)
    remaining_count = total_count - completed_count
    progress = completed_count / total_count if total_count else 0

    result1, result2, result3 = st.columns(3)
    result1.metric("전체 공부", f"{total_count}개")
    result2.metric("완료", f"{completed_count}개")
    result3.metric("남은 공부", f"{remaining_count}개")

    st.progress(progress, text=f"전체 진행률 {progress * 100:.0f}%")

    today_tasks = plan[plan["날짜"] == today]

    if not today_tasks.empty:
        st.markdown("#### 🔥 오늘 할 공부")

        for _, row in today_tasks.iterrows():
            status = "✅" if row["완료"] else "⬜"
            st.write(
                f"{status} **{row['과목']}** · "
                f"{row['공부 내용']} ({row['공부 시간(분)']}분)"
            )

    else:
        st.info("오늘은 계획된 공부가 없습니다.")

    st.markdown("#### 📅 전체 계획")

    edited_plan = st.data_editor(
        plan,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "완료": st.column_config.CheckboxColumn("완료"),
            "날짜": st.column_config.DateColumn(
                "날짜",
                format="YYYY-MM-DD",
                disabled=True,
            ),
            "요일": st.column_config.TextColumn(
                "요일",
                disabled=True,
            ),
            "과목": st.column_config.TextColumn(
                "과목",
                disabled=True,
            ),
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
        <div class="guide-box">
        <b>사용 방법</b><br>
        ① 왼쪽에서 시험 날짜와 공부 시간을 설정합니다.<br>
        ② 과목별 중요도, 자신감, 시험 범위를 입력합니다.<br>
        ③ 시험 계획표 만들기 버튼을 누릅니다.<br>
        ④ 공부를 끝낼 때마다 완료 칸을 체크합니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
'''

requirements_code = '''streamlit>=1.35.0
pandas>=2.0.0
'''

output_dir = Path("/mnt/data/bangbae_exam_planner_clean")
output_dir.mkdir(parents=True, exist_ok=True)

main_path = output_dir / "main.py"
requirements_path = output_dir / "requirements.txt"
zip_path = Path("/mnt/data/bangbae_exam_planner_clean.zip")

main_path.write_text(main_code, encoding="utf-8")
requirements_path.write_text(requirements_code, encoding="utf-8")

with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
    zip_file.write(main_path, arcname="main.py")
    zip_file.write(requirements_path, arcname="requirements.txt")

print(main_path)
print(requirements_path)
print(zip_path)
