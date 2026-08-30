# Externer Prüfkatalog, gegen den Bestand gemessen

**Stand: 30.08.2026 · falzmarke v0.8.2 · Commit `71bfaaa`**

Ein von außen erstellter Katalog („`blitzsicht/falzmarke` auf 10/10 Engineering-Reife bringen")
nennt 24 Forderungen. Dieses Dokument hält fest, welche davon bereits erfüllt sind, welche
teilweise, und welche echte Arbeit bedeuten — **mit Fundstelle statt mit Einschätzung.**

Der Katalog wurde ohne Kenntnis des Repositoriums geschrieben. Das ist kein Vorwurf, aber es
erklärt seinen Hauptmangel: Er fordert an mehreren Stellen als P0, was seit Monaten grün in der
CI läuft. Ein Katalog, der nicht misst, rät — und genau das verbietet er in seinem eigenen
Abschnitt 0.1.

Gemessen wurde am 30.08.2026 durch Lektüre der genannten Dateien, nicht durch Textsuche.
Wo eine Aussage nicht überprüft werden konnte, steht das als eigener Zustand da.

---

## Zusammenfassung

| Forderung | Urteil | Arbeit? |
|---|---|---|
| Abschnitt 2 Norm-Beweiskette maschinenlesbar | teilweise | Formalia |
| Abschnitt 3 Dependency Single Source of Truth | **offen** | **ja** |
| Abschnitt 4 CI als Quality Gate | teilweise | Konfiguration |
| Abschnitt 5 Supply-Chain (veraPDF ungeprüft) | **teilweise** | **ja** |
| Abschnitt 6 Architektur modularisieren | Bestand unter anderen Namen | nein |
| Abschnitt 7 Typsicherheit (ruff/mypy in CI) | teilweise | ja, klein |
| Abschnitt 8 API und Datenvertrag | schon da | Notiz |
| Abschnitt 10 Security adversarial | teilweise | ja |
| Abschnitt 11 Property-based Testing | offen | ja |
| Abschnitt 12 Fehlerdiagnostik mit IDs | teilweise | ja |
| Abschnitt 13 Doku trennen | teilweise | Geschmack |
| Abschnitt 0.2 Gegenproben-Pflicht | teilweise | **ja** |

---

## Was echte Arbeit bedeutet

### 1. `pillow` fehlt in zwei von drei Abhängigkeitslisten (Abschnitt 3)

`pyproject.toml:37` führt `pillow>=10` als Runtime-Abhängigkeit — seit Issue #154 wird es direkt
benutzt. In `skill/requirements.txt` (5 Zeilen) und im `DEPS`-Dict in
`skill/scripts/bootstrap.py:32-38` steht es **nicht**.

Die CI wird trotzdem grün, weil `pdfplumber` Pillow transitiv mitbringt. Das ist genau der
Zustand, den der Katalog verbietet: „Keine Runtime-Abhängigkeit darf nur zufällig über ein
anderes Paket vorhanden sein."

Ein Konsistenztest existiert nicht. `tests/test_vendor.py:95-98` prüft nur, dass `pdfplumber`
und `pypdf` *genannt* sind — kein Listenvergleich.

**Zu tun:** Ein Test, der die drei Listen gegeneinander hält. Fünfzehn Zeilen, schließt die
ganze Fehlerklasse. Gegenprobe: eine Abhängigkeit aus einer Liste entfernen, Test muss rot
werden.

### 2. veraPDF wird ungeprüft heruntergeladen und ausgeführt (Abschnitt 5)

`.github/workflows/ci.yml:215-218` lädt `https://software.verapdf.org/releases/verapdf-installer.zip`
— Latest-URL ohne feste Version, Entpacken über den Glob `verapdf-greenfield-*`, **kein SHA-256,
keine Verifikation**, sofortige Ausführung.

Das ist die einzige Blind-Ausführung im Repository. Alle `uses:`-Einträge sind auf 40-stellige
Commit-SHAs gepinnt, mit einer dokumentiert begründeten Ausnahme
(`pypa/gh-action-pypi-publish@v1.14.2`, `release.yml:188` — das Docker-Image existiert unter dem
Commit-SHA nicht). Dependabot läuft monatlich für Actions und pip.

Bitter ist die Rolle des Werkzeugs: veraPDF ist der **unabhängige** Prüfer, auf den sich die
PDF/A- und PDF/UA-Behauptungen stützen. Ein Beleg, dessen Herkunft ungeprüft ist, trägt weniger,
als er zu tragen scheint.

**Zu tun:** Version und Digest festnageln, Digest vor der Ausführung prüfen.

### 3. Die Pflicht-Checks werden aus einem Laufzeit-Zustand abgeleitet (Abschnitt 4)

`scripts/repo-einstellungen.sh:38` ermittelt die Pflicht-Checks des Rulesets aus dem **letzten
CI-Lauf** und übernimmt nur Jobs mit `conclusion=="success"`.

Das ist am 30.08.2026 nachweislich schiefgegangen: Beim Scharfstellen des Rulesets lief die CI
auf `main` noch. `frischklon` hat `needs: tests` und war nicht fertig, also fiel er aus der
Liste — das Ruleset verlor einen Pflicht-Check, den es vorher hatte. Aufgefallen ist es erst
durch diese Messung.

Eine Repository-Konfiguration, die aus einem Laufzeit-Zufall abgeleitet wird, kommt bei jedem
Lauf anders heraus. Der Kommentar über der Stelle begründet die Ableitung damit, dass ein Check,
den es nie gab, den Branch dauerhaft sperren würde — das Anliegen ist richtig, die Quelle falsch
gewählt: Die Jobnamen stehen in `.github/workflows/ci.yml`.

**Behoben am 30.08.2026** durch direktes Setzen des Rulesets auf sechs Pflicht-Checks
(`tests` ×3, `frischklon`, `skill-paket`, `PDF-Konformität (veraPDF, fremdes Werkzeug)`).
Die Ursache im Skript steht noch offen.

Nebenbefund zur Namensfalle: Der Job heißt in der Check-Liste
`PDF-Konformität (veraPDF, fremdes Werkzeug)`, nicht `pdf-konformitaet`. Ein geratener Context
hätte jeden Pull Request dauerhaft blockiert.

### 4. Die Lint-Regeln haben keine Gegenproben (Abschnitt 0.2)

`tests/test_gegenbeweis.py` enthält 17 Testfunktionen, davon 3 Kontrollproben und rund 13 echte
Sabotagen. Sie decken **Geometrie und Emitter** ab: Falzmarke, Lochmarke, Betreff, Anschrift,
Unterrand, Satzspiegel, Infoblock, PDF/UA-Alternativtext, vier HTML-Sabotagen. Dazu ein
Meta-Test (Z. 327-345), der prüft, dass ein nicht auswertender Emitter auffiele.

Dem stehen rund vier Dutzend `fehler()`- und `warnung()`-Aufrufstellen allein in `lint.py`
gegenüber (`grep -c` zählt 41 bzw. 17, die Definitionszeilen eingerechnet — die genaue Zahl ist
für die Aussage unerheblich, die Größenordnung nicht).
Die Schreibregeln (Anrede, Gruß, Datum, Telefon, IBAN) haben Positiv- und Negativtests in
`test_lint.py`, aber keine Sabotage im Sinne des Katalogs: Es ist nicht belegt, dass die
*Prüfung* anschlägt, wenn die *Regel* verletzt wird — nur, dass sie bei präparierter Eingabe
meldet.

Das ist die größte echte Lücke, die die Messung gefunden hat, und sie liegt genau im
Selbstverständnis des Projekts.

### 5. Zwei uneinheitliche Diagnose-Formate (Abschnitt 12)

`--json` gibt es für `lint` und `verify` (`cli.py:808, 1092, 1114`, dokumentiert in
`docs/cli.md:5-9,126`) — aber die beiden Berichte haben verschiedene Formen:

| | Lint (`lint.py:317-321`) | Geometrie (`geometrie.py:144-150`) |
|---|---|---|
| stabile ID | `regel` — gepunktet, z. B. `geometrie.form_b.briefkopf` | keine, nur Anzeigename |
| Ist / Soll / Toleranz | fehlt | vorhanden |
| Quelle | fehlt | fehlt |
| nächster Schritt | `korrektur` | `ursache` |

Der Katalog fordert `FM-GEO-001`-Kennungen. Die gepunkteten Regelnamen leisten dasselbe und sind
sprechender; was wirklich fehlt, ist die **Vereinheitlichung** und die Angabe der Quelle im
Befund.

### 6. Kein Linting und keine Typprüfung in der CI (Abschnitt 7)

`pyproject.toml:90-92` konfiguriert `ruff` nur rudimentär (`line-length`, `target-version`, keine
Regelauswahl). Weder ruff noch mypy/pyright laufen in einem CI-Job — `ci.yml` vollständig
gelesen, kein Schritt vorhanden.

Dataclasses sind dagegen längst Standard (allein `baum.py` 12× `@dataclass(frozen=True)`),
Zustände sind validierte String-Konstanten mit harter Prüfung (`FEHLER`/`WARNUNG` `lint.py:25`,
`FASSUNGEN = ("1.0", "1.1")` `markdown.py:33`). Enums fehlen — das ist Geschmack, kein Mangel.

### 7. Kein Property-based Testing, Angriffsprotokoll veraltet (Abschnitt 10, Abschnitt 11)

Hypothesis ist nirgends eingebunden. Die Sicherheitslage ist dagegen substanziell:
`docs/angriff-2026-08-25.md` ist ein systematisches Angriffsprotokoll **einschließlich der
ergebnislosen Versuche** — drei Funde, behoben, darunter ein Pfad-Traversal über das Profil-Logo.
`tests/test_profilgrenze.py` prüft die Profilgrenze samt Symlinks, YAML wird durchgängig mit
`safe_load` gelesen, die Typst-Maskierung ist getestet (`test_wortlaut.py:148`).

Zwei Lücken: Für **E-Mail-Header-Injection** wurde kein Test gefunden (`eml.py` nutzt
`email.headerregistry` — ob das genügt: **nicht geprüft**). Und das Protokoll ist Stand v0.3.x,
während v0.8.2 läuft: `eml`, `serie` und `dienst` sind seither dazugekommen und nie adversarial
geprüft worden.

---

## Was der Katalog fordert und schon dasteht

### Abschnitt 6 Architektur — der teuerste Vorschlag, ohne Gewinn

Der Katalog schlägt vor, `skill/falzmarke/` in `core/`, `letter/`, `email/`, `pdf/`,
`integrations/`, `cli/` umzubauen. Die 17 Module sind bereits nach Verantwortung geschnitten und
in `docs/architecture.md:1-15` genau so dokumentiert: `lint` (Prüfung und Datenvertrag),
`markdown` (Dialekt), `emit`/`emit_html`/`emit_text` (Ausgabe), `geometrie` (Messung am PDF),
`eml`/`pruefung_eml` (E-Mail), `dienst` (MCP).

Der Vorschlag ist im Kern der Bestand unter englischen Namen in Unterpaketen. Die Kosten sind
real: `dienst.py:36` und `skill/scripts/falzmarke.py:15` importieren aus `falzmarke.cli`,
`pyproject.toml:78-79` listet die Pakete explizit, das Paket liegt öffentlich auf PyPI, und
englische Modulnamen widersprächen der Repo-Regel, dass alles auf Deutsch geschrieben wird.

Berechtigt ist genau ein Teil davon: `cli.py` (1485 Zeilen) mischt Profilauflösung
(`lade_profil:190`), Datenaufbau (`baue_daten:231`), Render-Pipeline (`rendere:573`),
E-Mail-Setzung (`setze_email:936`) und 13 Befehls-Handler. Das Herausziehen von Profil- und
Datenaufbau wäre eine echte Verbesserung — das große Schema bringt nichts, was die jetzige
Schneidung nicht leistet.

### Abschnitt 2 Norm-Beweiskette — vorhanden, anders geschnitten

`skill/falzmarke/regeln/din5008.yaml` führt 45 Regeln mit `id`, `titel`, `herkunft`, `quellen`,
`wirkung`, `belegt_durch`, `bemerkung`; `quellen.yaml` ergänzt je Quelle `art`, `url`, `gruppe`,
`zaehlt`, `abgerufen`.

Entscheidend ist, dass der Belegstatus **wirkt**, und zwar über zwei Achsen (`deckel()`,
`regeln/__init__.py:339-356`): `herkunft` deckelt nach Belegstärke — nur `mehrfach_bestaetigt`,
`werkzeug` und `primaerquelle` dürfen Fehler sein —, `ebene` zusätzlich nach Gegenstand (ADR
0035). Eine Regel aus Primärquellen, die die Ebene `recht` trägt, wird trotzdem auf Warnung
gedeckelt. Beide Achsen können nur herabstufen, nie herauf. Einzeln Belegtes wird zur Warnung mit
Quellenhinweis, Ungeklärtes gar nicht gemeldet. Angewendet wird das in
`lint.py:341-350` — *jeder* `Bericht.fehler()` läuft dort durch. `tests/test_quellenlage.py`
erzwingt es mit rund 30 Tests samt eigenen Gegenproben (Z. 131, 192, 316).

Als eigene Felder fehlen: `wert`, `einheit`, `toleranz`, `fundstelle`, `normfassung`,
`berichtigung`, `kategorie`. Die Werte stecken im Freitext des `titel`, die Toleranzen in
`geometrie.py`. Das ist Formalia — die Mechanik dahinter ist stärker als das, was der Katalog
beschreibt.

### Abschnitt 8 Datenvertrag — steht

`dialekt:` wird real ausgewertet: `pruefe_fassung` (`markdown.py:590-604`) lehnt unbekannte
Fassungen mit Fehler ab, die Fassung steuert Grenzen (`MAX_LISTENTIEFE[lage.dialekt]`,
`markdown.py:425`), und der Default bleibt bewusst 1.0, „damit ein alter Brief sein Aussehen
nicht ändert" (`markdown.py:35-37`). Exit-Codes 0–4 sind in `docs/cli.md:116-124` dokumentiert.
Neun ADRs liegen in `docs/entscheidungen/`.

Es fehlt eine geschriebene Deprecation-Regel. Gelebt wird sie über den Fassungsmechanismus.

### Abschnitt 13 Dokumentation — vorhanden, andere Namen

`docs/architecture.md`, `docs/recht.md` (= legal), `SECURITY.md`, sowie
`normabgleich-pruefliste.md`, `quellenunabhaengigkeit-2026-08-27.md` und `angriff-2026-08-25.md`
als Beleg-Dokumente. Es fehlen `QUALITY.md`, `verification.md`, `standards.md`, `evidence.md`
unter diesen Namen.

Wichtiger: README-Behauptungen sind **bereits testgeprüft** — `tests/test_textkanon.py` hält die
Zusage-Sätze fest und verbietet ungedeckte Konformitätsbehauptungen, ein CI-Schritt führt die
Befehle aus der README wirklich aus, `test_installationswege.py` und `test_changelog.py` sichern
den Rest. Die README ist mit 532 Zeilen kein Zwei-Minuten-Dokument; das zu kürzen ist eine
Geschmacksfrage, kein Mangel.

### Abschnitt 15 Release Engineering — weitgehend erfüllt

`release.yml` hängt `falzmarke.skill`, `falzmarke-offline.skill` und je eine `.sha256` an
(Z. 74-82), erzeugt Attestation über `attest-build-provenance` (Z. 68), gleicht Tag gegen Version
ab und lässt `paket_pruefen.sh` vor dem Upload laufen. PyPI läuft über Trusted Publishing mit
OIDC. Das Ruleset `release-tags` blockt Löschen, Überschreiben und Verschieben von `v*`-Tags.

Zwei ehrliche Lücken: Das **Wheel** hängt nicht am GitHub-Release und trägt keine Attestation.
Und die Classifiers behaupten Python 3.11–3.13 (`pyproject.toml:20-22`), während die CI nur auf
3.12 läuft (`ci.yml:25`) — eine ungeprüfte Behauptung, also entweder Matrix erweitern oder
Classifier streichen.

---

## Der eine Punkt, den der Katalog nicht lösen kann

Der wichtigste offene Vorgang steht seit Langem im Repository: **#12 — Normabgleich gegen den
Originaltext der DIN 5008:2020-03** samt Berichtigung 1:2020-07.

Er ist durch keinen der 24 Abschnitte lösbar, weil er kein Engineering-Problem ist. Er braucht
ein gekauftes Normexemplar und jemanden, der Fundstellen überträgt. Solange er offen ist, sagt
das Projekt nicht „normgerecht" — so steht es in `CLAUDE.md`, festgehalten von
`tests/test_textkanon.py`.

Ein Katalog, der 24 Kapitel Arbeit vorschlägt und diesen Punkt in einem Nebensatz mitführt, setzt
die Gewichte falsch.

---

## Wozu keine Bewertungszahl gehört

Der Katalog schließt mit einer Zielmatrix, in der sich das Projekt in zwölf Kategorien selbst
Noten zwischen 9,5 und 10 geben soll.

Das ist dieselbe Art unbelegter Behauptung, die sein eigener Abschnitt 0.1 verbietet. Eine
Selbstbewertung ohne externen Maßstab ist keine Messung — sie ist eine Meinung mit Nachkommastelle.

Was dieses Projekt statt einer Note hat, ist besser: veraPDF als fremdes Werkzeug mit eigener
Gegenprobe, 17 Sabotagen gegen die eigenen Prüfmittel, eine Quellenlage, die einzeln belegte
Regeln zu Warnungen deckelt, und einen Satz in der README, der sagt, was noch nicht belegt ist.
