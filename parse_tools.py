
import json
import glob
import os
for f in glob.glob(r'C:\Users\kaust\.gemini\antigravity-ide\brain\*\.system_generated\logs\transcript.jsonl'):
    try:
        for line in open(f, encoding='utf-8', errors='ignore'):
            obj = json.loads(line)
            if obj.get('type') == 'PLANNER_RESPONSE':
                for c in obj.get('tool_calls', []):
                    name = c.get('tool_name')
                    if name in ('write_to_file', 'replace_file_content', 'multi_replace_file_content'):
                        print(f"{os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(f))))} -> Step {obj.get('step_index')}: {name} -> {c.get('tool_arguments', {}).get('TargetFile')} ")
    except Exception as e:
        pass

