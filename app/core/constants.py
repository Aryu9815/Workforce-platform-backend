DEFAULT_STATES = [
    ("To Do", "todo", True, False, "#999999", 1),
    ("In Progress", "in_progress", False, False, "#0275d8", 2),
    ("Review", "review", False, False, "#f0ad4e", 3),
    ("Done", "done", False, True, "#5cb85c", 4),
]

TRANSITION_MAP = [
    ("To Do", "In Progress", False),
    ("In Progress", "Review", False),
    ("Review", "Done", False),
    ("Review", "In Progress", False),
]