# Rewriting flagged passages in a human voice

Read this when the scan has `ai_style` findings or the user asks for a human-sounding rewrite. The rules are adapted from the humanizer skill by blader (MIT), which builds on Wikipedia's "Signs of AI writing".

## Why these patterns exist

A language model picks the choice that fits the widest range of readers. A person writes for one reader and one subject, so their choices are uneven and specific. Every pattern below is a default choice. Replace it with the specific claim.

## Procedure

1. Group `ai_style` findings by paragraph. Done when each flagged paragraph has its findings listed once.
2. Rewrite each flagged paragraph on the clean copy. Keep every fact, number, name, date, quotation and citation exactly as written. Add nothing the source does not say. When a sentence needs a detail you lack, write a plainer sentence or ask.
3. Show the user before and after for each paragraph. Apply after approval. Done when every flagged paragraph is rewritten or the user chose to keep it.
4. Re-run `scan`. Done when no `ai_style` finding remains on rewritten paragraphs.

## Voice

- When the user gives a writing sample, match its sentence length, punctuation and transitions. The sample overrides every rule below, dashes included.
- Without a sample, academic and technical text stays neutral and plain. Essays and opinion keep the writer's stance and uncertainty.
- Arabic text gets native Arabic phrasing. Do not translate the English fixes word for word.
- Leave quotations, titles, proper names and fixed legal wording untouched.

## Patterns the scan reports

| Finding | What it is | Fix |
|---|---|---|
| not-X-but-Y contrast | The negative half names something nobody claimed, so the positive half sounds bigger. Arabic form: ليس ... بل ... | State the point directly. Keep a contrast only when it corrects a belief the reader holds. |
| stock closer | A one-line paragraph restating the one before ("That is the real win.") | Cut it, or merge a real new fact into the paragraph. |
| deep-sounding saying | "at its core", "the real question is", حجر الزاوية, بيت القصيد | Replace with the specific claim. |
| staged run-up | "Let's dive in", "Here's the thing", دعونا نغوص | Delete the run-up and start with the point. |
| argument with no one | "I'm not saying", "To be clear", a rejected option nobody proposed | Delete, or state the real claim. |
| dash used as connector | Em dash or spaced dash joining clauses | Use a period, comma, colon or parentheses, or rewrite the sentence. |
| inflated significance or sales language | "stands as", "nestled", "continues to thrive", "the future looks bright" | Keep the fact, drop the dressing, end on the last concrete fact. |
| stock AI word, several stock words in one paragraph | delve, tapestry, pivotal, underscore, showcase, intricate, vibrant; or crucial, enhance, robust, landscape together | Use the plain word the writer would say. |
| -ing rider on a plain fact | ", highlighting the importance of ..." | Keep the fact. Keep the rider only when the source supports it. |
| unnamed authority | "experts argue", "industry reports" | Name the source and what it said, or cut the claim. |
| knowledge-limit hedge | "based on available information", "maintains a low profile" | State what the sources do not show, or delete. |
| emoji or arrow decoration | Pictographs and arrows in a formal file | Remove. |
| bold label before a colon repeated down a list | Every list item opens with a bold label | Turn the list into prose when the labels carry no information. |

## Patterns the scan cannot see

Check these during the rewrite:

- Forced triads: three parallel items where the meaning has two or four. Merge, develop the strongest, or vary the structure.
- Repeated sentence openings: three sentences in a row starting with the same word. Merge them or change the subject.
- Stacked qualifiers: "could potentially arguably". Keep one qualifier, and only where the source supports doubt.
- Hidden actor: passive voice or a missing subject where the actor matters.
- Decorated headings: title case on every word, emojis, a heading repeated by the first sentence under it.
- Every paragraph ending on the same kind of moral.

## Guard rails

- A pattern is a default someone may have chosen on purpose. Several together are the signal, and one lone sighting is a prompt to read the sentence, not an order to change it.
- Keep specific, odd, human details: a real place, an aside, an honest mixed feeling.
- Removing patterns is half the job. The result must still sound like a person who has something to say.
