export type Schema = Record<string, unknown>;
export const fieldTypes = ["string", "integer", "number", "boolean", "object", "array", "null"] as const;

export function objectValue(value: unknown): value is Schema {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

export function parseSchema(source: string): Schema | undefined {
  try {
    const parsed: unknown = JSON.parse(source);
    return objectValue(parsed) ? parsed : undefined;
  } catch {
    return undefined;
  }
}

export function typeLabel(value: unknown): string {
  if (value === false) return "never";
  if (!objectValue(value)) return "any";
  if (typeof value.$ref === "string") return value.$ref.split("/").at(-1) || "reference";
  if (Array.isArray(value.type)) return value.type.join(" | ");
  if (typeof value.type === "string") return value.type;
  if (Array.isArray(value.anyOf) || Array.isArray(value.oneOf)) return "union";
  return value.properties ? "object" : "any";
}

export function properties(schema: Schema): Schema {
  return objectValue(schema.properties) ? schema.properties : {};
}

export function renameField(schema: Schema, from: string, to: string): Schema {
  if (to === from) return schema;
  const fields = properties(schema);
  if (!to.trim() || Object.hasOwn(fields, to)) throw new Error("Each parameter needs its own name.");
  return {
    ...schema,
    properties: Object.fromEntries(Object.entries(fields).map(([key, value]) => [key === from ? to : key, value])),
    ...(Array.isArray(schema.required) ? { required: schema.required.map(key => key === from ? to : key) } : {}),
  };
}

export function requiredField(schema: Schema, key: string, required: boolean): Schema {
  const names = Array.isArray(schema.required) ? schema.required.filter(name => name !== key) : [];
  if (required) names.push(key);
  return { ...schema, required: names };
}

/** Resolve local JSON Pointers only. Schema inspection never contacts a remote reference. */
export function localReference(root: Schema, ref: string): Schema | undefined {
  if (ref === "#") return root;
  if (!ref.startsWith("#/")) return undefined;
  let item: unknown = root;
  try {
    for (const part of decodeURIComponent(ref.slice(2)).split("/")) {
      const key = part.replaceAll("~1", "/").replaceAll("~0", "~");
      if (!objectValue(item) || !Object.hasOwn(item, key)) return undefined;
      item = item[key];
    }
  } catch { return undefined; }
  return objectValue(item) ? item : undefined;
}

export function alternatives(field: Schema): unknown[] {
  for (const key of ["anyOf", "oneOf", "allOf"]) {
    if (Array.isArray(field[key])) return field[key];
  }
  return [];
}
