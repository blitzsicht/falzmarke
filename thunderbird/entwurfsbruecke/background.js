// Startet die Brücke, sobald Thunderbird das Add-on lädt.
browser.entwurfsbruecke.starten().then(
  (stand) => console.log("falzmarke Entwurfsbrücke", JSON.stringify(stand)),
  (fehler) => console.error("falzmarke Entwurfsbrücke", fehler)
);
