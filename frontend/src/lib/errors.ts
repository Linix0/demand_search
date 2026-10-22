export function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "发生未知错误，请稍后重试。";
}
