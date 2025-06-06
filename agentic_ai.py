import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import os
import requests
import json
import platform
import webbrowser

# Load API Key
load_dotenv()
client = OpenAI()

# Tool: Get weather
def get_weather(city: str):
    url = f"https://wttr.in/{city}?format=%C+%t"
    response = requests.get(url)
    if response.status_code == 200:
        return f"The weather in {city} is {response.text}."
    return "Something went wrong"

# Tool: Run various commands
def run_command(cmd: str):
    try:
        if cmd.startswith("create_file:"):
            _, filename, content = cmd.split(":", 2)
            with open(filename.strip(), "w", encoding="utf-8") as f:
                f.write(content)
            return f"{filename} created successfully."

        elif cmd.startswith("open_in_browser:"):
            target = cmd.split(":", 1)[1].strip()
            if target.startswith("http://") or target.startswith("https://"):
                webbrowser.open(target)
                return f"{target} opened in browser."
            else:
                filepath = os.path.abspath(target)
                if os.path.exists(filepath):
                    webbrowser.open(f"file://{filepath}")
                    return f"{target} opened in browser."
                else:
                    return f"Error: {target} does not exist."

        elif cmd.startswith("start_server:"):
            _, port = cmd.split(":")
            port = port.strip()
            if platform.system() == "Windows":
                os.system(f"start cmd /k python -m http.server {port}")
            else:
                os.system(f"nohup python3 -m http.server {port} &")
            return f"Server started on http://localhost:{port}"

        elif cmd.startswith("change_dir:"):
            _, path = cmd.split(":", 1)
            os.chdir(path.strip())
            return f"Changed directory to {os.getcwd()}"

        else:
            return os.popen(cmd).read()
    except Exception as e:
        return f"Error: {str(e)}"

# Tool registry
available_tools = {
    "get_weather": get_weather,
    "run_command": run_command,
}

# System prompt
SYSTEM_PROMPT = """
You are a helpful AI Assistant who is specialized in resolving user queries.
You work on start, plan, action, observe mode.

For the given user query and available tools, plan the step-by-step execution. Based on the planning,
select the relevant tool from the available tools. Then perform an action to call the tool.

Wait for the observation and, based on the tool output, resolve the user query.

Rules:
- Follow the Output JSON Format.
- Always perform one step at a time and wait for next input
- Carefully analyze the user query

Output JSON Format:
{
    "step": "string",
    "content": "string",
    "function": "The name of function if the step is action",
    "input": "The input parameter for the function"
}

Available Tools:
- "get_weather": Takes a city name as input and returns the current weather for that city
- "run_command": Takes a shell command (if simple), or:
    - `create_file:filename:content` to create a file
    - `open_in_browser:filename_or_url` to open a local file or URL
    - `start_server:<port>` to start a web server in the current directory
    - `change_dir:<path>` to change working directory
"""

# Streamlit UI
st.set_page_config(page_title="Tool-Using AI Assistant", layout="wide")
st.title("🧠 Tool-Using AI Assistant with Streamlit")
st.write("Enter your query below and let the assistant work through **plan → action → observe → output**.")

# Initialize session
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# User input
query = st.text_input("Your query", key="query_input")

if query:
    st.session_state.messages.append({ "role": "user", "content": query })

    while True:
        response = client.chat.completions.create(
            model="gpt-4.1",
            response_format={"type": "json_object"},
            messages=st.session_state.messages
        )

        response_json = response.choices[0].message.content
        st.session_state.messages.append({ "role": "assistant", "content": response_json })

        parsed_response = json.loads(response_json)
        step = parsed_response.get("step")

        # PLAN
        if step == "plan":
            st.info(f"🧠 Planning: {parsed_response.get('content')}")
            continue

        # ACTION
        elif step == "action":
            tool_name = parsed_response.get("function")
            tool_input = parsed_response.get("input")
            st.warning(f"🛠️ Tool: {tool_name} with input: {tool_input}")

            if tool_name in available_tools:
                tool_output = available_tools[tool_name](tool_input)
                st.session_state.messages.append({
                    "role": "user",
                    "content": json.dumps({
                        "step": "observe",
                        "output": tool_output
                    })
                })
                continue
            else:
                st.error(f"Unknown tool: {tool_name}")
                break

        # OUTPUT
        elif step == "output":
            st.success(f"🤖 Output: {parsed_response.get('content')}")
            break
