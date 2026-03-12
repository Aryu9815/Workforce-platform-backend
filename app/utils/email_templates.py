SPRINT_END = """
Dear Team,

The current sprint has now been formally closed.
I request you to review their open tickets 
{tickets}
and take the necessary actions at the earliest:

Move any pending or incomplete tickets to the Backlog.

If the work is planned for the upcoming cycle, move the tickets to the Next Sprint.

If needed, please create a new sprint and move the relevant backlog items accordingly.

Your timely action will help us maintain a clean workflow and ensure smooth planning for the next sprint.

Thank you for your cooperation.

Regards,
Aryan
"""

STAFF_JOINING = """
Dear {name},

Welcome to our company! We are pleased to have you as a part of our team.

Below are your employee details for your reference:

Staff ID: {id}
Designation: {designation}
Department: {department} 

Please ensure that your onboarding tasks are completed as guided by the HR team. If you need any assistance, feel free to reach out.

We look forward to your valuable contribution and wish you great success in your new role.

Warm regards,
Aryan
"""

STAFF_REMOVE = """
Dear {name},

This email is to formally notify you that your employment with our company has been discontinued effective .

Your Staff ID , along with all associated system access and permissions, will be deactivated as part of the offboarding process. Please ensure that you complete the required exit formalities and return any company assets in your possession, including documents, devices, and access cards.

If you require any clarification regarding final settlement, relieving letter, or other offboarding procedures, please reach out to the HR department.

We appreciate your contributions during your time with us and wish you the very best in your future endeavors.

Regards,
Aryan
"""

TASK_ASSIGNED = """
Dear {name},

A new task has been assigned to you. Please find the details below:

Ticket Number: {ticket}
Task Name: {task_name}
Description: {description}
Assigned By: {assigned_by}
Priority: {priority}

Kindly review the task and begin work as per the required priority. If you have any questions or need clarification, feel free to reach out to the assigning manager or your team lead.

Thank you for your prompt attention.

Regards,
Aryan
"""

TASK_COLLABARATED = """
Dear {name},

You have been assigned as a collaborator on the following ticket:

Ticket Number: {ticket}
Task Name: {task_name}
Description: {description}
Assigned By: {assigned_by}
Priority: {priority}

As a collaborator, you are requested to support the primary assignee in completing the task, provide updates when required, and contribute to ensuring timely progress.

If you require any clarification, please connect with the assigning manager.

Thank you for your cooperation.

Regards,
Aryan
"""

ADD_MEMBER = """
Dear {name},

You have been assigned to the following project. Please find the details below:

Project Name: {project_name}
Project Code: {project_code}
Description: {description}
priority: {priority}
Your Role: {role}
Assigned By: {assigned_by}

As a project member, you are expected to collaborate with the team and contribute to the successful completion of project tasks. Please review the project details and connect with the project lead if you require any further information.

We look forward to your valuable contribution to the project.

Regards,
Aryan
"""

TASK_INCOMPLETE_ALERT = """
Dear {name},

This is a reminder that the following task assigned to you is currently marked as incomplete:

Ticket Number: {ticket}
Task Name: {task_name}
Description: {task_description}
Due Date: {due_date}

Please review the task and update its progress or complete it at the earliest possible time. If you are facing any blockers or require assistance, kindly inform the concerned team member or manager.

Timely completion of tasks helps ensure smooth project progress.

Regards,
Aryan

"""