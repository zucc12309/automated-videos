# GTA VI police system · evidence report (draft, 2026-10-16)

Status (update 2): pages for SVG, Beebom, Sole Retriever, Postmode, GTAVice and Yahoo were fetched and read directly (`data/gta6/pages/`, git-ignored). IGN itself is not reachable; its interview is quoted through SVG. The official video is on Rockstar's own channel (youtube.com/watch?v=tJbzMqJGH4k, "Grand Theft Auto VI: An Extended Look", 26:49, channel UC6VcWc1rAoWdBCM0JxrRQ3A), but it is age-restricted and YouTube asks this server to sign in, so the footage is not yet in hand.

Original status: **research from search-engine summaries only.** The build environment's network policy blocks rockstargames.com, YouTube, IGN and the coverage sites, so no article or video was opened directly and **no timestamp below has been checked against the footage**. Every row must be re-verified against the official video before publishing.

## Primary source (official)

- **"Grand Theft Auto VI: An Extended Look"** (about 26 min). Premiered on Netflix on 27 Aug 2026, 3 pm ET, then on Rockstar's YouTube channel about six hours later (PC Gamer, Kotaku, Screen Rant).
- **Developer commentary:** Rockstar North co-head Rob Nelson in press previews and an IGN interview, quoted secondhand via SVG, GTAVice and Yahoo.
- **Excluded:** the unauthorised recording of 8 Oct 2026 (Rockstar has not authenticated it) and the 2022 leak. Neither is used, quoted or shown.

## Evidence table

| # | Claim | Source | Timestamp | Confidence | Allowed wording |
|---|---|---|---|---|---|
| 1 | The wanted meter goes up to six stars | Extended Look (reported by Red Bull, Beebom, allthings.how) | to verify | OBSERVED (multiple outlets, not checked by us) | "six stars are back" |
| 2 | Red icons near the stars stand for **face, clothing, vehicle** (SVG also reports a two-person icon) | Extended Look HUD (SVG, Red Bull, Beebom) | to verify | OBSERVED, meanings partly CONFIRMED by #4 | "icons for your face, your outfit and your car" (only after we see them) |
| 3 | After Jason and Lucia switch from a car to a van, **the car icon disappears** and police pass by without noticing them | Extended Look (Red Bull, Beebom) | to verify | OBSERVED | "swap the car, and the car icon disappears" |
| 4 | Police remember **what you are wearing**; change at a clothing store or from outfits in your personal vehicle's trunk | Rob Nelson to IGN: "[the cops] still know what I'm wearing, so I would need to go to a clothing store or call my personal vehicle, which has changes of outfits in the trunk" (via SVG) | n/a (interview) | CONFIRMED (developer, quoted secondhand) | "Rockstar says the cops remember your outfit" |
| 5 | A crime is reported only if **someone witnesses it or an alarm goes off** | Rob Nelson (via Yahoo) | n/a | CONFIRMED (developer, quoted secondhand) | "a witness or an alarm has to report it" |
| 6 | Destroying CCTV footage stops police learning your appearance | a guide quoting previews | — | SPECULATIVE until a primary source is found | do not state as fact |
| 7 | Hollow stars mean "crime known, no description" | one fan-adjacent source | — | SPECULATIVE | do not use |
| 8 | A mask hides your face from witnesses | Tech2Geek says "confirmed"; no primary quote found | — | SPECULATIVE | do not use |
| 9 | `faceKnown`, `vehicleKnown`, `lastSeen` variables | ours | — | INFERRED (illustration) | labelled "CONCEPTUAL SIMULATION · not Rockstar's code" |

## What this changes in the brief's script

