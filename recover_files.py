import json
import os

log_file = "/Users/orlando/.gemini/antigravity-ide/brain/7eeb8c09-674f-4792-a100-4111d3152562/.system_generated/logs/transcript.jsonl"

files_to_recover = {
    "/Users/orlando/python/FastAPI/brazcom_isp/backend/app/schemas/caixa.py": None,
    "/Users/orlando/python/FastAPI/brazcom_isp/backend/app/crud/crud_caixa.py": None,
    "/Users/orlando/python/FastAPI/brazcom_isp/backend/app/routes/caixa.py": None,
    "/Users/orlando/python/FastAPI/brazcom_isp/frontend/src/pages/CaixaPDV.tsx": None,
    "/Users/orlando/python/FastAPI/brazcom_isp/frontend/src/services/caixaService.ts": None
}

with open(log_file, "r") as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get("type") == "PLANNER_RESPONSE":
                for tc in data.get("tool_calls", []):
                    if tc["name"] == "write_to_file":
                        # The args might be a string or a dict depending on how it was logged
                        args = tc["args"]
                        if isinstance(args, str):
                            args = json.loads(args)
                        target = args.get("TargetFile", "").strip('"')
                        if target in files_to_recover:
                            # Try to decode the content if it's double-encoded
                            content = args.get("CodeContent", "")
                            if content.startswith('"') and content.endswith('"'):
                                try:
                                    content = json.loads(content)
                                except:
                                    pass
                            files_to_recover[target] = content
        except Exception as e:
            pass

for filepath, content in files_to_recover.items():
    if content:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as out:
            out.write(content)
        print(f"Recovered: {filepath}")
    else:
        print(f"Could not find history for: {filepath}")
