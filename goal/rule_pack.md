# Rule pack**

## confusable_ocr_f_for_s
- **precondition**: `f` immediately followed by `t`/`l`/`k`/`p` inside a paragraph containing at least one thorn (`þ`), yogh (`ȝ`), long-s marker (`ſ`), or other clear archaic/early-print signal.
- **transform**: Replace `f` with `s` in those positions (`ft`→`st`, `fl`→`sl`, `fk`→`sk`, `fp`→`sp`), including common tokens such as `Coaft`→`Coast`, `Inftant`→`Instant`, `Succefs`→`Success`, `fubftitute`→`substitute`.
- **negative examples**: after, often, soft, lift, left, craft, profit, office, shift, safety, infant, inflation, softly, £5
- **priority**: high

## confusable_ocr_y_for_th
- **precondition**: `y` appearing where `þ` (thorn) is expected in Middle English text that already contains `þ`, `ȝ`, or unmistakably archaic orthography.
- **transform**: Replace `y` with `þ` when followed by `e`, `a`, `o`, or `u` in confirmed ME context.
- **negative examples**: the, they, your, year, young, yes, yesterday, yield, many, family
- **priority**: high

## confusable_ocr_l_for_1_digit
- **precondition**: Isolated `l` or `I` appearing inside dense numeric, tabular, or bibliographic contexts containing multiple digits, commas, dashes, semicolons, "n.", "pp.", currency, or superscripts.
- **transform**: Replace the isolated `l`/`I` with `1`.
- **negative examples**: Roman numerals (LI, LII, CL, XL), chemical formulas, "l." for line, pronoun "I", normal prose "l" or "I", law, lord
- **priority**: high

## confusable_ocr_1_for_l_in_text
- **precondition**: `1` immediately followed by a lowercase letter inside a paragraph that already contains at least one other OCR confusable or archaic glyph (`þ`, `ȝ`, `æ`, long-s markers, superscripts, or bibliographic notation).
- **transform**: Replace leading `1` with `l` (`1ondon`→`London`, `1aw`→`law`, `1ittle`→`little`).
- **negative examples**: Any token containing digits, decimals, commas, semicolons, dashes, Roman numerals, currency, dates, or bibliographic markers (`Route 1.`, `Vol. 1`, `1,000`, `$1.00`, `iv. 1`)
- **priority**: high

## confusable_ocr_y_for_v
- **precondition**: `y` immediately followed by a vowel forming a plausible medieval/Latin name or word inside a paragraph dense with medieval Latin markers (`Domino`, `Johanne`, `Radulpho`, `Henrico`, `Galfrido`, `filio`, `de`, `suo`).
- **transform**: Replace `y` with `v` in that token only (`yilla`→`villa`, `yobis`→`vobis`, `receiyed`/`receyved`→`received`).
- **negative examples**: eye, beyond, youth, your, yellow, yesterday, many, family, happy, modern English words
- **priority**: high

## confusable_ocr_i_for_l_in_names
- **precondition**: Isolated `i` appearing where `l` is expected inside dense clusters of medieval Latin personal or place names containing multiple capitalized name tokens (`Domino`, `Johanne`, `Radulpho`, `Henrico`, `Galfrido`, `filio`, `suo`).
- **transform**: Replace the isolated `i` with `l` in that name token only.
- **negative examples**: Roman numerals (`i.`, `ii.`, `iii.`), genuine Latin "i" in "filio", "suo", "ibi", modern words like "it", "is", "in"
- **priority**: high

## confusable_ocr_n_for_m
- **precondition**: `nm` appearing inside a paragraph that already contains at least one other clear OCR confusable (`f`/`s`, `y`/`þ`, medieval density, or dense proper-name/index lists).
- **transform**: Replace `nm` → `mm` (targeted only).
- **negative examples**: name, number, normal, income, unmade, nonmetal, nonmember
- **priority**: high

## confusable_ocr_minimu_n_for_m
- **precondition**: Terminal `n` appearing where `m` is expected at end of word (especially after `u` or `i`) in a paragraph containing other OCR artifacts (periods, broken words, or medieval signals).
- **transform**: `n` → `m` at word end when preceded by `u`/`i` and paragraph shows other damage.
- **negative examples**: in, on, than, been, given, taken, minion
- **priority**: high

## ligature_ocr_ae_oe_ct
- **precondition**: `æ`, `œ`, or split/misrecognized `ct` appearing in Latin, French, scholarly, or older English text that also contains other ligatures, diacritics, long-s substitutes, or archaic glyphs (`þ`, `ȝ`, superscripts).
- **transform**: Expand `æ`→`ae`, `œ`→`oe`; normalize `ct` ligature forms and `ct`→`st` confusions to standard spelling.
- **negative examples**: Modern brand names, IPA symbols, intentional Old English/Anglo-Saxon `æ`, clean modern prose without other archaic markers
- **priority**: med

## junk_repeated_glyph_run
- **precondition**: 4+ consecutive identical rare letters (`w y a e l i m n u v`) that do not form valid English words, known proper names, or standard onomatopoeia, or 3+ consecutive superscript markers (`¹¹`, `ªª`, `³³`, `ºº`), surrounded by spaces or punctuation.
- **transform**: Collapse runs longer than 3 identical glyphs (or repeated superscript junk) to a single instance or clean form.
- **negative examples**: www (URLs), aaaa (stylized onomatopoeia), intentional repetition in poetry/song, "llll" in dictionary notation, legitimate footnote sequences, single ordinals
- **priority**: med

## hyphen_line_join
- **precondition**: Hyphenated word break at end of line followed by lowercase continuation, or clear erroneous particle breaks (`realiz - ed`, `start - ed`, `misgiv - ings`), where the joined form is a known English word or standard verb in older printed prose.
- **transform**: Remove hyphen (and any extra whitespace) and join the two parts cleanly.
- **negative examples**: well-known, self-made, mother-in-law, editor-in-chief, intentional compound adjectives, scholarly hyphenation, dictionary-style breaks, poetic line breaks, bibliographic entries
- **priority**: med

## quote_ocr_broken_apostrophe
- **precondition**: `'` immediately followed by a space then a lowercase letter forming a common English contraction or possessive (`' s`, `' t`, `' ll`, `' re`, `' ve`, `' d`, `' m`).
- **transform**: Remove the intervening space (`' s` → `'s`, `' t` → `'t`, etc.).
- **negative examples**: Deliberate spacing in poetry, titles, opening single quotes, non-contraction uses, title-case possessives, foreign-language spacing
- **priority**: med

## junk_dot_run
- **precondition**: 2+ consecutive dots or mixed dot/hyphen runs (`..`, `...`, `.-.`, `..-`, `. . .`, `.Sec.`, `..Sec.`) appearing inside bibliographic/index-style lists or immediately after abbreviations.
- **transform**: Collapse runs of 2+ dots/hyphen-dot mixes to a single period or clean ellipsis (`...`).
- **negative examples**: Deliberate ellipses in modern prose, decimal points, version numbers, URLs, intentional bibliographic ranges
- **priority**: med
