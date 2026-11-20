"""Personalised advice, built from the student's own highest-risk factors (rule-based).
General wellbeing suggestions, not medical advice."""
import json

# feature -> (short title, what to do)
ADVICE = {
    "study_load": ("Manage your study load and balance",
        "Break big tasks into small steps, spread them across the week, use focused 25-minute study blocks, "
        "and protect at least one evening a week for yourself."),
    "academic_performance": ("Steady your focus and academic confidence",
        "Set one small, specific goal per study session, silence notifications while you work, and ask a "
        "lecturer or tutor for feedback on where to improve."),
    "basic_needs": ("Get support with money worries",
        "If money is getting in the way of your studies, ask your student affairs or welfare office about "
        "financial aid, hardship funds and budgeting help."),
    "future_career_concerns": ("Make career worries concrete",
        "Book a session with your university career service and write down one small next step, such as "
        "updating your CV or asking one person about their job."),
    "sleep_quality": ("Improve your sleep routine",
        "Keep a regular sleep and wake time, write tomorrow's to-do list before bed so it is off your mind, "
        "avoid screens for the last 30 minutes, and keep caffeine to the morning."),
    "social_support": ("Strengthen your support network",
        "Reach out to one friend or family member this week, or join a study group or student society to "
        "meet people. Talking about stress usually makes it lighter."),
    "anxiety_level": ("Calm tension in your body and mind",
        "Try box breathing or a 10-minute walk when you notice tension rising, and plan short breaks. If "
        "tension is constant, a counsellor can teach you more techniques."),
    "depression": ("Take small steps back towards what you enjoy",
        "Plan one small enjoyable or social activity this week and talk to someone you trust. If low mood or "
        "withdrawal lasts more than two weeks, please speak to a counsellor or doctor."),
}

INTRO = {
    "Low": "Your responses suggest a low level of stress right now. Keep up what is working for you.",
    "Moderate": "Your responses suggest a moderate level of stress. A few small changes in the areas below may help.",
    "High": ("Your responses suggest a high level of stress. Consider the steps below and talk to someone "
             "you trust or to your university counselling service."),
}

MINDFULNESS = [
    {"title": "Box Breathing", "mins": 4,
     "text": "Breathe in, hold, breathe out and hold again, each for a count of four. A few rounds can help you settle."},
    {"title": "Guided Body Scan", "mins": 10,
     "text": "Slowly move your attention from head to toe, noticing and softening any tense areas."},
    {"title": "Progressive Muscle Relaxation", "mins": 8,
     "text": "Tense and release muscle groups one at a time to ease tension built up during long study sessions."},
]

PHYSICAL = [
    {"title": "Short Walk", "mins": 15,
     "text": "A gentle walk outdoors breaks up long periods of sitting and can help clear your head."},
    {"title": "Gentle Stretching or Yoga", "mins": 20,
     "text": "Slow movement and stretching to release tension in the neck, shoulders and lower back."},
    {"title": "Campus Gym or Sport", "mins": 45,
     "text": "More vigorous exercise on most days may support better mood and sleep."},
]


def build_recommendation(level, ranked_factors):
    """Returns (advice_text, plan_json): a paragraph and a list of up to 3-4 plan items."""
    plan = []
    for factor in ranked_factors:
        if factor["risk"] < 0.5 or len(plan) >= 3:
            continue
        title, detail = ADVICE[factor["key"]]
        urgency = "Urgent" if factor["risk"] >= 0.8 else "Moderate" if factor["risk"] >= 0.65 else "Suggested"
        plan.append({"factor": factor["key"], "title": title, "detail": detail, "urgency": urgency})

    if not plan:
        plan.append({"factor": None, "title": "Keep up your healthy routine",
                     "detail": "None of your answers stood out as a major stressor. Keep your sleep, study and "
                               "social habits steady and check in again in a couple of weeks.",
                     "urgency": "Suggested"})
    if level == "High":
        plan.append({"factor": None, "title": "Talk to someone",
                     "detail": "Speaking with a friend, family member or your university counselling service can "
                               "make a high-stress period easier to manage.",
                     "urgency": "Urgent"})

    advice_text = INTRO[level] + " " + " ".join(f"{item['title']}: {item['detail']}" for item in plan)
    return advice_text, json.dumps(plan)


MOTIVATION = {
    "first": [
        ("Welcome aboard!", "You have completed your first assessment. Checking in with yourself is a healthy habit and a strong first step. Retake it in about two weeks to see how things change.", "bi-rocket-takeoff-fill"),
        ("Great start!", "That took a little courage and time, and you did it. Your result is a starting point, not a verdict. Follow one idea from your plan this week and check in again soon.", "bi-stars"),
    ],
    "improved": [
        ("Great progress!", "Your stress index went from {from_index} to {to_index} since your last check-in. Whatever you have been doing is working. Keep it up and be proud of yourself.", "bi-trophy-fill"),
        ("You are moving in the right direction!", "Your stress is lower than last time ({from_index} to {to_index}). Small steps add up. Notice what helped and keep doing more of it.", "bi-emoji-smile-fill"),
    ],
    "same": [
        ("Holding steady", "Your stress is about the same as last time ({to_index}). Staying steady is a win, especially when life is busy. Try one change from your plan this week to nudge it down.", "bi-bullseye"),
        ("Consistency counts", "Not much has changed since your last check-in ({to_index}). Pick one small habit from your plan, such as a regular bedtime or a short walk, and see how it feels.", "bi-compass"),
    ],
    "worse": [
        ("Tough stretch, and that is okay", "Your stress index went from {from_index} to {to_index} since your last check-in. Stress goes up and down, especially around exams and deadlines. Be kind to yourself, pick one small step from your plan, and reach out to someone you trust if you need to.", "bi-heart-fill"),
        ("You are not alone", "Things feel heavier than last time ({from_index} to {to_index}). That does not mean you are failing. Take it one day at a time, rest when you can, and consider talking to a friend or your university counselling service.", "bi-chat-heart-fill"),
    ],
}


def build_motivation(current, previous):
    """Compare this assessment with the one before it and pick an encouraging message.
    current / previous: Prediction objects (previous is None for a first assessment)."""
    if previous is None:
        kind, from_index = "first", None
    else:
        from_index = previous.stress_index
        change = current.stress_index - previous.stress_index
        if change <= -5:               # the index follows the student's own answers, so a 5-point move is
            kind = "improved"          # a real change and smaller moves count as "about the same"
        elif change >= 5:
            kind = "worse"
        else:
            kind = "same"
    options = MOTIVATION[kind]
    title, message, icon = options[current.prediction_id % len(options)]
    return {"kind": kind, "title": title, "icon": icon, "from_index": from_index, "to_index": current.stress_index,
            "message": message.format(from_index=from_index, to_index=current.stress_index)}


def needs_support_message(level, ranked_factors):
    """Show the support box when stress is High or the low-mood factor is strongly flagged."""
    return level == "High" or any(f["key"] == "depression" and f["risk"] >= 0.67 for f in ranked_factors)
