"""Pure phase2 assessment: advice and experiment observations grant no assay authority."""
REGISTERED = frozenset(("memo-scalar-boundary",))

def assess(packet):
    if not isinstance(packet,dict):return {"state":"NotAvailable","verdict":"Inconclusive","next":"ContextRequired","reason":"Malformed observations."}
    if any(type(packet.get(key)) is not bool for key in ("baselineAvailable","fresh","artifactsIntact","exactPin")):
        return {"state":"NotAvailable","verdict":"Inconclusive","next":"ContextRequired","reason":"Observation flags require explicit booleans."}
    if any(not isinstance(packet.get(key),list) or any(not isinstance(x,str) for x in packet[key]) for key in ("oldNamedCases","candidateOldCases","redFailures","expectedRedFailures")):
        return {"state":"NotAvailable","verdict":"Inconclusive","next":"ContextRequired","reason":"Named execution selections are malformed."}
    if any(not isinstance(packet.get(key),str) or len(packet[key])!=64 or any(c not in "0123456789abcdef" for c in packet[key]) for key in ("contract","baselineContract")) or not packet["expectedRedFailures"] or len(set(packet["expectedRedFailures"]))!=len(packet["expectedRedFailures"]):
        return {"state":"NotAvailable","verdict":"Inconclusive","next":"ContextRequired","reason":"Frozen contract pins and nonempty unique red expectations are required."}
    if not packet.get("baselineAvailable"):
        return {"state":"NotAvailable","verdict":"Inconclusive","next":"ContextRequired","reason":"Missing frozen baseline."}
    if packet.get("baselineVerdict") != "Pass":
        return {"state":"NotAvailable","verdict":"Inconclusive","next":"ContextRequired","reason":"Repair the failed original baseline before interpreting a change."}
    if not packet.get("fresh") or not packet.get("artifactsIntact"):
        return {"state":"NotAvailable","verdict":"Inconclusive","next":"ContextRequired","reason":"Source or retained evidence changed."}
    if packet.get("contract") != packet.get("baselineContract"):
        return {"state":"NotAvailable","verdict":"Inconclusive","next":"ContextRequired","reason":"A changed contract requires explicit reviewed migration."}
    old=packet.get("oldNamedCases",[])
    observed=packet.get("candidateOldCases",[])
    if len(old)<12 or len(set(old))!=len(old) or len(observed)<12 or len(set(observed))!=len(observed) or set(observed)!=set(old):
        return {"state":"Rejected","verdict":"Fail","next":"ContextRequired","reason":"The frozen twelve named acceptance cases and minimum must remain."}
    if packet.get("redCompilation")!="Pass" or packet.get("greenCompilation")!="Pass":
        return {"state":"NotAvailable","verdict":"Inconclusive","next":"ContextRequired","reason":"A compiler or infrastructure failure is not an acceptance failure."}
    if packet.get("redFailures")!=packet.get("expectedRedFailures"):
        return {"state":"Rejected","verdict":"Fail","next":"ContextRequired","reason":"Observed red acceptance failures differ from the registered requirement change."}
    if packet.get("candidateVerdict")!="Pass":
        budget=packet.get("budget",0)
        eligible=packet.get("probeId") in REGISTERED and type(budget) is int and budget>0
        return {"state":"NeedsReview","verdict":"Fail","next":"ProbeRequested" if eligible else "ContextRequired","reason":"Investigate the registered memo boundary; advice cannot execute or waive tests."}
    if not packet.get("exactPin"):
        return {"state":"NeedsReview","verdict":"Inconclusive","next":"ContextRequired","reason":"Exact native runtime qualification is missing."}
    return {"state":"ReadyForReview","verdict":"Pass","next":"NoInvestigation","reason":"Bounded native lifecycle observations completed; checker authority and human approval remain separate."}
