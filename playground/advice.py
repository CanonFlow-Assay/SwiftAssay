"""Pure offline investigation selection; advice never grants verification."""

REGISTERED_PROBES = frozenset(("zero-amount", "exact-limit"))


def decide(observation: dict, budget: int = 3, fresh: bool = True) -> dict:
    if not fresh:
        return {"kind": "ContextRequired", "reason": "Source changed; collect fresh evidence."}
    if observation.get("baseline") != "Pass":
        return {"kind": "ContextRequired", "reason": "Repair or complete the original baseline first."}
    if observation.get("compilation") != "Pass":
        return {"kind": "ContextRequired", "reason": "Invalid or incomplete mutation execution is not a killed mutation."}
    if observation.get("expanded") == "Killed":
        if observation.get("original") == "Survived":
            if budget <= 0:
                return {"kind": "BudgetExhausted", "reason": "Keep the survivor visible; no probe budget remains."}
            if observation.get("probeId") not in REGISTERED_PROBES:
                return {"kind": "ContextRequired", "reason": "No eligible registered boundary investigation."}
            return {"kind": "ProbeRequested", "probeId": observation.get("probeId"),
                    "reason": "A registered boundary selection distinguishes the surviving change."}
        return {"kind": "NoInvestigation", "reason": "Existing tests killed this mutation."}
    if observation.get("expanded") == "Survived":
        return {"kind": "SurvivorReview", "reason": "A survivor is unresolved; do not infer equivalence or waive it."}
    return {"kind": "ContextRequired", "reason": "Missing or malformed execution evidence cannot support a proposal."}
