"""Test B — Claude-directed motion graphics: "How AI agents use tools".

Two ways to run it:
* With ANTHROPIC_API_KEY set and budget.allow_paid_generation=true: pass --runtime to have the Claude provider direct the
  video from the topic notes below (paid; approved_budget_usd caps it).
* Without a key (default): render the storyboard in storyboard_b_agents_tools.json, which was directed in an interactive
  Claude Code session. Its `director` block says so; it is never presented as a runtime API result.
Either way the narration claims are verified against the topic notes.
"""
import json
import sys
import time
from pathlib import Path

from video_mcp import engine

NOTES = ("Tool use with Claude: you describe each tool with a name, a description, and a JSON schema for its inputs. When the model "
         "wants a tool, it stops and returns a tool call (a tool_use block) with the arguments it chose. Your code runs the tool and "
         "sends the result back, and the model continues from there. Without tools, the model can only guess from what it learned; "
         "with tools it checks live data. The Model Context Protocol standardizes how clients connect to tool servers, so one tool "
         "server can plug into many clients. Treat every tool result as untrusted input and require approval before anything destructive.")
TOPIC = {"id": "demo-b-agents-tools", "kind": "manual", "title": "How AI agents use tools", "summary": NOTES,
         "url": "https://docs.anthropic.com/en/docs/build-with-claude/tool-use", "published": time.time(), "retrieved_at": time.time(), "score": 0}

if __name__ == "__main__":
    if "--runtime" in sys.argv:
        print(json.dumps(engine.start_job(topic=TOPIC, mode="claude", approved_budget_usd=0.9, seed="demo-b"), indent=2))
    else:
        board = json.loads((Path(__file__).parent / "storyboard_b_agents_tools.json").read_text())
        print(json.dumps(engine.start_job(storyboard=board, topic=TOPIC, mode="claude", seed="demo-b"), indent=2))
