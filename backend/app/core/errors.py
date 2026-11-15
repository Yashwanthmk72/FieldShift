# AI-assisted: written with an AI coding assistant (see README, "AI tools used").
"""Framework-free HTTP error type so services and repositories can signal status codes."""


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail
