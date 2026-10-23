// Pezzi comuni alla chat e alla pagina della query salvata: SQL colorato,
// tabella dei risultati, esportazione CSV. Richiede menu.js (el, icona, api).

function bloccoSql(sql) {
  const codice = el("code", { className: "language-sql", textContent: sql });
  if (window.hljs) hljs.highlightElement(codice);
  return el("pre", { className: "sql" }, codice);
}

function csv(r) {
  const cella = v => v === null ? "" : /[";\n]/.test(String(v)) ? `"${String(v).replaceAll('"', '""')}"` : String(v);
  return [r.colonne, ...r.righe].map(riga => riga.map(cella).join(";")).join("\r\n");
}

function scarica(nomeFile, testo) {
  // Il BOM fa aprire correttamente a Excel le lettere accentate
  const url = URL.createObjectURL(new Blob(["﻿" + testo], { type: "text/csv;charset=utf-8" }));
  const a = el("a", { href: url, download: nomeFile });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function mostraTabella(contenitore, r, nomeFile = "risultati.csv") {
  // Una colonna è numerica (allineata a destra) se tutti i suoi valori non nulli sono numeri
  const numerica = r.colonne.map((_, i) => r.righe.some(riga => riga[i] !== null)
    && r.righe.every(riga => riga[i] === null || typeof riga[i] === "number"));
  const tabella = el("table");
  tabella.append(el("thead", {}, el("tr", {}, ...r.colonne.map((c, i) => el("th", { textContent: c, className: numerica[i] ? "num" : "" })))));
  const corpo = el("tbody");
  for (const riga of r.righe) {
    corpo.append(el("tr", {}, ...riga.map((v, i) => v === null
      ? el("td", { className: "null" + (numerica[i] ? " num" : ""), textContent: "NULL" })
      : el("td", { textContent: String(v), className: numerica[i] ? "num" : "" }))));
  }
  tabella.append(corpo);
  const n = r.righe.length;
  const esporta = conIcona("button", { className: "bottone", type: "button" }, "scarica", "Scarica CSV");
  esporta.onclick = () => scarica(nomeFile, csv(r));
  contenitore.replaceChildren(
    el("div", { className: "tabella" }, tabella),
    el("div", { className: "piede-risultati" },
      el("span", { className: "nota", textContent: r.troncato ? `Mostrate le prime ${n} righe.` : `${n} ${n === 1 ? "riga" : "righe"}.` }),
      n ? esporta : ""));
}

// Pulsante "Esegui" che mostra nel contenitore i risultati della query, eseguita sulla connessione indicata
function bottoneEsegui(sql, risultati, nomeFile, connessioneId) {
  const esegui = conIcona("button", { className: "bottone primario", type: "button" }, "esegui", "Esegui");
  esegui.onclick = async () => {
    esegui.disabled = true;
    risultati.replaceChildren(el("p", { className: "nota", textContent: "Esecuzione…" }));
    try { mostraTabella(risultati, await api("/api/esegui", { connessione_id: connessioneId, sql }), nomeFile); }
    catch (e) { risultati.replaceChildren(el("p", { className: "errore", textContent: e.message })); }
    esegui.disabled = false;
  };
  return esegui;
}

function bottoneCopia(sql) {
  const copia = conIcona("button", { className: "bottone", type: "button" }, "copia", "Copia");
  copia.onclick = async () => {
    await navigator.clipboard.writeText(sql);
    copia.innerHTML = icona("ok"); copia.append(el("span", { textContent: "Copiata" }));
    setTimeout(() => { copia.innerHTML = icona("copia"); copia.append(el("span", { textContent: "Copia" })); }, 1500);
  };
  return copia;
}

// Nome di file sicuro su Windows, dal titolo di una query
const nomeFileDa = titolo => (titolo.replace(/[\\/:*?"<>|]+/g, " ").trim().slice(0, 80) || "risultati") + ".csv";
