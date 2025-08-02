import streamlit as st
import pandas as pd
import altair as alt
import requests
from fpdf import FPDF
import tempfile
import os

# Title
st.title("📊 Quiz Performance Report Generator")

# Get Perplexity API Key
api_key = st.secrets.get("PERPLEXITY_API_KEY") or os.getenv("PERPLEXITY_API_KEY")

# Upload CSV
uploaded_file = st.file_uploader("Upload Quiz Results CSV", type=["csv"])

def get_ai_feedback(summary_text):
    prompt = [
        {"role": "system", "content": "You are a helpful AI tutor providing feedback on quiz performance."},
        {"role": "user", "content": f"Analyze the student's quiz performance and suggest strengths and weaknesses with nice charts and graphics. Input: {summary_text}"}
    ]

    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "sonar-medium-online",
                "messages": prompt,
                "max_tokens": 150,
                "temperature": 0.7
            }
        )
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        return f"Error generating feedback: {e}"

def generate_pdf(student, summary_text, strengths, weaknesses, ai_feedback):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, f"Quiz Performance Report for {student}\n\n{summary_text}\n\nStrengths:\n")
    for topic in strengths.index:
        pdf.cell(0, 10, f"- {topic}", ln=True)
    pdf.cell(0, 10, "\nWeaknesses:", ln=True)
    for topic in weaknesses.index:
        pdf.cell(0, 10, f"- {topic}", ln=True)
    pdf.cell(0, 10, "\nAI Feedback:", ln=True)
    pdf.multi_cell(0, 10, ai_feedback)
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp_file.name)
    return tmp_file.name

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    required_columns = {"Student", "Topic", "Question", "Correct", "Score"}
    if not required_columns.issubset(df.columns):
        st.error(f"CSV must contain columns: {required_columns}")
    else:
        student_list = df["Student"].unique().tolist()
        selected_student = st.selectbox("Select a student", student_list)

        student_df = df[df["Student"] == selected_student]

        total_questions = len(student_df)
        correct_answers = student_df["Correct"].sum()
        accuracy = (correct_answers / total_questions) * 100
        total_score = student_df["Score"].sum()

        st.subheader("📌 Summary")
        st.markdown(f"**Accuracy:** {accuracy:.2f}%")
        st.markdown(f"**Total Score:** {total_score}")

        topic_perf = student_df.groupby("Topic")["Correct"].agg(["count", "sum"])
        topic_perf["Accuracy"] = (topic_perf["sum"] / topic_perf["count"]) * 100

        strengths = topic_perf[topic_perf["Accuracy"] >= 70].sort_values("Accuracy", ascending=False)
        weaknesses = topic_perf[topic_perf["Accuracy"] < 70].sort_values("Accuracy")

        st.subheader("✅ Strengths")
        if not strengths.empty:
            st.dataframe(strengths[["Accuracy"]])
        else:
            st.markdown("No strong areas identified.")

        st.subheader("⚠️ Weaknesses")
        if not weaknesses.empty:
            st.dataframe(weaknesses[["Accuracy"]])
        else:
            st.markdown("No weak areas identified.")

        st.subheader("💡 Recommendations")
        for topic in weaknesses.index:
            st.markdown(f"- Practice more questions on **{topic}**.")

        summary_text = f"{selected_student} scored {total_score} with an accuracy of {accuracy:.2f}%. Strengths: {', '.join(strengths.index)}. Weaknesses: {', '.join(weaknesses.index)}."
        ai_feedback = get_ai_feedback(summary_text)

        st.subheader("🤖 AI Feedback")
        st.write(ai_feedback)

        st.subheader("📈 Topic-wise Accuracy")
        chart_data = topic_perf.reset_index()
        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X("Topic", sort='-y'),
            y="Accuracy",
            color=alt.condition(
                alt.datum.Accuracy >= 70,
                alt.value("green"),
                alt.value("red")
            )
        ).properties(height=300)

        st.altair_chart(chart, use_container_width=True)

        st.subheader("📄 Download Report as PDF")
        pdf_path = generate_pdf(selected_student, summary_text, strengths, weaknesses, ai_feedback)
        with open(pdf_path, "rb") as f:
            st.download_button("Download PDF Report", f, file_name=f"{selected_student}_report.pdf")
else:
    st.info("Upload a CSV to begin.")