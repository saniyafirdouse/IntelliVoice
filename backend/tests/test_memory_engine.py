"""
Run from the backend/ folder:   python test_memory_engine.py
No server, database or API keys needed.
"""
from engines.memory_engine import MemoryEngine
 
 
def test_followup_carryover():
    m = MemoryEngine()
    s = "s1"
    e1 = m.resolve_entities(s, {"branch": "CSE", "quota": "management"}, needs_memory=False)
    m.add_turn(s, "CSE fee under management quota?", "fee_query", e1, "It is ...", "en")
 
    e2 = m.resolve_entities(s, {"branch": "ECE"}, needs_memory=True)
    assert e2 == {"branch": "ECE", "quota": "management"}, e2
    print("PASS 1: follow-up keeps quota, switches branch")
 
 
def test_resolved_entities_are_what_gets_saved():
    m = MemoryEngine()
    s = "s2"
    m.add_turn(s, "KCET cutoff for CSE", "cutoff_query", {"exam": "KCET", "branch": "CSE"}, "...", "en")
    resolved = m.resolve_entities(s, {"category": "GM"}, needs_memory=True)
    m.add_turn(s, "for GM?", "cutoff_query", resolved, "...", "en")
    ctx = m.get_context(s)
    assert ctx["active_entities"] == {"exam": "KCET", "branch": "CSE", "category": "GM"}, ctx
    print("PASS 2: Engine 3 filter and remembered state stay in sync")
 
 
def test_session_isolation():
    m = MemoryEngine()
    m.add_turn("parent_A", "CSE fee?", "fee_query", {"branch": "CSE"}, "...", "en")
    m.add_turn("parent_B", "Hostel?", "hostel_query", {"campus_facility": "hostel"}, "...", "hi")
    a = m.resolve_entities("parent_A", {}, needs_memory=True)
    b = m.resolve_entities("parent_B", {}, needs_memory=True)
    assert a == {"branch": "CSE"} and b == {"campus_facility": "hostel"}, (a, b)
    print("PASS 3: two users never see each other's memory")
 
 
def test_needs_memory_false_is_noop():
    m = MemoryEngine()
    s = "s4"
    m.add_turn(s, "CSE fee?", "fee_query", {"branch": "CSE"}, "...", "en")
    e = m.resolve_entities(s, {"campus_facility": "library"}, needs_memory=False)
    assert e == {"campus_facility": "library"}, e
    print("PASS 4: needs_memory=False ignores old entities")
 
 
def test_turn_order_and_clear():
    m = MemoryEngine()
    s = "s5"
    for i in range(1, 5):
        m.add_turn(s, f"q{i}", f"intent_{i}", {}, f"a{i}", "kn")
    ctx = m.get_context(s, last_n=3)
    assert [t["user_text"] for t in ctx["turns"]] == ["q2", "q3", "q4"], ctx
    assert ctx["last_intent"] == "intent_4" and ctx["turn_count"] == 4
    assert m.clear_session(s) is True
    assert m.get_context(s)["turn_count"] == 0
    print("PASS 5: turns in order, clear_session wipes memory")
 
 
if __name__ == "__main__":
    test_followup_carryover()
    test_resolved_entities_are_what_gets_saved()
    test_session_isolation()
    test_needs_memory_false_is_noop()
    test_turn_order_and_clear()
    print("\nAll 5 Memory Engine tests passed.")
 