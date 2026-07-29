# Visual Asset Provenance

This register records source-provenance evidence for the repository's visual identity assets. On
2026-07-29, the operator explicitly attested that **every image currently in this repository was
AI-generated and that none was copied or downloaded from a third-party work**. The operator then
clarified that the two published identity assets—the Hexanomicon book and the clipped Lich
figure—were generated through Gemini, probably the Nano Banana image surface. Both files contain
embedded C2PA manifest text identifying them as “Created by Google Generative AI” and
`trainedAlgorithmicMedia`; this register observed that payload but has not independently
cryptographically validated its signature chain. The exact historical model recollection remains
qualified rather than being promoted into a reconstructed receipt. The earlier attestation
identifies the remaining four files as ChatGPT generations.

The attestation is evidence supplied by the operator, not a reconstructed generation receipt. The
exact historical prompts, product model/version, generation dates, product terms then in force,
and original generation records are unavailable unless separately recovered. A Git commit records
when a file entered this repository, not when or how it was generated.

| Asset | SHA-256 | First tracked | Published use | Rights evidence |
| :--- | :--- | :--- | :--- | :--- |
| `hexanomicon.png` | `560a27085c96f5ffbb828cb7f12fe2de8ec74de5277da7c0dbd253a0a73094f4` | `9d9ce07` (2025-12-11) | Documentation logo, favicon, and landing hero | **Operator-attested Gemini generation, probably Nano Banana; embedded Google Generative AI C2PA payload; no third-party copy/download.** Exact historical receipt unavailable. |
| `lich-phylactery-cliparted.png` | `7a500fbea91cb40ddd993662d3d05d32e4308835a60172db72ec2ddf7d81d49f` | `9d9ce07` (2025-12-11) | Repository README hero | **Operator-attested Gemini generation, probably Nano Banana; embedded Google Generative AI C2PA payload; no third-party copy/download.** Exact historical receipt unavailable. |
| `lich-phylactery.png` | `2084caf2b01e075ae5863968082084da0e481617b988506c00a6aca27cb9a174` | `348cf7c` (2025-12-16) | Not currently referenced by tracked pages | **Operator-attested ChatGPT generation; no third-party copy/download.** Historical generation receipt unavailable. |
| `lich.png` | `7143fc0384d631bce9dcc507921e18a22fd2d3864f5562e6f34a31c3c4eccd2a` | `348cf7c` (2025-12-16) | Not currently referenced by tracked pages | **Operator-attested ChatGPT generation; no third-party copy/download.** Historical generation receipt unavailable. |
| `phylactery-logo.png` | `f964af11bca8796088a6fff9ada2831868344b55ca37dd8f4a9eb2b0fce6799b` | `348cf7c` (2025-12-16) | Not currently referenced by tracked pages | **Operator-attested ChatGPT generation; no third-party copy/download.** Historical generation receipt unavailable. |
| `phylactery.png` | `e38427e87b56d472e002b33f5982a11ea2590d4f6595d693b70e6f013a69bda6` | `348cf7c` (2025-12-16) | Not currently referenced by tracked pages | **Operator-attested ChatGPT generation; no third-party copy/download.** Historical generation receipt unavailable. |

The files named `hexanomicon.png`, `lich-phylactery-cliparted.png`,
`lich-phylactery.png`, `lich.png`, and `phylactery.png` currently contain JPEG data despite their
extensions. That is a format-maintenance defect, not rights evidence.

## Remaining record and review boundaries

The missing historical generation material remains an evidence-quality gap. If recovered, the
register should add:

1. the exact historical prompt and referenced inputs;
2. the generation product, model/version, and surface;
3. the generation date and terms then in force;
4. the original generation receipt and material edit history; and
5. any later export/transcoding lineage tied to the final distributable hash.

Source provenance and visual similarity are separate questions. Manual visual review found no
obvious copied franchise insignia in the six files, but generated output can still resemble
protected expression, marks, characters, or trade dress. Neither the operator attestation nor
that visual review establishes copyrightability, ownership of exclusive rights, trademark
clearance, publicity clearance, model-training provenance, or freedom from contractual claims.
