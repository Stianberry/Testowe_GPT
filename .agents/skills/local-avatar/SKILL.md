---
name: local-avatar
description: Generate short avatar clips from an operator-provided photo and audio using SadTalker or InfiniteTalk in the local video studio.
---

Przeczytaj `docs/local-avatars.md` i `AGENTS.md`. Domyślnie SadTalker;
`studio avatar-doctor` sprawdza środowisko przed `studio avatar-local`.
Na RTX/WSL2 wybierz CUDA, na Macu SadTalker CPU. InfiniteTalk wymaga CUDA.
Pierwszy test 3–5 s, nie cała narracja. Nie zmieniaj przypiętych upstreamów.
Nie klonuj głosu bez nagrania i nie zastępuj twarzy użytkownika losową postacią.
Po renderze obejrzyj twarz i odsłuchaj polską mowę. Materiał nie jest
automatycznie zatwierdzony. Nie wywołuj HeyGen jako fallback po błędzie.
Jeśli brak GPU, wag, zdjęcia lub audio, zapisz konkretny brak i wykonaj
niezależne etapy researchu i montażu.
