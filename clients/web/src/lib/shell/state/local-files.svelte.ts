/** File contents and revisions belong to the current browser document. */
interface RevisionEntry {
  id: number;
  time: string;
  action: string;
  detail: string;
}
interface OpenFile {
  id: number;
  name: string;
  text: string;
  draft: string;
  revision: number;
  history: RevisionEntry[];
}

const byteLimit = 1024 * 1024;

function appendEntry(file: OpenFile, action: string, detail: string) {
  file.history.push({ id: file.history.length + 1, time: new Date().toISOString(), action, detail });
}

export function createLocalFiles() {
  let files = $state<OpenFile[]>([]);
  let selected = $state<number | null>(null);
  let notice = $state("");
  let ordinal = 0;
  const current = $derived(files.find((file) => file.id === selected));

  async function open(file: File) {
    if (file.size > byteLimit) {
      notice = "Choose a text file up to 1 MiB.";
      return;
    }
    try {
      const text = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer());
      if (text.includes("\u0000")) throw new Error("Binary input");
      const record: OpenFile = {
        id: ++ordinal,
        name: file.name,
        text,
        draft: text,
        revision: 1,
        history: [],
      };
      appendEntry(record, "Read", `Opened ${file.size} bytes from the selected file.`);
      files.push(record);
      selected = record.id;
      notice = "";
    } catch {
      notice = "Could not read this file as UTF-8 text. Choose a text file.";
    }
  }

  function save() {
    if (!current || current.text === current.draft) return;
    if (new Blob([current.draft]).size > byteLimit) {
      appendEntry(current, "Edit refused", "The draft exceeds 1 MiB. Shorten it and retry.");
      notice = "Revision exceeds 1 MiB. The last saved revision is still available.";
      return;
    }
    const before = current.text.split("\n");
    const after = current.draft.split("\n");
    let firstChange = 0;
    while (
      firstChange < before.length &&
      firstChange < after.length &&
      before[firstChange] === after[firstChange]
    ) {
      firstChange++;
    }
    current.text = current.draft;
    current.revision++;
    notice = "";
    appendEntry(
      current,
      "Edited",
      `Revision ${current.revision}. First changed line ${firstChange + 1}. ${before.length} → ${after.length} lines.`,
    );
  }

  function download() {
    if (!current || current.text !== current.draft) return;
    const url = URL.createObjectURL(new Blob([current.text], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a");
    const stem =
      current.name
        .replace(/\.txt$/i, "")
        .replace(/[^\p{L}\p{N}._-]+/gu, "_")
        .slice(0, 120) || "document";
    link.href = url;
    link.download = `${stem}-r${current.revision}.txt`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    appendEntry(
      current,
      "Export requested",
      `Requested a copy of revision ${current.revision} as ${link.download}.`,
    );
  }

  return {
    get all() {
      return files;
    },
    get current() {
      return current;
    },
    get notice() {
      return notice;
    },
    select(id: number) {
      selected = id;
    },
    open,
    save,
    download,
  };
}
