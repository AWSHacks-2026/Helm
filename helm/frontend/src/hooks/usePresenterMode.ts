export function readPresenterMode(search: string): boolean {
  const params = new URLSearchParams(search);
  return params.get("presenter") === "1" || params.get("demo") === "1";
}

export function usePresenterMode(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return readPresenterMode(window.location.search);
}
