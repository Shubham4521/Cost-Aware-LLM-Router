import os, sys, time
import pandas as pd
import streamlit as st
from openai import OpenAI
from tavily import TavilyClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from router.rules import route

FREE_ID    = "openai/gpt-oss-120b"
CHEAP_ID   = "openai/gpt-5-mini"
PREMIUM_ID = "anthropic/claude-sonnet-5"

st.set_page_config(page_title="Cost-Aware LLM Router", page_icon="🔀", layout="wide")


def get_key(name):
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name, "")


@st.cache_resource
def clients():
    groq = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=get_key("GROQ_API_KEY"))
    openrouter = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=get_key("OPENROUTER_API_KEY"))
    tavily = TavilyClient(api_key=get_key("TAVILY_API_KEY"))
    return groq, openrouter, tavily


groq, openrouter, tavily = clients()
MODELS = {"free": (groq, FREE_ID), "cheap": (openrouter, CHEAP_ID), "premium": (openrouter, PREMIUM_ID)}


def search_context(q):
    res = tavily.search(q, max_results=5, topic="news", days=7)
    return "\n\n".join(f"{x['title']}\n{x['content']}" for x in res["results"])


def ask(prompt, tier, search):
    client, model = MODELS[tier]
    content = prompt
    if search:
        content = (f"Today's date is {time.strftime('%d %B %Y')}. Use these search results to answer."
                   f"\n\nSEARCH RESULTS:\n{search_context(prompt)}\n\nQUESTION: {prompt}")
    kwargs = dict(model=model, messages=[{"role": "user", "content": content}], max_tokens=2000)
    if client is openrouter:
        kwargs["extra_body"] = {"usage": {"include": True}}
    start = time.time()
    r = client.chat.completions.create(**kwargs)
    cost = float(getattr(r.usage, "cost", 0) or 0)
    return r.choices[0].message.content or "", cost, round(time.time() - start, 2), model


if "messages" not in st.session_state:
    st.session_state.messages = []
if "log" not in st.session_state:
    st.session_state.log = []

st.title("🔀 Cost-Aware LLM Router")
st.caption("Each prompt goes to the cheapest model that can handle it. Questions about live information get web search.")

with st.sidebar:
    mode = st.radio("Routing mode", ["Auto (router)", "Force free", "Force cheap", "Force premium"])
    st.caption("Each message is answered on its own (no chat memory).")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("meta"):
            st.caption(m["meta"])

prompt = st.chat_input("Ask anything")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    decision = route(prompt)
    tier = decision["tier"] if mode.startswith("Auto") else mode.split()[-1]
    search = decision["search"]

    with st.chat_message("assistant"):
        with st.spinner(f"Routing to {tier} tier{' with web search' if search else ''}..."):
            try:
                answer, cost, latency, model = ask(prompt, tier, search)
            except Exception as e:
                st.error(f"Model call failed: {e}")
                st.stop()
        meta = (f"Tier: **{tier}** · Model: {model} · Search: {'yes' if search else 'no'} · "
                f"Cost: ${cost:.5f} · Time: {latency}s")
        st.markdown(answer)
        st.caption(meta)

    st.session_state.messages.append({"role": "assistant", "content": answer, "meta": meta})
    st.session_state.log.append({"prompt": prompt[:80], "tier": tier, "model": model,
                                 "search": search, "cost_usd": cost, "latency_s": latency})

with st.sidebar:
    total = sum(x["cost_usd"] for x in st.session_state.log)
    st.metric("Session cost (USD)", f"${total:.5f}")
    st.metric("Messages", len(st.session_state.log))
    if st.session_state.log:
        log_df = pd.DataFrame(st.session_state.log)
        st.download_button("Download session log", log_df.to_csv(index=False),
                           file_name="session_log.csv", mime="text/csv")
