# Formal Methods & Theorem Proving Exploration

Hands-on study of the mathematical foundations underlying formal verification
tools like VC Formal. Built as a companion to my
[RTL FPV Sequence Detector](https://github.com/Puji97/rtl-fpv-sequence-detector)
— that project applied FPV at the tool level; this one implements the theory underneath it.

## Why this project exists

Using VC Formal to verify RTL raises deeper questions:

- What algorithm is the tool actually running?
- What does "proof complete" mathematically mean?
- How does a safety property differ from a liveness property?
- What is a fixed-point and why does reachability computation use one?

This project answers those questions by building the machinery from scratch.

---

## Module 1 — Safety & Liveness Proofs in Lean 4

**Location:** `TrafficLight/Basic.lean`

A traffic light FSM modeled as an inductive type in Lean 4, with four
machine-verified proofs:

| Theorem                              | Property type    | What it proves                           |
| ------------------------------------ | ---------------- | ---------------------------------------- |
| `safety_red_not_green`               | Safety           | Red and Green are never the same state   |
| `liveness_reaches_green`             | Liveness         | Every state reaches Green within 3 steps |
| `invariant_green_reachable_from_red` | Invariant        | Green is always reachable from reset     |
| `no_deadlock`                        | Deadlock freedom | Every state has a successor              |

### Key concepts demonstrated

**Propositions as types.** In Lean, `Light.Red ≠ Light.Green` is not a
boolean check — it is a _type_. A proof of that statement is a _value_ of
that type. Lean's kernel verifies the construction is valid.

**Tactics and proof state.** Every proof is a conversation with the `⊢`
turnstile. Each tactic transforms the proof obligation until nothing remains
(`Goals accomplished`). This is the same obligation VC Formal discharges when
it reports "proof complete" on an SVA assertion.

**`decide` tactic.** Works because `Light` derives `DecidableEq` — Lean can
mechanically enumerate all cases and check the property holds on each one.
Equivalent to exhaustive state-space search.

### Connection to VC Formal

```
SVA assertion: assert property (!(red && green));
Lean theorem:  theorem safety : Light.Red ≠ Light.Green
Both express:  ⊢ no reachable state violates this property
```

### How to run

Install Lean 4 via elan:

```bash
curl https://elan.lean-lang.org/elan-init.sh -sSf | sh
elan default stable
```

Open `TrafficLight/Basic.lean` in VS Code with the `lean4` extension.
The Lean InfoView panel shows live proof state as you click through the file.

---

## Module 2 — Explicit-State Model Checker in Python

**Location:** `02-model-checking-python/model_checker.py`

Implements the core algorithm that formal verification tools use internally:
BFS fixed-point reachability, safety checking, and deadlock detection on
Kripke structures.

### The fixed-point algorithm

```python
reachable = init_states
while queue:
    state = queue.popleft()
    for successor in transitions[state]:
        if successor not in reachable:
            reachable.add(successor)
            queue.append(successor)
# fixed point: reachable stopped growing
```

This computes `R = lfp(λS. init ∪ post(S))` — the least fixed point of the
reachability operator. VC Formal runs this same computation on the Boolean
state space of your RTL (2^N states for N flip-flops — the state-space
explosion problem).

### Two examples

**Example 1 — Traffic Light (safe)**
Same FSM as Module 1, now model-checked algorithmically:

```
Fixed-point reached in 3 iterations
✓ SAFE — property holds on all 3 reachable states
✓ NO DEADLOCK — every reachable state has a successor
```

**Example 2 — Buggy Arbiter (intentional bugs)**
A 2-requester arbiter with a bug that allows double-granting:

```
Fixed-point reached in 6 iterations
✗ VIOLATION — bad states reached: [DEADLOCK_both_granted]
✗ DEADLOCK — states with no successors: [DEADLOCK_both_granted]
```

The model checker finds both the safety violation and the deadlock
automatically — exactly what VC Formal does when an SVA assertion fails.

### How to run

```bash
cd 02-model-checking-python
python3 model_checker.py
```

---

## How the modules connect

```
Lean (Module 1)          Python (Module 2)
─────────────────        ──────────────────────────────
theorem + proof    ←→    algorithm that checks the same property
decide tactic      ←→    BFS exhaustive state enumeration
Goals accomplished ←→    ✓ SAFE / ✓ NO DEADLOCK
proof obligation ⊢ ←→    bad_condition lambda
cases s tactic     ←→    for state in reachable: ...
```

Both modules check the same properties on the same FSM using different
approaches — Lean proves them mathematically, Python computes them
algorithmically.

---

## Skills demonstrated

- Lean 4 theorem proving: inductive types, pattern matching, tactic proofs
- Formal property specification: safety, liveness, invariants, deadlock freedom
- Fixed-point reasoning and reachability computation
- Kripke structures and model checking algorithms
- Connection between proof assistants and automated verification tools

---

## Related project

[RTL FPV Sequence Detector](https://github.com/Puji97/rtl-fpv-sequence-detector)
— applies these concepts at the tool level using SystemVerilog, SVA assertions,
and VC Formal FPV.
