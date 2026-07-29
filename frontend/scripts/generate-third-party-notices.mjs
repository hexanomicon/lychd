import { readFile, readdir, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const lockPath = join(frontendRoot, "package-lock.json");
const outputPath = join(frontendRoot, "static", "THIRD_PARTY_NOTICES.txt");

const fallbackCopyright = new Map([
  ["@polka/url", "Copyright (c) Luke Edwards"],
  ["@redocly/openapi-core", "Copyright 2019 Redocly Inc."],
  ["@rolldown/binding-linux-x64-gnu", "Copyright (c) 2024-present VoidZero Inc. & Contributors"],
  ["change-case", "Copyright (c) Blake Embrey"],
  ["is-reference", "Copyright (c) Rich Harris"],
  ["locate-character", "Copyright (c) Rich Harris"],
  ["saxes", "Copyright (c) Louis-Dominique Dubeau"],
  ["sirv", "Copyright (c) Luke Edwards"],
  ["stackback", "Copyright (c) Roman Shtylman"],
  ["uri-js-replace", "Copyright (c) Andreinwald and contributors"]
]);

const mitTerms = `Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.`;

const iscTerms = `Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.`;

function fallbackLicense(name, expression) {
  const copyright = fallbackCopyright.get(name);
  if (!copyright) {
    throw new Error(`${name} declares ${expression} but ships no license file and has no audited fallback`);
  }
  if (expression === "MIT") return `MIT License\n\n${copyright}\n\n${mitTerms}`;
  if (expression === "ISC") return `ISC License\n\n${copyright}\n\n${iscTerms}`;
  throw new Error(`${name} declares unsupported fallback expression ${expression}`);
}

function packageNameFromPath(relativePath) {
  const marker = "node_modules/";
  const tail = relativePath.slice(relativePath.lastIndexOf(marker) + marker.length);
  const parts = tail.split("/");
  return parts[0].startsWith("@") ? `${parts[0]}/${parts[1]}` : parts[0];
}

function normalize(text) {
  return text.replaceAll("\r\n", "\n").trim();
}

const lock = JSON.parse(await readFile(lockPath, "utf8"));
const packages = new Map();

for (const [relativePath, lockEntry] of Object.entries(lock.packages ?? {})) {
  if (!relativePath.includes("node_modules/")) continue;
  if (lockEntry.optional === true) continue;

  const packageDirectory = join(frontendRoot, relativePath);
  const manifest = JSON.parse(await readFile(join(packageDirectory, "package.json"), "utf8"));
  const name = manifest.name ?? packageNameFromPath(relativePath);
  const version = manifest.version ?? lockEntry.version;
  const key = `${name}@${version}`;
  if (packages.has(key)) continue;

  const filenames = (await readdir(packageDirectory))
    .filter((filename) => /^(licen[cs]e|copying|notice)([-._]|$)/i.test(filename))
    .sort((left, right) => left.localeCompare(right));
  const texts = [];
  for (const filename of filenames) {
    texts.push(`--- ${filename} ---\n${normalize(await readFile(join(packageDirectory, filename), "utf8"))}`);
  }

  const expression = manifest.license ?? lockEntry.license ?? "UNKNOWN";
  packages.set(key, {
    expression,
    key,
    repository: manifest.repository,
    text: texts.length > 0 ? texts.join("\n\n") : fallbackLicense(name, expression)
  });
}

const sections = [...packages.values()]
  .sort((left, right) => left.key.localeCompare(right.key))
  .map((item) => {
    const repository =
      typeof item.repository === "string" ? item.repository : item.repository?.url ?? "not declared";
    return [
      "=".repeat(80),
      item.key,
      `Declared license: ${item.expression}`,
      `Repository: ${repository}`,
      "=".repeat(80),
      "",
      item.text
    ].join("\n");
  });

const output = `${[
  "LychD Altar — Third-Party Notices",
  "",
  "Generated deterministically from frontend/package-lock.json and the installed package",
  "license files. The inventory deliberately covers the complete locked frontend dependency",
  "non-optional set; inclusion here does not claim that every package contributes code to every",
  "bundle. Platform-specific optional build packages are not shipped in the browser artifact.",
  "",
  "Regenerate with: npm run licenses",
  ""
].join("\n")}${sections.join("\n\n")}\n`;

await writeFile(outputPath, output, "utf8");
