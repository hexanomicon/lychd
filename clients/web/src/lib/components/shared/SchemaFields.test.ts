import { fireEvent, render, screen, within } from "@testing-library/svelte";
import { expect, it, vi } from "vitest";
import SchemaFields from "./SchemaFields.svelte";
import { example, validate } from "$lib/pages/loom/studio/blueprint";

function field(name: string, root: ParentNode = document) {
  const summary = [...root.querySelectorAll("details.parameter > summary")]
    .find(el => el.querySelector("strong")?.textContent === name);
  if (!summary) throw Error("Missing field: " + name);
  const body = summary.parentElement as HTMLDetailsElement;
  body.open = true;
  return body;
}

it("edits a nested array item, renames required fields, deletes and round trips the exact draft schema", async () => {
  let source = JSON.stringify({type:"object",description:"Preserve this",properties:{items:{type:"array",items:{type:"object",additionalProperties:false,properties:{}}}}});
  const onchange = vi.fn((value: string) => { source = value; });
  const view = render(SchemaFields,{source,onchange});
  const rerender = () => view.rerender({source,onchange});
  await fireEvent.click(within(field("items")).getByRole("button",{name:/Add parameter/})); await rerender();
  let parameter = within(field("parameter"));
  await fireEvent.click(parameter.getByRole("checkbox",{name:"Required"})); await rerender();
  parameter = within(field("parameter"));
  await fireEvent.change(parameter.getByLabelText("Name"),{target:{value:"path"}});
  await rerender();
  expect(JSON.parse(source).properties.items.items).toEqual({type:"object",additionalProperties:false,properties:{path:{type:"string"}},required:["path"]});
  const draft = example();
  draft.nodes[0]!.schema = source;
  expect(validate(JSON.parse(JSON.stringify(draft))).nodes[0]?.schema).toBe(source);
  expect(screen.queryByRole("textbox",{name:/Output schema/i})).toBeNull();
  await fireEvent.click(within(field("path")).getByRole("button",{name:"Remove"})); await rerender();
  const item = JSON.parse(source).properties.items.items;
  expect([item.properties,item.required,item.additionalProperties]).toEqual([{},[],false]);
});

it("expands nested arrays, unions and local recursive references read-only", () => {
  const schema={type:"array",items:{anyOf:[{$ref:"#/$defs/entry~1kind"},{type:"null"}]},$defs:{"entry/kind":{type:"object",properties:{message:{type:"string"},child:{$ref:"#/$defs/entry~1kind"}}}}};
  render(SchemaFields,{source:JSON.stringify(schema)});
  expect(screen.getByText("message")).toBeTruthy();
  expect(screen.getByText(/Recursive reference/)).toBeTruthy();
  expect(screen.queryByRole("button",{name:/Add parameter/})).toBeNull();
});
