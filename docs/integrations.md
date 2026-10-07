# Integracje i wymagany dostęp

Stan dokumentacji i przypiętych źródeł sprawdzony 7 października 2026 r.

| Element | Przypięta wersja | Rola i stan |
|---|---|---|
| HyperFrames | npm 0.8.139, upstream e6daed3 | Lokalny rendering przetestowany. |
| OpenMontage | 9327439 | Narzędzia zaimportowane; rzeczywiste cięcie przetestowane. Agentowy proces produkcji wymaga próby na temacie. |
| video-use | b877063 | Skill dla własnych nagrań; brak materiału użytkownika do testu. |
| HeyGen CLI / skills | CLI v0.9.0 / skills 1bd5e4d | CLI i schemat photo sprawdzone offline; awatar wymaga zdjęcia i konta. |
| SadTalker | cd4c046 | Domyślny lokalny backend, CUDA na RTX/WSL2 lub CPU na Macu. Oddzielny Python 3.10. |
| InfiniteTalk | 50aa0a9 | Opcjonalny lokalny backend NVIDIA/CUDA; profil 480p/offload wymaga testu na PC. |
| DeepSeek | API chat/completions | Propozycje scenariusza z manifestu. Mock HTTP; konto wymaga klucza. |
| Short form / captions | 2a77533 | Skille krótkiego formatu, napisów i lower thirds. |
| Remotion | skills 4733526 | Opcjonalne alternatywne instrukcje; silnik Remotion nie jest instalowany. |
| Postiz | aktualny public/v1 | Adapter szkiców i statystyk; mock HTTP, bez testu konta. |
| OpenCreator | rozpoznano v3.2.5 | Opcjonalny panel; nie zainstalowany. Digital Avatar i Auto Clips są opisane jako in development. |

## Klucze

W cloud wpisz wartości w ustawieniach środowiska. Na własnym komputerze
możesz użyć ignorowanego `.env` na podstawie `.env.example`. CLI i panel
ładują ten plik bez nadpisywania eksportowanych zmiennych. Nie wysyłaj kluczy
w rozmowie ani nie commituj `.env`. Program sprawdza obecność, nie drukuje wartości.

| Zmienna | Co odblokowuje | Docelowy host |
|---|---|---|
| TAVILY_API_KEY | Wyszukiwanie aktualnych tematów i kandydatów na źródła | api.tavily.com |
| DEEPSEEK_API_KEY | Opcjonalne propozycje scenariusza na podstawie źródeł | api.deepseek.com |
| HEYGEN_API_KEY | Opcjonalne zdjęcie → awatar; lokalne modele nie potrzebują go | api.heygen.com |
| POSTIZ_API_KEY | Podłączone kanały, upload, szkice i statystyki | api.postiz.com |
| PEXELS_API_KEY | Opcjonalne wyszukiwanie B-roll | api.pexels.com |

Codex jest już zalogowany przez środowisko. Nie wymaga osobnego klucza OpenAI
do tego wariantu procesu. Brak Tavily można częściowo zastąpić RSS i URL,
ale pełny research nowych tematów potrzebuje działającego wyszukiwania.

## Awatar i głos

Pierwszy wariant to lokalny SadTalker; InfiniteTalk jest opcją dla NVIDIA.
Instrukcje WSL2/RTX i Maca: [local-avatars.md](local-avatars.md).
Modele mają oddzielne środowiska i `avatar-doctor`. Wybór lokalnego modelu
nie uruchamia HeyGen automatycznie, także po błędzie.

`studio avatar-photo` przyjmuje lokalny JPEG/PNG (≥512×512) lub publiczny URL.
Lokalny plik trafia do oficjalnego CLI przez stdin jako base64, bez publicznego
hostowania zdjęcia. Funkcja jest asynchroniczna: status i tożsamość zapisuje się
po zakończeniu przez workflow `heygen-avatar`. Utworzenie twarzy i wybór głosu
to osobne czynności. Naturalność polskiej mowy, podobieństwo oraz lip sync
wymagają krótkiego testu na koncie użytkownika.
OpenMontage `heygen_avatar` jest adapterem beta dla istniejących looków;
silnik Avatar V wymaga kwalifikującego się digital twin. Photo nie daje
automatycznie dostępu do każdego silnika. Wybieraj silnik zgodny z kontem.

## Materiały i sieć

Przeglądarka jest lokalnym Chromium. Przy capture dokument i zasoby są pobierane
przez httpx z weryfikacją TLS i proxy środowiska, a potem renderowane przy
oryginalnym URL w Chromium. Pozwala to użyć zaufanego proxy bez wyłączania
walidacji certyfikatów w przeglądarce. `capture.json` zapisuje brakujące domeny
zasobów; częściowo wczytana strona nie może automatycznie uchodzić za dobry screen.
Sprawdź pełny kontekst i wycinek przed użyciem. Ponowny screen po przyznaniu
dostępu jest potrzebny, gdy brakował CSS, obrazu lub właściwej treści.

yt-dlp i Playwright nie gwarantują dostępu do każdego filmu i artykułu.
Dodawaj konkretne domeny źródeł i CDN w ustawieniach sieci, gdy stanowią
rzeczywiście potrzebne materiały. Nie obchodź logowania, paywalla ani DRM.
W Wikimedia/Pexels wybieraj konkretny plik, autora i warunki użycia.

## Postiz

Domyślny host według aktualnej dokumentacji: `https://api.postiz.com/public/v1/`.
Nagłówek: `Authorization: <klucz>` bez dopisywania `Bearer`.
Proces: lista kanałów → upload pliku → `POST /posts` z `type: draft`.
Szkic można przejrzeć i zaplanować w Postiz. Płatne akcje i publikacje na
realnych kontach nie zostały wykonane w tej konfiguracji.
Metryki zależą od platformy i konta; nie zakładaj uniwersalnej krzywej retencji.
Własny hosting Postiz oznacza osobne usługi i konfigurację OAuth; nie jest
potrzebny do pierwszego testu wariantu Cloud.

## Harmonogram bez n8n

`studio discover` zapisuje research w `data/inbox`. Można go uruchamiać przez
cron/systemd timer lub harmonogram OpenCreator na stale działającym serwerze.
W tym środowisku wykonuje się na żądanie, a procesy nie przetrwają uśpienia
ani odtworzenia maszyny. Nie traktuj bieżącej sesji jako monitora newsów 24/7.

## Źródła instrukcji

- [HyperFrames](https://github.com/heygen-com/hyperframes)
- [OpenMontage](https://github.com/calesthio/OpenMontage)
- [video-use](https://github.com/browser-use/video-use)
- [HeyGen CLI](https://github.com/heygen-com/heygen-cli) i [skille](https://github.com/heygen-com/skills)
- [Postiz API](https://docs.postiz.com/public-api/introduction)
- [Short form skills](https://github.com/iart-ai/tiktok-video-skills)
- [OpenCreator](https://github.com/krillinai/OpenCreator)

OpenMontage i Postiz są AGPL, HyperFrames i HeyGen CLI Apache-2.0, video-use MIT.
Remotion ma własne warunki licencyjne. Nie włączono domyślnie narzędzi z
licencją Noncommercial. Stosy GPU są opcjonalne i instalowane oddzielnie.
