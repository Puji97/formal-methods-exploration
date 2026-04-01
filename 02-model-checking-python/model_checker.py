"""
Explicit-State Model Checker
=============================
Implements the core algorithm inside formal verification tools.
Given a state machine, it:
  1. Computes ALL reachable states (BFS fixed-point)
  2. Checks safety properties on that set
  3. Detects deadlocks
  4. Checks liveness via cycle detection

Hardware connection:
  VC Formal does exactly this on your RTL's Boolean state space.
  For N flip-flops: 2^N states — the state-space explosion problem.
"""

from collections import deque


# ── Data Structures ───────────────────────────────────────────────────────────

class State:
    """
    A single state in the system.
    frozen via __hash__ so states can live in sets and dicts.
    This is like one row in your FSM state encoding table.
    """
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name


class StateMachine:
    """
    A Kripke structure — the mathematical object model checkers operate on.

    In hardware terms:
      states      = all possible flip-flop value combinations
      init_states = reset state
      transitions = combinational next-state logic
      labels      = which signals are asserted in each state
    """
    def __init__(self, states, init_states, transitions, labels):
        self.states      = states       # set of State
        self.init_states = init_states  # set of State (where system starts)
        self.transitions = transitions  # dict: State -> set of State
        self.labels      = labels       # dict: State -> set of strings

        # ── Layer 2: Reachability (The Fixed-Point Computation) ───────────────────────

def compute_reachable(sm):
    """
    BFS from initial states until no new states are discovered.
    
    This IS the fixed-point computation:
      Start with R = init_states
      Repeatedly add: any state reachable from something already in R
      Stop when R doesn't change — that's the fixed point
    
    Why "fixed point"? Because we're looking for a set R where:
      R = init ∪ post(R)
    Once R satisfies that equation, adding more transitions gives nothing new.
    
    State-space explosion: for N flip-flops this set has up to 2^N members.
    That's why SAT-based tools exist — they represent this set symbolically.
    """
    reachable = set(sm.init_states)   # start with initial states
    queue     = deque(sm.init_states) # BFS frontier
    iterations = 0

    while queue:
        state = queue.popleft()
        iterations += 1

        for successor in sm.transitions.get(state, set()):
            if successor not in reachable:
                reachable.add(successor)    # new state found
                queue.append(successor)     # explore it next

    print(f"\n  Fixed-point reached in {iterations} iterations")
    print(f"  Reachable states: {{{', '.join(s.name for s in reachable)}}}")
    return reachable


# ── Layer 4: Deadlock Detection ───────────────────────────────────────────────

def check_deadlock(sm, reachable):
    """
    Deadlock: a reachable state with NO outgoing transitions.
    The system gets stuck — no next state exists.

    In hardware: an FSM state with no next-state logic defined.
    In SVA:      assert property (always !stuck);
    """
    print(f"\n  Checking deadlock freedom")

    deadlocked = [
        s for s in reachable
        if not sm.transitions.get(s, set())
    ]

    if deadlocked:
        print(f"  ✗ DEADLOCK — states with no successors: {deadlocked}")
        return False
    else:
        print(f"  ✓ NO DEADLOCK — every reachable state has a successor")
        return True
    
# ── Layer 3: Safety Checking ──────────────────────────────────────────────────

def check_safety(sm, reachable, bad_condition, property_name):
    """
    Safety: "nothing bad ever happens"
    = no reachable state satisfies the bad condition

    Algorithm: just scan every reachable state.
    If ANY state satisfies bad_condition → safety violation.

    In SVA:     assert property (always !bad);
    In Lean:    theorem safety : ¬bad(s) for all reachable s
    In VC Formal: proof failure + counterexample trace
    """
    print(f"\n  Checking safety: '{property_name}'")

    violations = []
    for state in reachable:
        props = sm.labels.get(state, set())
        if bad_condition(props):
            violations.append(state)

    if violations:
        print(f"  ✗ VIOLATION — bad states reached: {violations}")
        print(f"  In VC Formal this would be a failing assertion + CEX waveform")
        return False
    else:
        print(f"  ✓ SAFE — property holds on all {len(reachable)} reachable states")
        return True

# ── Example 1: Traffic Light ──────────────────────────────────────────────────

def run_traffic_light():
    print("\n" + "="*60)
    print("EXAMPLE 1: Traffic Light")
    print("Same FSM you proved in Lean — now model-checked in Python")
    print("="*60)

    red    = State("Red")
    green  = State("Green")
    yellow = State("Yellow")

    sm = StateMachine(
        states      = {red, green, yellow},
        init_states = {red},
        transitions = {
            red:    {green},
            green:  {yellow},
            yellow: {red},
        },
        labels = {
            red:    {"red_active"},
            green:  {"green_active"},
            yellow: {"yellow_active"},
        }
    )

    reachable = compute_reachable(sm)

    check_safety(sm, reachable,
        bad_condition   = lambda p: "red_active" in p and "green_active" in p,
        property_name   = "red and green never simultaneously active")

    check_deadlock(sm, reachable)

# ── Example 2: Buggy Arbiter ──────────────────────────────────────────────────

def run_buggy_arbiter():
    print("\n" + "="*60)
    print("EXAMPLE 2: Buggy Arbiter — intentional deadlock")
    print("2 requesters, 1 shared resource, 1 bug")
    print("="*60)

    idle     = State("Idle")
    req_a    = State("ReqA_Pending")
    req_b    = State("ReqB_Pending")
    grant_a  = State("GrantA")
    grant_b  = State("GrantB")
    deadlock = State("DEADLOCK_both_granted")  # the bug

    sm = StateMachine(
        states      = {idle, req_a, req_b, grant_a, grant_b, deadlock},
        init_states = {idle},
        transitions = {
            idle:     {req_a, req_b},
            req_a:    {grant_a, deadlock},  # bug: can go to deadlock
            req_b:    {grant_b, deadlock},  # bug: can go to deadlock
            grant_a:  {idle},
            grant_b:  {idle},
            deadlock: set(),                # no outgoing transitions — stuck!
        },
        labels = {
            idle:     {"idle"},
            req_a:    {"req_a"},
            req_b:    {"req_b"},
            grant_a:  {"grant_a", "resource_busy"},
            grant_b:  {"grant_b", "resource_busy"},
            deadlock: {"grant_a", "grant_b", "resource_busy", "deadlocked"},
        }
    )

    reachable = compute_reachable(sm)

    check_safety(sm, reachable,
        bad_condition = lambda p: "grant_a" in p and "grant_b" in p,
        property_name = "resource never double-granted")

    check_deadlock(sm, reachable)


if __name__ == "__main__":
    print("Explicit-State Model Checker")
    run_traffic_light()
    run_buggy_arbiter()

    