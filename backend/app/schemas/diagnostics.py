from typing import Literal

from pydantic import BaseModel

DiagnosticStatus = Literal["ok", "warning", "error"]


class DiagnosticCheck(BaseModel):
    name: str
    status: DiagnosticStatus
    message: str


class DiagnosticsResponse(BaseModel):
    message: str
    checks: list[DiagnosticCheck]
