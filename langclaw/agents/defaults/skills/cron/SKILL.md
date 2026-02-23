---
name: "cron"
description: "Use this skill when the user wants to schedule a recurring reminder or task, list their scheduled jobs, or cancel an existing job."
---

# Cron Skill

## Purpose

Create, inspect, and remove time-based automations using the `cron` tool.
There are two modes:

- **Reminder mode** — deliver a static message to the user on a schedule.
- **Task mode** — describe a task for the agent to execute each time the job fires (e.g. "Check the weather and report").

## When to Use

- User says "remind me", "every X minutes", "schedule", "set up a recurring task"
- User asks to see their active reminders or jobs
- User wants to cancel or stop a scheduled job

## Tool Reference

The `cron` tool accepts an `action` and scheduling parameters.

### Add a job

```
cron(action="add", message="<text or task>", every_seconds=<N>)
cron(action="add", message="<text or task>", cron_expr="<5-field cron>")
```

Exactly one of `every_seconds` or `cron_expr` is required.
`message` should contain only the task/reminder content.
Do not include schedule/timezone or recipient/user details in `message`;
those are defined by cron parameters + channel context.

### List active jobs

```
cron(action="list")
```

Returns all scheduled jobs with their ID and schedule.

### Remove a job

```
cron(action="remove", job_id="<id>")
```

Use the job ID returned by `list` or `add`.

## Natural Language → Schedule Mapping

| User says              | Parameters                         |
|------------------------|------------------------------------|
| "every 20 minutes"     | `every_seconds=1200`               |
| "every hour"           | `every_seconds=3600`               |
| "every day at 9 AM"    | `cron_expr="0 9 * * *"`            |
| "weekdays at 5 PM"     | `cron_expr="0 17 * * 1-5"`         |
| "every Monday at 8 AM" | `cron_expr="0 8 * * 1"`            |
| "twice a day"          | `cron_expr="0 9,21 * * *"`         |

## Examples

Reminder every 20 minutes:

```
cron(action="add", message="Time to take a break!", every_seconds=1200)
```

Daily weather report task:

```
cron(action="add",
     message="Check today's weather forecast and send a brief summary.",
     cron_expr="0 8 * * *")
```

Daily quote task (task-only `message`):

```
cron(action="add",
     message="Pick one movie/anime quote matching today's mood from local weather + weekday/weekend. Output: quote, 1-2 sentence why-it-fits, source URL. Add SPOILER WARNING only for major twists/final-act reveals. Avoid explicit NSFW.",
     cron_expr="30 13 * * *")
```

List all jobs:

```
cron(action="list")
```

Remove a job:

```
cron(action="remove", job_id="3f2a1b...")
```

## Notes

- Always confirm the schedule back to the user after creating a job (e.g. "I've set a reminder every 20 minutes").
- When the user says "cancel all reminders", call `list` first to get IDs, then `remove` each one.
- Cron expressions use UTC by default unless the gateway is configured with a different timezone.
- Jobs are in-memory and do not survive a gateway restart.
