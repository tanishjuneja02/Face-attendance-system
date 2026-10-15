"""Graphs for a student's attendance. Data prep is plain pandas (testable); drawing uses Altair,
which comes with Streamlit.

Three charts, each answering one question:
  donut     - how much of my time was I present vs absent?
  subjects  - which subjects am I below the minimum in?
  calendar  - which days did I miss?
"""
import pandas as pd

GREEN, RED, AMBER, GREY = "#22c55e", "#ef4444", "#f59e0b", "#94a3b8"


def subject_frame(df, minimum):
    """One row per subject: attended, held, percent, status ('ok' or 'low'). Lowest percent first."""
    out = df.groupby("subject")["present"].agg(attended="sum", held="count").reset_index()
    out["attended"] = out["attended"].astype(int)
    out["percent"] = (100 * out["attended"] / out["held"]).round(1)
    out["status"] = out["percent"].map(lambda p: "ok" if p >= minimum else "low")
    return out.sort_values(["percent", "subject"]).reset_index(drop=True)


def donut_frame(df):
    present = int(df["present"].sum())
    return pd.DataFrame({"status": ["Present", "Absent"], "classes": [present, len(df) - present]})


def calendar_frame(df):
    """One row per day: percent of that day's classes attended, plus week and weekday for the grid."""
    days = df.assign(date=pd.to_datetime(df["date"])).groupby("date")["present"].agg(
        attended="sum", held="count").reset_index()
    days["attended"] = days["attended"].astype(int)
    days["percent"] = (100 * days["attended"] / days["held"]).round(0)
    days["week"] = (days["date"] - pd.to_timedelta(days["date"].dt.weekday, unit="D"))
    days["week_label"] = days["week"].dt.strftime("%d %b")
    days["weekday"] = days["date"].dt.strftime("%a")
    days["label"] = days["date"].dt.strftime("%d %b %Y")
    return days


def donut_chart(df, overall):
    import altair as alt

    data = donut_frame(df)
    colours = alt.Scale(domain=["Present", "Absent"], range=[GREEN, RED])
    arcs = alt.Chart(data).mark_arc(innerRadius=62, outerRadius=100, stroke="white", strokeWidth=2).encode(
        theta=alt.Theta("classes:Q"),
        color=alt.Color("status:N", scale=colours, legend=alt.Legend(title=None, orient="bottom")),
        tooltip=["status:N", "classes:Q"],
    )
    centre = alt.Chart(pd.DataFrame({"t": [f"{overall}%"]})).mark_text(
        fontSize=30, fontWeight="bold").encode(text="t:N")
    return (arcs + centre).properties(height=260)


def subject_chart(df, minimum):
    import altair as alt

    data = subject_frame(df, minimum)
    colours = alt.Scale(domain=["ok", "low"], range=[GREEN, RED])
    bars = alt.Chart(data).mark_bar(cornerRadiusEnd=6, size=22).encode(
        y=alt.Y("subject:N", sort=alt.EncodingSortField("percent", order="ascending"), title=None),
        x=alt.X("percent:Q", scale=alt.Scale(domain=[0, 100]), title="Attendance %"),
        color=alt.Color("status:N", scale=colours, legend=None),
        tooltip=["subject:N", "attended:Q", "held:Q", "percent:Q"],
    )
    labels = alt.Chart(data).mark_text(align="left", dx=6, fontWeight="bold").encode(
        y=alt.Y("subject:N", sort=alt.EncodingSortField("percent", order="ascending")),
        x="percent:Q",
        text=alt.Text("percent:Q", format=".0f"),
    )
    line = alt.Chart(pd.DataFrame({"x": [minimum]})).mark_rule(
        strokeDash=[5, 4], color=AMBER, strokeWidth=2).encode(x="x:Q")
    return (bars + labels + line).properties(height=max(120, 46 * len(data)))


def calendar_chart(df):
    import altair as alt

    data = calendar_frame(df)
    return alt.Chart(data).mark_rect(cornerRadius=4, stroke="white", strokeWidth=2).encode(
        x=alt.X("week_label:O", title="Week starting",
                sort=list(data.sort_values("week")["week_label"].unique()), axis=alt.Axis(labelAngle=0)),
        y=alt.Y("weekday:N", sort=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], title=None),
        color=alt.Color(
            "percent:Q", title="Present %",
            scale=alt.Scale(domain=[0, 100], range=[RED, GREEN]),
        ),
        tooltip=["label:N", "attended:Q", "held:Q", "percent:Q"],
    ).properties(height=220)