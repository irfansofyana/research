# Research

This repository contains a list of my research carried out by AI agents.

<!-- [[[cog
import os
import subprocess
import json
from datetime import datetime

def get_first_commit_date(folder_path):
    try:
        # Get the date of the first commit that touched this folder
        cmd = ['git', 'log', '--diff-filter=A', '--follow', '--format=%aI', '--', folder_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        dates = result.stdout.strip().split('\n')
        if dates and dates[-1]:
            return dates[-1] # The last one is the oldest
        return None
    except Exception:
        return None

def get_project_summary(folder_path):
    summary_path = os.path.join(folder_path, '_summary.md')
    if os.path.exists(summary_path):
        with open(summary_path, 'r') as f:
            return f.read().strip()
    
    # If no summary exists, try to generate one using llm
    # This requires 'llm' to be installed and configured
    try:
        # Check if llm is installed
        subprocess.run(['llm', '--version'], check=True, capture_output=True)
        
        # Simple prompt to generate summary
        prompt = f"Describe the project in the folder '{folder_path}'. Create a concise, engaging summary with bullet points. Do not use a main header."
        
        # In a real scenario, we'd probably want to feed some file contents to llm.
        # For now, we'll just ask it to describe based on folder name/structure if possible, 
        # or we might need to list files. 
        # Let's list files to give it context.
        files = subprocess.run(['find', folder_path, '-maxdepth', '2', '-not', '-path', '*/.*'], capture_output=True, text=True).stdout
        
        full_prompt = f"{prompt}\n\nFiles in project:\n{files}"
        
        cmd = ['llm', '-m', 'github/gpt-4.1', full_prompt]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            summary = result.stdout.strip()
            with open(summary_path, 'w') as f:
                f.write(summary)
            return summary
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
        
    return "No summary available."

projects = []
for item in os.listdir('.'):
    if os.path.isdir(item) and not item.startswith('.'):
        date = get_first_commit_date(item)
        if date:
            projects.append({'name': item, 'date': date})

# Sort by date descending
projects.sort(key=lambda x: x['date'], reverse=True)

for project in projects:
    name = project['name']
    print(f"## [{name}]({name})")
    print(f"_{project['date'][:10]}_")
    print("")
    print(get_project_summary(name))
    print("")

]]] -->
## [example-research-project](example-research-project)
_2025-11-19_

Just example Project

This is an example research project created to test the auto-update README functionality.
It demonstrates how the system picks up new folders and adds them to the list.

## [poc-google-oauth-mcp](poc-google-oauth-mcp)
_2025-11-18_

No summary available.

<!-- [[[end]]] -->
