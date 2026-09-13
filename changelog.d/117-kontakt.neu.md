**Die E-Rechnung trägt Ansprechpartner, Konto und elektronische Adresse.** Die eingebettete XML
schreibt jetzt den Kontakt des Ausstellers aus dem Informationsblock (dieselbe Person wie im PDF),
einen Zahlungsweg per Überweisung aus dem neuen Profilfeld `rechnung.bank` und die elektronische
Adresse aus `rechnung.adresse`. `lint` prüft Form und Prüfziffer der IBAN und warnt, wenn sie
nicht auch in der Fußzeile steht. Unter EN 16931 ist alles freiwillig; XRechnung (#117) verlangt
alle drei Angaben. Außerdem liest die Zeile „E-Rechnung“ im Messbericht Beilage, Guideline-ID,
Profil und Factur-X-Fassung jetzt aus der fertigen Datei — vorher stammten sie aus Konstanten,
und die Zeile konnte nie rot werden.
