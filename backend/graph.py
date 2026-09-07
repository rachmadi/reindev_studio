from langgraph.graph import StateGraph, START, END
try:
    from .state import SquadState
    from .agents.pm import pm_agent
    from .agents.architect import architect_agent
    from .agents.developer import developer_agent
    from .agents.tester import tester_agent
    from .agents.reviewer import reviewer_agent
    from .executor import executor_node
except (ImportError, ValueError):
    from state import SquadState
    from agents.pm import pm_agent
    from agents.architect import architect_agent
    from agents.developer import developer_agent
    from agents.tester import tester_agent
    from agents.reviewer import reviewer_agent
    from executor import executor_node

def route_after_executor(state: SquadState) -> str:
    """
    Menentukan apakah alur kerja perlu berputar kembali ke Developer (Self-Healing Loop)
    jika pengujian gagal dan batas iterasi belum tercapai, atau lanjut ke Code Reviewer.
    """
    test_results = state.get("test_results", {})
    passed = test_results.get("passed", False)
    iteration = state.get("iteration_count", 0)
    max_iter = state.get("max_iterations", 3)
    
    if not passed and iteration < max_iter:
        return "developer"
    return "reviewer"

def build_squad_graph():
    """Membangun StateGraph lengkap untuk virtual software squad ReinDev Studio."""
    workflow = StateGraph(SquadState)
    
    # 1. Daftarkan seluruh Node Spesialis
    workflow.add_node("pm", pm_agent)
    workflow.add_node("architect", architect_agent)
    workflow.add_node("developer", developer_agent)
    workflow.add_node("tester", tester_agent)
    workflow.add_node("executor", executor_node)
    workflow.add_node("reviewer", reviewer_agent)
    
    # 2. Rangkaikan Edges Sekuensial
    workflow.add_edge(START, "pm")
    workflow.add_edge("pm", "architect")
    workflow.add_edge("architect", "developer")
    workflow.add_edge("developer", "tester")
    workflow.add_edge("tester", "executor")
    
    # 3. Rangkaikan Conditional Edge (Cyclic Self-Healing Loop)
    workflow.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "developer": "developer",
            "reviewer": "reviewer"
        }
    )
    
    # 4. Finalisasi Alur
    workflow.add_edge("reviewer", END)
    
    return workflow.compile()

# Instance default yang siap digunakan
squad_graph = build_squad_graph()
