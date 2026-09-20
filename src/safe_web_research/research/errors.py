class ResearchError(RuntimeError):
    """Base class for bounded research failures."""


class ResearchPlanningError(ResearchError):
    """The planner returned an invalid or unusable research plan."""


class ResearchSynthesisError(ResearchError):
    """The synthesizer returned an invalid or ungrounded result."""


class ResearchBudgetError(ResearchError):
    """A provider exceeded a budget that trusted code attempted to enforce."""
