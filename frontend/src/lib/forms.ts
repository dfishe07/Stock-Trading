export function getValueAtPath<T = unknown>(source: Record<string, unknown>, path: string): T | undefined {
  return path.split(".").reduce<unknown>((current, key) => {
    if (current && typeof current === "object" && key in (current as Record<string, unknown>)) {
      return (current as Record<string, unknown>)[key];
    }
    return undefined;
  }, source) as T | undefined;
}

export function setValueAtPath<T extends Record<string, unknown>>(source: T, path: string, value: unknown): T {
  const next = structuredClone(source);
  const keys = path.split(".");
  let cursor: Record<string, unknown> = next;

  keys.forEach((key, index) => {
    if (index === keys.length - 1) {
      cursor[key] = value;
      return;
    }

    if (!cursor[key] || typeof cursor[key] !== "object") {
      cursor[key] = {};
    }
    cursor = cursor[key] as Record<string, unknown>;
  });

  return next;
}

