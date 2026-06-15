export type DiagnosticStatus = 'ok' | 'warning' | 'error'

export interface DiagnosticCheck {
  name: string
  status: DiagnosticStatus
  message: string
}

export interface DiagnosticsResponse {
  message: string
  checks: DiagnosticCheck[]
}
