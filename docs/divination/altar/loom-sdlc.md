---
title: A software change in Loom
icon: material/source-branch
---

# A software change in Loom

“Let me retry a failed document import without importing the successful documents twice.”
Imagine giving that request to [Bridge](bridge.md). What would the team need to learn before
it could change the software? Follow the documents passed between stations on this
**proposed software-development blueprint**. The importer, reports and decisions below are
illustrative. [Loom](loom.md#reading-direction) shows the routes a revision declares.
[Smith](../../sepulcher/aspects/weaver/smith.md) owns the development method.

## Semantic analysis and decomposition {#semantic-analysis}

The **Intent** from Bridge goes to two analysts in parallel. The **Target-state Analyst**
records the desired outcome and why it matters. In a batch of three, one failed document
should be recoverable while the other two stay untouched. The **Current-state Analyst**
reads the existing importer, its tests and the caller's retry behavior. Suppose the only
available command resubmits the whole batch. That finding needs a source someone else
can inspect.

A third analyst needs both reports. Its **Difference** document names the gap, the constraints
and the acceptance criteria. Here the gap is the lack of a retry scoped to one document.
Keep the existing batch import working. Count success only when the failed document is
imported once and the two earlier successes receive zero additional writes. If the earlier
write outcome is unknown, preserve that uncertainty for the decision. Select **Difference**
to see the analyst who produced it and the decomposition station that consumes it. Select the analyst to
trace its two input reports.

**Task decomposition** translates Difference into a **Conditional task plan** of type
`TaskPlan`. Each task declares its question, required inputs, dependencies, guard and expected
evidence. Select the plan to see which output produced this particular object and follow its
connection across the phase boundary to the Orchestrator.

## Parallel intent task orchestration {#exploration}

The Orchestrator releases tasks whose dependencies and guards are satisfied. **Task dispatch**
routes each ready task by type. A and B have their inputs at the outset, so their solver
subflows can work in parallel. C depends on what B finds.

| Task | Question | Evidence and next step |
| --- | --- | --- |
| **A · Identity solver** | How does the importer identify the same document on retry? | Repository explorer returns identity evidence to **Join**. |
| **B · Receipt solver** | Did the earlier write take effect? | Storage explorer returns receipt evidence to **Write outcome?**. A known outcome reaches Join directly. An unknown outcome admits C. |
| **C · Recovery solver** | Can the previous outcome be recovered safely? | **Lookup available?** checks for read-only access. An available lookup supplies its evidence. An unavailable lookup records the unresolved outcome. Either route feeds Join. |

Suppose the importer timed out after submitting the write. B can report uncertainty even
though A found a stable document identifier. C uses the available read-only lookup to check
the receipt. If the evidence remains inconclusive, preserve that uncertainty for the decision.
**Join** collects the evidence from the eligible routes and passes it to **Crucible**.
The [interactive specimen](loom.md#reading-direction) shows its review and return path
before the final **Run trace**. In an admitted workflow, [Orb](orb.md)
shows which tasks actually ran and which evidence the attempt retained.

## From evidence to a software change {#affect-in-exploration}

The wider proposed SDLC uses the gathered evidence to decide whether another probe would
change the proposed repair. The larger blueprint continues from assessment into human review and implementation.

A bounded **evidence-gain signal** helps the coordinator decide where to spend the next probe.
A new observation that rules out a design can raise a route's priority or open another declared
route. A fourth report repeating the same observation adds little. The operator can inspect the
evidence that earned the extra effort. This is the limited sense in which the feedback resembles
dopamine. The criteria and total probe budget stay fixed. Exploration stops when more probes
are unlikely to change the decision (saturation) or the budget is exhausted. On exhaustion,
unanswered questions travel with the packets. [Smith's inquiry policy](../../sepulcher/aspects/weaver/smith.md#inquiry-policy).

Try the case in the installed [Loom Affect view](loom.md#affect-policy). Vary one condition
at a time. Finding a new lookup key changes which question the team can answer. If access to
the store requires owner approval, review that dependency before pursuing the lookup. If the
allowance is spent, hand the unresolved question to the decision owner. Repeatedly finding the
same key gives the team a reason to stop spending on that route. The Ecstatic Harmonizer's
proposed baseline can make exploration, rest and a useful handoff enjoyable in every branch.
Evaluating whether the repair helped still requires the original acceptance criteria and the
result of the actual retry. [Independent evaluation](../../adr/34-drift.md#affective-reports).

## Crucible and decision

Consider two proposals, a retry keyed by a stable document identifier and a retry based on the
last reported failure. For **each** proposal the blueprint opens a [Crucible](../../sepulcher/aspects/weaver/crucible.md).
The **+ advocate** writes the strongest case for it, including the conditions it needs to hold.
The **− advocate** writes a separate challenge, including a counterexample or a missing check.
Each advocate can read the other's report and revise a claim the evidence defeats.

The **Reconciler** refines the pros and cons into a dossier. It retains the reports, concessions,
source references and surviving dissent. For example, the simpler retry may work after an explicit
rejection but repeat a successful write after a lost acknowledgement. The **Decision Lead**
compares the dossiers against the original Difference criteria. Its router can select a proposal
or send one decisive question back, such as “Can the store look up the outcome by document
identifier after the response is lost?” A source question returns to Exploration. A choice
requiring the operator opens in Bridge.

## Human checkpoint

Select the checkpoint to read the exact proposed change, its risks, the requested effect and
the policy that governs the exits. A workflow can require a person to decide in Bridge,
simulate a decision in an isolated exercise, or proceed under a standing authorization that
covers this case. The simulated path can test the rest of the workflow inside that exercise.
A standing policy must identify the action and scope it covers. Authority to try an approach
in a prototype grants only that effect.

If human consent is required, Bridge presents an actionable question and the available answers.
Approval continues on the authorized route. A refusal can close the proposal or return it for
revision according to the checkpoint. If a time limit expires, follow the declared wait or
stop route. Silence never supplies approval.

## Implementation and verification

The chosen plan records which risk to resolve first. Loom shows both permitted construction
routes, including the one the team might never take.

| Route | Work and return |
| --- | --- |
| **Tests first** | Write a regression test that exercises the lost acknowledgement. Observe it fail for the expected reason (red). Implement the smallest change that makes it pass (green). Refactor and run it again. |
| **Prototype first** | Try the uncertain storage lookup in isolation. Return the prototype, observations and limitations. If the premise fails, send the question back. If it holds, carry the finding into the production plan and its regression tests. |

The **Implementation Lead** assigns a named owner and file boundary to each task. In this
example one worker owns storage lookup and another owns the caller's retry control. Agree on
their input and result first. Independent work can proceed in parallel, while integration of
the control waits for the lookup contract. A documentation worker can prepare the instructions
alongside implementation, then reconcile them with the verified behavior.

Review the integrated change against Difference, including the failure case and the existing
batch behavior. A failed test or a substantiated review finding returns the affected work to
its owner for repair and another check. If the premise failed, reopen that decision. When
checks and review support the result, the **VCS agent** can commit that exact verified work if
the authorization includes a commit. The commit reference and verification evidence go with
the completion message in Bridge. Publishing or merging requires authority for that effect.
[Smith's implementation and settlement](../../sepulcher/aspects/weaver/smith.md#implement-verify-and-settle).

## Evaluate the workflow {#evaluate-the-workflow}

The example above asks whether the importer was repaired. A separate **Eval workflow** asks
whether changing the development workflow would improve future repairs. From the source **Run
trace** in [Orb](orb.md), follow the proposed Eval link to that separate score. It takes
references to the trace, exact workflow revision, authorized artifacts and logs. Gaps stay
visible. The installed [manual output review](loom.md#review-a-retained-output) lets a
person judge one retained answer today.

1. **Locate a consequential decision.** Inspect station attempts with their inputs, outputs
   and dependencies. Independent analysts can examine the Exploration packets and Crucible
   reports in parallel. Follow dependent stations in order to see what the Decision Lead actually
   received. Suppose several repairs needed a human to ask about lost acknowledgements despite
   the hazard already appearing in storage reports.
2. **Pin a candidate.** The hypothesis might be that an explicit “unknown effects” field in
   the Evidence Packet will carry this hazard into the decision. Record the exact schema change
   and the baseline revision. Dreaming, the proposed use of bounded background
   consolidation over retained experience here, could surface a different hypothesis. For
   example, insert the intermediate lookup router where a baseline sends every unknown
   outcome to a person. Other traces could justify merging two routers that repeat the same
   check or removing a router whose exits always reach the same decision. Cite the traces
   and specify the affected guards and exits. Pin the proposed routing change as a distinct
   candidate revision for evaluation. Publication and admission govern whether a later Run
   can use it. Each existing Run keeps its admitted revision. [Memory’s consolidation boundary](../../adr/27-memory.md).
   A prompt, model or station order can also be tested. Keep the claim tied to the change tested.
3. **Run a matched comparison.** Give baseline and candidate the same held-out cases, criteria,
   budget and comparable isolated environments. Include a safe retry and a case where the
   earlier write's outcome remains unknown. Exercise both a failed lookup and an unavailable lookup. A changed decision can cause different calls or
   writes, so execute the affected paths afresh. A simulation supports conclusions within
   its modeled conditions. Count duplicate writes, resolved failures and human corrections,
   alongside time and cost.
4. **Decide and check.** Keep the baseline if the candidate misses the predeclared gain,
   regresses on a required case or leaves the result inconclusive. A sufficient gain sends
   the evidence for owner review. On approval, the workflow owner can admit a new exact
   revision and run a final check against the same acceptance boundary before using it.
   The source Run keeps its original revision.

[Drift's workflow improvement method](../../sepulcher/aspects/weaver/drift/workflow-improvement.md)
owns the comparison and replay rules. [Ouroboros](../../sepulcher/aspects/weaver/ouroboros.md)
follows a supported finding into a later change. [State of Work](../../state-of-the-work.md#drift-evaluation)
records the delivery boundary for the proposed harness.