The evidence is **stronger than the brief assumed** for clothing and vehicles (#3 and #4 are shown or stated), and **weaker** for "a camera catches your car" (#6). Proposed narration (about 85 words), every line tied to a row:

> GTA 6 tracks more than just your wanted level. (#1, #2)
> Look under the stars. (#2)
> Those icons show what the police know about you: your face, your outfit, your car. (#2, #4)
> Here's the trick. A crime only counts if a witness or an alarm reports it. (#5)
> And when the cops lose track of your car, its icon disappears. (#3)
> In code, that's more than one wanted-level number. It's stored information about you. (#9, labelled)
> Rockstar says the cops remember your outfit, so you change clothes. (#4)
> Swap the car, change the clothes, and break the connection.
> Would you want this system? Follow DevMimo for more game engineering.

Hook choice: **B** ("GTA 6 might track more than just your wanted level") is supported by #2 and #3. If we verify those, we can drop "might". A is vaguer; C claims CCTV/evidence (#6), which isn't supported.

## Sources (search results; pages not opened)

- PC Gamer, reveal timing: https://www.pcgamer.com/games/grand-theft-auto/how-to-watch-gta-6-gameplay-reveal-time-netflix-youtube/
- Kotaku, reveal: https://kotaku.com/grand-theft-auto-6-looks-incredible-in-netflixs-big-gameplay-reveal-2000728933
- Screen Rant: https://screenrant.com/gta-6-stream-extended-look-official-gameplay-reveal/
- SVG, wanted system and Nelson quote: https://www.svg.com/2246084/gta-6-wanted-system-explained-rockstar/
- GTAVice, IGN interview summary: https://www.gtavice.net/news/igns-full-gta-6-interview-reveals-even-more-gameplay-details
- Yahoo, wanted level explained: https://tech.yahoo.com/gaming/articles/gta-6-wanted-level-explained-170115765.html
- Red Bull, Extended Look details: https://www.redbull.com/us-en/gta-6-extended-look-everything-revealed
- Beebom, wanted system: https://beebom.com/gta-6-wanted-system-explained/
- Tech2Geek: https://www.tech2geek.net/gta-6-police-explained-how-the-new-wanted-system-works/


## Verified on the fetched pages (update 2)

- **SVG** (Joe Roberts, Aug 2026): "IGN was given some insight into the "GTA 6" Wanted system by Rockstar North co-head Rob Nelson". Nelson: "Changing your hair will change your appearance … But the police will still know what you are wearing". "several red icons which now sit below the star-level on the HUD and inform players what information the police have." The Extended Look "did reveal these new icons, which include avatars of two people, a single person, a clothes hanger, and a car." According to IGN, the single person means the cops know your physical description, the hanger what you're wearing, and the camera that police have CCTV footage. Nelson to IGN: "The Wanted system in 'GTA 6' requires that someone witness the crime, or an alarm needs to be set off for it to be reported to the law." There is also a "hollow" star (police know a crime happened but have no information), and a wanted area where the level comes back if you return.
- **Postmode** (Jordan Oloman, 28 Aug 2026): IGN's Matt Purslow lists three icons under the wanted level (silhouette, clothes hanger, camera). "There are even more in the Extended Look, bringing the total to six, including a silhouette of a duo, a car icon, and a weapon icon."
- **Sole Retriever**: during a robbery in the Extended Look, "in the corner … there is a camera icon, a clothes hanger, a weapon, and two circles with a silhouette of a person"; stars change colour; a second sequence has Lucia leaving the robbed store.
- **Beebom**: Nelson "confirms that police can know what a character looks like, what they are wearing, what vehicle they are using, and whether Jason and Lucia are together"; "red icons underneath the wanted stars".
- **Engadget** (fetched): "six stars in the upper-right of the screen" during the chase.

Upgrades in confidence: #2 icons → OBSERVED in the official video by several outlets, with meanings CONFIRMED by Nelson via IGN for appearance, clothing, CCTV and duo; #6 CCTV → CONFIRMED icon meaning (via IGN); #7 hollow stars → CONFIRMED via IGN (SVG). Masks stay SPECULATIVE (Beebom lists them, with no quote).
