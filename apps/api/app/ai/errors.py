"""Safe, provider-neutral AI errors."""


class AIError(Exception):
    """Base class for expected AI service failures."""


class AIConfigurationError(AIError):
    """AI routes or provider credentials are incomplete."""


class AIInputValidationError(AIError):
    """AI input exceeds the policy limits for a generation request."""


class AIProviderError(AIError):
    def __init__(
        self, provider: str, code: str, *, retryable: bool = False, status_code: int | None = None
    ) -> None:
        self.provider = provider
        self.code = code
        self.retryable = retryable
        self.status_code = status_code
        super().__init__(f"{provider} provider request failed: {code}")


class AIOutputValidationError(AIError):
    """Provider output was incomplete or did not match the requested schema."""


class AIUsageRecordingError(AIError):
    """A provider response could not be recorded by the required usage sink."""


class PromptNotFound(AIError):
    """The requested prompt identifier and version are not registered."""


class PromptInputError(AIError):
    """Prompt inputs are invalid or cannot be rendered."""


class AgentError(AIError):
    """An agent attempted an unsupported or invalid operation."""


class AgentLimitExceeded(AgentError):
    """An agent exceeded its configured step or tool-call limit."""
