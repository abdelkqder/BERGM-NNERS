"""Plain explanations shared by the guided display and its evidence export."""
ROBOT_STATES = {
    "AVAILABLE": "ready at the entrance", "BUSY": "working on a job",
    "EN_ROUTE": "travelling to the finding", "RETURNING": "returning to the entrance",
    "NEEDS_REPAIR": "needs repair", "NEEDS_CHARGING": "needs charging",
    "OUT_OF_SERVICE": "out of service", "EXPLORING": "exploring the tunnel",
    "FAILED": "stopped after a failure", "DONE": "exploration ended",
    "ASSIGNED": "received a job", "DEPLOYING": "travelling to the finding",
    "ON_SITE": "at the finding", "WORKING": "handling the hazard",
    "VERIFYING": "checking the result", "UPDATE_MEMORY": "saving the new observation",
    "LOW_BATTERY": "battery low; returning", "WAITING": "waiting for route clearance",
    "COMPLETED": "job finished; return follows",
}
MEMORY_STATES = {"UNVERIFIED": "reported; needs checking", "VERIFIED": "checked; report confirmed", "ACTIVE": "checked; hazard still present",
                 "CLEARED": "removed or resolved", "CONTRADICTED": "checked; not found",
                 "ESCALATED": "still present; needs further help"}
MISSION_STATES = {"QUEUED": "waiting for a robot", "DISPATCHED": "instructions sent",
                  "IN_PROGRESS": "robot working", "BLOCKED": "route blocked; job unfinished",
                  "COMPLETED": "job finished", "FAILED": "attempt failed"}
MISSION_STATES.update(ASSIGNED="robot chosen; sending instructions", CANCELLED="no longer needs this job")


def explanation(session):
    if session.error:
        return dict(status="stopped", title="Demo stopped: a check failed",
                    what=session.error, why="Success requires every final check to pass.",
                    next="Press R to restart. Details shows the diagnostic evidence.")
    debris = session.name == "debris-recovery"
    failed_writer = session.name == "writer-failure"
    stories = [
        ("1. Explore and save findings", "The explorer searches the tunnel and saves hazards in small radio markers.",
         "Saved findings can survive even if the explorer stops.", "Let the explorer save its first finding."),
        ("2. Pass findings to the outside team", "The radio markers pass saved findings toward the entrance gateway.",
         "The outside command team needs those findings to choose the next jobs.", "Wait for exploration to end and the findings to arrive."),
        ("3. Send the response robots", "The explorer has stopped. The outside team now has its saved findings.",
         "The gateway carries the team's instructions back into the tunnel.", "Send robots with the right equipment to check the hazards."),
        ("4. Check the hazards", "Response robots have received instructions and are travelling to the findings.",
         "A saved report must be checked at its location.", "Wait for the robots to report what they find."),
    ]
    if debris:
        stories[2] = ("3. Add a blocked route and send robots", stories[2][1],
                      "This test adds rubble after exploration, so the saved route is now blocked.",
                      "Send a fire response robot; it must discover the blockage itself.")
        stories[3] = ("4. Discover the blocked route", "A fire response robot is travelling toward the saved fire report.",
                      "The robot must report new rubble before the outside team can arrange help.",
                      "Wait for the blocked job to be reported.")
        stories += [
            ("5. Remove the rubble", "The fire job is blocked. The outside team has requested rubble removal.",
             "The fire job remains unfinished until the route is cleared.", "Wait for the clearance report to reach the outside team."),
            ("6. Retry the fire job", "The outside team has received the clearance report and can retry the original job.",
             "The retry gets its own attempt number, so old results cannot finish it.", "Wait for the fire to be put out on the retry."),
        ]
    stories.append((f"{len(stories)+1}. Receive results and return home",
                    "The fire is resolved." + ("" if debris else " The gas was checked and is still present."),
                    "Robots and radio messages must finish returning before this demo can pass.",
                    "Wait for every response robot to return and every final check to pass."))
    stories.append(("Success: every check passed",
                    "The fire is resolved and the response robots are ready at the entrance.",
                    "" if debris else "The gas remains a hazard; finishing the checks does not make the tunnel safe.",
                    "Inspect the saved findings or press R to run again."))
    title, what, why, next_step = stories[session.stage]
    if failed_writer and session.stage in (2, 3):
        what = "The explorer failed as planned. Its findings survived in the radio markers and reached the outside team."
        why = "Response robots can use saved findings without the explorer returning."
    return dict(status="success" if session.done else "paused" if session.paused else "running",
                title=title, what=what, why=why or "The cleared route allowed the original fire job to finish.",
                next=("Press Space to continue. " if session.paused and not session.done else "") + next_step)
