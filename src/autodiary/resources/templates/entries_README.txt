HOW TO CREATE DIARY ENTRIES
============================

## File Format
Create a JSON file with diary entries in this format:

[
  {
    "description": "What you did on this day",
    "hours": 8,
    "links": "https://github.com/project",
    "blockers": "Any issues you faced",
    "learnings": "What you learned today",
    "mood_slider": 5,
    "skill_ids": ["3", "44", "16"],
    "date": "2026-01-05"
  }
]

## Required Fields
- description: What you worked on (detailed description)
- hours: Number of hours worked (usually 8)
- links: Any relevant links (GitHub, documentation, etc.)
- blockers: Any challenges or blockers you faced
- learnings: What you learned or accomplished
- mood_slider: How you felt (1-5 scale, 5 being great)
- skill_ids: Array of skill ID strings (see below)
- date: Date in YYYY-MM-DD format

## Skill IDs
Skill IDs are required for each entry. Use the app's Help menu to see all available skills:

1. Open the app
2. Go to "Help & Documentation"
3. Select "View Available Skills"
4. Find the skills that match your work
5. Note the skill ID numbers

### Common Skill IDs
- "3" - Python
- "1" - JavaScript
- "10" - Java
- "44" - Data modeling
- "16" - Data visualization
- "20" - SQL
- "19" - Database design
- "15" - Machine learning
- "63" - Git

### Example Skill IDs
- Web development: ["1", "29", "30", "31"]  (JavaScript, HTML, CSS, React)
- Data analysis: ["3", "44", "16", "20"]     (Python, Data modeling, Data visualization, SQL)
- Backend development: ["3", "19", "20", "42"] (Python, Database design, SQL, MySQL)

## Tips
- Dates can be left empty ("") and will be auto-assigned during upload
- You can include multiple skills per entry
- Be descriptive in your learnings section
- Keep blockers specific and actionable
- Links are optional but helpful for reference

## Testing
Use the "Dry Run" option in the app to validate your entries before uploading!
