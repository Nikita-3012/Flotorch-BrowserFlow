"""browser-use step hooks for console visibility."""

from browser_use import Agent

from constants import WORKSPACE_FALLBACK_TOKEN


def make_step_end_logger(phase_label: str, *, watch_workspace_fallback: bool = False):
    """Log each browser-use iteration (one LLM step) to stdout — common QA automation visibility."""

    fallback_notice_printed = False

    async def _on_step_end(agent: Agent) -> None:
        nonlocal fallback_notice_printed
        if watch_workspace_fallback and not fallback_notice_printed:
            mo = agent.state.last_model_output
            if mo:
                blob = " ".join(
                    filter(
                        None,
                        [
                            mo.memory,
                            mo.next_goal,
                            mo.evaluation_previous_goal,
                            mo.thinking,
                        ],
                    )
                )
                if WORKSPACE_FALLBACK_TOKEN in blob:
                    print(
                        "\n>>> QA: Custom workspace creation failed — "
                        'continuing inside "Default Workspace".\n'
                    )
                    fallback_notice_printed = True

        completed_idx = max(0, agent.state.n_steps - 1)
        last_url = ""
        if agent.history.history:
            last_url = (agent.history.history[-1].state.url or "").strip()
        url_suffix = f" | {last_url}" if last_url else ""
        print(f"[{phase_label}] browser-use step {completed_idx} finished{url_suffix}")

    return _on_step_end
