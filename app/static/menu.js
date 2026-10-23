// Menu laterale comune a tutte le pagine (con la sezione Progetti), icone,
// finestre di dialogo e piccole funzioni di aiuto.
// Ogni pagina ha <aside class="menu" id="menu"></aside> e un bottone .hamburger nella barra.

const ICONE = {
  chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  grafico: '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
  database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  cpu: '<rect x="5" y="5" width="14" height="14" rx="2"/><path d="M9 1v4M15 1v4M9 19v4M15 19v4M1 9h4M1 15h4M19 9h4M19 15h4"/>',
  scudo: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  chiudi: '<path d="M18 6 6 18M6 6l12 12"/>',
  copia: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  esegui: '<path d="M6 4l14 8-14 8z"/>',
  nuovo: '<path d="M12 5v14M5 12h14"/>',
  scarica: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5M12 15V3"/>',
  aggiorna: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
  invia: '<path d="M22 2 11 13M22 2l-7 20-4-9-9-4z"/>',
  ok: '<path d="M20 6 9 17l-5-5"/>',
  impostazioni: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  ripristina: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
  freccia: '<path d="m9 18 6-6-6-6"/>',
  cartella: '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.7-.9l-.8-1.2A2 2 0 0 0 7.9 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2z"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
  puntini: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  modifica: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  cestino: '<path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>',
  sposta: '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.7-.9l-.8-1.2A2 2 0 0 0 7.9 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2z"/><path d="M12 10l3 3-3 3M9 13h6"/>',
  salva: '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
  avviso: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
  espandi: '<path d="m7 15 5 5 5-5M7 9l5-5 5 5"/>',
  comprimi: '<path d="m7 20 5-5 5 5M7 4l5 5 5-5"/>',
};

function icona(nome) {
  return `<svg class="icona" viewBox="0 0 24 24" aria-hidden="true">${ICONE[nome] || ""}</svg>`;
}

function el(tag, attributi = {}, ...figli) {
  const e = document.createElement(tag);
  Object.assign(e, attributi);
  for (const f of figli) e.append(f);
  return e;
}

// Elemento con HTML fidato (solo le nostre icone, mai testo dell'utente o del database)
function conIcona(tag, attributi, nomeIcona, testo = "") {
  const e = el(tag, attributi);
  e.innerHTML = icona(nomeIcona);
  if (testo) e.append(el("span", { textContent: testo }));
  return e;
}

async function api(percorso, corpo, metodo = corpo === undefined ? "GET" : "POST") {
  const r = await fetch(percorso, {
    method: metodo,
    headers: corpo === undefined ? {} : { "Content-Type": "application/json" },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  });
  const dati = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(dati.detail || `Errore ${r.status}`);
  return dati;
}

// ---------- Finestra di dialogo ----------
// campi: [{ nome, etichetta, valore, obbligatorio, segnaposto, tipo: "testo" | "scelta", opzioni: [{valore, testo}],
//           mostraSe: { campo, valore } }]
// azione(valori) viene eseguita alla conferma: se lancia un errore, il messaggio resta nella finestra.
// Restituisce il risultato di azione (o i valori), oppure null se si annulla.
function finestra({ titolo, testo = "", campi = [], conferma = "Conferma", pericolo = false, azione }) {
  return new Promise(risolvi => {
    const dialogo = el("dialog", { className: "finestra" });
    const form = el("form");
    const errore = el("p", { className: "errore", role: "alert" });
    const controlli = {};
    form.append(el("h2", { textContent: titolo }));
    if (testo) form.append(el("p", { className: "testo-finestra", textContent: testo }));

    for (const c of campi) {
      let controllo;
      if (c.tipo === "scelta") {
        controllo = el("select", { name: c.nome });
        for (const o of c.opzioni) controllo.append(el("option", { value: o.valore, textContent: o.testo, selected: String(o.valore) === String(c.valore) }));
      } else {
        controllo = el("input", { name: c.nome, type: c.tipo === "password" ? "password" : "text", value: c.valore ?? "",
                                  maxLength: 120, placeholder: c.segnaposto ?? "", autocomplete: "off" });
      }
      const blocco = el("label", { className: "campo" }, el("span", { textContent: c.etichetta }), controllo);
      controlli[c.nome] = { controllo, blocco, c };
      form.append(blocco);
    }
    const visibili = () => Object.values(controlli).filter(x => !x.blocco.hidden);
    const aggiornaVisibili = () => {
      for (const { blocco, c } of Object.values(controlli)) {
        if (c.mostraSe) blocco.hidden = controlli[c.mostraSe.campo].controllo.value !== String(c.mostraSe.valore);
      }
    };
    form.addEventListener("change", aggiornaVisibili);
    aggiornaVisibili();
    // Invio conferma anche dai menu a tendina (il browser lo fa da solo solo nei campi di testo)
    form.addEventListener("keydown", e => {
      if (e.key === "Enter" && e.target.tagName === "SELECT") { e.preventDefault(); form.requestSubmit(); }
    });

    const annulla = el("button", { type: "button", className: "bottone", textContent: "Annulla" });
    const ok = el("button", { type: "submit", className: "bottone " + (pericolo ? "pericolo" : "primario"), textContent: conferma });
    form.append(errore, el("div", { className: "azioni-finestra" }, annulla, ok));
    dialogo.append(form);

    let risultato = null;
    const chiudi = valore => { risultato = valore; dialogo.close(); };
    dialogo.addEventListener("close", () => { dialogo.remove(); risolvi(risultato); });
    annulla.onclick = () => chiudi(null);
    form.addEventListener("submit", async evento => {
      evento.preventDefault();
      const valori = Object.fromEntries(visibili().map(({ controllo, c }) => [c.nome, controllo.value.trim()]));
      const vuoto = visibili().find(({ controllo, c }) => c.obbligatorio && !controllo.value.trim());
      if (vuoto) { errore.textContent = `Compila il campo «${vuoto.c.etichetta}».`; vuoto.controllo.focus(); return; }
      ok.disabled = true;
      try { chiudi(azione ? await azione(valori) : valori); }
      catch (e) { errore.textContent = e.message; ok.disabled = false; }
    });

    document.body.append(dialogo);
    dialogo.showModal();
    const primo = form.querySelector("input, select");
    if (primo) { primo.focus(); if (primo.select) primo.select(); } else ok.focus();
  });
}

// ---------- Menu a comparsa (i pulsanti ⋯) ----------
let menuAperto = null;

function chiudiMenuContestuale() {
  if (menuAperto) { menuAperto.remove(); menuAperto = null; }
}

function menuContestuale(ancora, voci) {
  const giaAperto = menuAperto?.ancora === ancora;
  chiudiMenuContestuale();
  if (giaAperto) return;  // secondo clic sullo stesso ⋯: lo chiude
  const m = el("div", { className: "menu-contestuale", role: "menu" });
  for (const v of voci) {
    const b = conIcona("button", { type: "button", role: "menuitem", className: v.pericolo ? "pericolo" : "" }, v.icona, v.testo);
    b.onclick = () => { chiudiMenuContestuale(); v.azione(); };
    m.append(b);
  }
  m.ancora = ancora;
  document.body.append(m);
  const r = ancora.getBoundingClientRect();
  m.style.top = `${Math.min(r.bottom + 4, innerHeight - m.offsetHeight - 8)}px`;
  m.style.left = `${Math.max(8, Math.min(r.left, innerWidth - m.offsetWidth - 8))}px`;
  menuAperto = m;
  m.querySelector("button")?.focus();
}

document.addEventListener("click", e => {
  if (menuAperto && !menuAperto.contains(e.target) && !menuAperto.ancora.contains(e.target)) chiudiMenuContestuale();
});
document.addEventListener("keydown", e => { if (e.key === "Escape") chiudiMenuContestuale(); });

// ---------- Menu laterale ----------
const VOCI_MENU = [
  { href: "/", testo: "Chat", icona: "chat" },
  { href: "/consumi", testo: "Consumi", icona: "grafico" },
];
// Voci staccate, in fondo al menu
const VOCI_FONDO = [
  { href: "/connessioni", testo: "Connessioni", icona: "database" },
  { href: "/impostazioni", testo: "Impostazioni", icona: "impostazioni" },
];

function vociNav(voci, etichetta, classe = "") {
  const nav = el("nav", { ariaLabel: etichetta, className: classe });
  for (const v of voci) {
    const a = conIcona("a", { href: v.href }, v.icona, v.testo);
    if (location.pathname === v.href) a.setAttribute("aria-current", "page");
    nav.append(a);
  }
  return nav;
}

function preparaMenu() {
  const menu = document.getElementById("menu");
  const marchio = el("a", { className: "marchio", href: "/" });
  marchio.innerHTML = `<span class="logo">${icona("database")}</span>`;
  marchio.append("Chat SQL");

  const selettore = el("div", { className: "selettore", id: "selettore-connessione" });
  const nav = vociNav(VOCI_MENU, "Navigazione principale");
  const sezioneProgetti = el("section", { className: "progetti", id: "progetti", ariaLabel: "Progetti" });
  const fondo = vociNav(VOCI_FONDO, "Configurazione", "fondo");

  const info = el("div", { className: "info", id: "info-db" });
  menu.replaceChildren(marchio, selettore, nav, sezioneProgetti, fondo, info);
  prontaConnessione.then(disegnaSelettore);
  caricaInfo(info);
  ricaricaProgetti();

  // Hamburger: apre e chiude il menu su schermi stretti
  const app = document.querySelector(".app");
  const velo = el("div", { className: "velo" });
  app.append(velo);
  const chiudi = () => app.classList.remove("menu-aperto");
  document.querySelectorAll(".hamburger").forEach(b => {
    b.innerHTML = icona("menu");
    b.setAttribute("aria-label", "Apri il menu");
    b.onclick = () => app.classList.toggle("menu-aperto");
  });
  velo.onclick = chiudi;
  menu.addEventListener("click", e => { if (e.target.closest("nav a, .progetti a")) chiudi(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !document.querySelector("dialog[open]")) chiudi(); });
}

// ---------- Connessione attiva ----------
// Quale database si sta usando resta nel browser: ogni utente può lavorare su uno diverso
const CHIAVE_CONNESSIONE = "nl2sql-connessione";
let elencoConnessioni = [];
let connessioneAttiva = null;

// Le pagine aspettano questa promessa prima di chiamare le API che vogliono una connessione
const prontaConnessione = (async () => {
  elencoConnessioni = await api("/api/connessioni");
  let ricordata = null;
  try { ricordata = Number(localStorage.getItem(CHIAVE_CONNESSIONE)); } catch { /* storage non disponibile */ }
  connessioneAttiva = elencoConnessioni.find(c => c.id === ricordata) || elencoConnessioni[0] || null;
  return connessioneAttiva;
})().catch(() => null);

function ricordaConnessione(id) {
  try { localStorage.setItem(CHIAVE_CONNESSIONE, String(id)); } catch { /* storage non disponibile */ }
}

const descriviConnessione = c => [c.dialetto, c.database].filter(Boolean).join(" · ") || "non configurata";

function disegnaSelettore() {
  const contenitore = document.getElementById("selettore-connessione");
  if (!contenitore) return;
  const c = connessioneAttiva;
  if (!c) { contenitore.replaceChildren(el("p", { className: "vuoto", textContent: "Nessuna connessione configurata." })); return; }
  const bottone = el("button", { type: "button", className: "connessione", title: `Database: ${c.nome}`, ariaLabel: `Database attivo: ${c.nome}. Cambia database` });
  bottone.innerHTML = icona("database");
  bottone.append(
    el("span", { className: "testi" }, el("span", { className: "nome", textContent: c.nome }),
      el("span", { className: "dettaglio", textContent: descriviConnessione(c) })));
  bottone.insertAdjacentHTML("beforeend", icona("espandi"));
  bottone.onclick = () => menuContestuale(bottone, elencoConnessioni.map(x => ({
    testo: x.configurata ? x.nome : `${x.nome} (non configurata)`,
    icona: x.id === c.id ? "ok" : "database",
    azione: () => scegliConnessione(x.id),
  })));
  contenitore.replaceChildren(bottone);
}

// Scelta dal selettore: si riparte da una pagina pulita (la chat in corso riguarda il database precedente)
function scegliConnessione(id) {
  if (id === connessioneAttiva?.id) return;
  ricordaConnessione(id);
  if (queryCorrente) location.href = "/"; else location.reload();
}

// Dopo aver creato, modificato o eliminato connessioni: rilegge l'elenco e aggiorna il menu
async function ricaricaConnessioni() {
  elencoConnessioni = await api("/api/connessioni");
  connessioneAttiva = elencoConnessioni.find(c => c.id === connessioneAttiva?.id) || elencoConnessioni[0] || null;
  if (connessioneAttiva) ricordaConnessione(connessioneAttiva.id);
  disegnaSelettore();
  aggiornaInfo();
  ricaricaProgetti();
  return elencoConnessioni;
}

// Usata dalla pagina di una query salvata che appartiene a un altro database: il menu passa a quello
function usaConnessione(id) {
  const c = elencoConnessioni.find(x => x.id === id);
  if (!c || c.id === connessioneAttiva?.id) return;
  connessioneAttiva = c;
  ricordaConnessione(id);
  disegnaSelettore();
  aggiornaInfo();
  ricaricaProgetti();
}

// Le pagine la chiamano dopo aver cambiato le impostazioni
function aggiornaInfo() {
  const info = document.getElementById("info-db");
  if (info) caricaInfo(info);
}

async function caricaInfo(contenitore) {
  try {
    const c = await prontaConnessione;
    if (!c) { contenitore.replaceChildren(); return; }
    const i = await api(`/api/info?connessione_id=${c.id}`);
    contenitore.replaceChildren();
    const riga = (nomeIcona, testo, titolo) => {
      const d = conIcona("div", { className: "riga", title: titolo || testo }, nomeIcona);
      d.append(el("span", { textContent: testo }));
      return d;
    };
    contenitore.append(el("div", { className: "sezione", textContent: "Collegamento" }));
    contenitore.append(riga("cpu", `${i.modello} · ${i.effort}`, `Modello: ${i.modello}, effort ${i.effort}`));
    if (!i.configurata) {
      const d = conIcona("div", { className: "riga", title: "Manca la stringa di connessione" }, "avviso");
      d.append(el("span", { className: "etichetta-stato avviso", textContent: "non configurata" }));
      contenitore.append(d);
    }
    if (i.solo_metadati) {
      const d = conIcona("div", { className: "riga", title: "Claude vede solo la struttura del database, mai i dati" }, "scudo");
      d.append(el("span", { className: "etichetta-stato", textContent: "solo metadati" }));
      contenitore.append(d);
    }
  } catch { /* le informazioni sono facoltative */ }
}

// ---------- Sezione Progetti ----------
// Quali cartelle sono aperte resta nel browser (comodità personale, non serve salvarlo sul server)
const CHIAVE_STATO = "nl2sql-progetti";
function statoProgetti() {
  try { return { chiusa: false, aperti: [], ...JSON.parse(localStorage.getItem(CHIAVE_STATO) || "{}") }; }
  catch { return { chiusa: false, aperti: [] }; }
}
function salvaStatoProgetti(stato) {
  try { localStorage.setItem(CHIAVE_STATO, JSON.stringify(stato)); } catch { /* storage non disponibile */ }
}

let elencoProgetti = [];  // l'ultimo elenco letto dal server, usato anche dalle pagine (es. "Sposta")
const queryCorrente = Number((location.pathname.match(/^\/query\/(\d+)$/) || [])[1]) || null;

// Rilegge i progetti dal server e ridisegna la sezione; avvisa le pagine con l'evento "progetti-cambiati"
async function ricaricaProgetti() {
  const sezione = document.getElementById("progetti");
  if (!sezione) return;
  await prontaConnessione;
  if (!connessioneAttiva) { elencoProgetti = []; sezione.replaceChildren(); return; }
  try { elencoProgetti = await api(`/api/progetti?connessione_id=${connessioneAttiva.id}`); }
  catch (e) { sezione.replaceChildren(el("p", { className: "vuoto", textContent: e.message })); return; }
  disegnaProgetti(sezione);
  window.dispatchEvent(new Event("progetti-cambiati"));
}

let progettoAperto = null;  // il progetto già aperto in automatico per la query corrente

function disegnaProgetti(sezione) {
  const stato = statoProgetti();
  // La cartella che contiene la query aperta si apre da sola una volta (all'arrivo sulla pagina o dopo uno
  // spostamento); poi l'utente può chiuderla come le altre
  const progettoCorrente = elencoProgetti.find(p => p.query.some(q => q.id === queryCorrente));
  if (progettoCorrente && progettoCorrente.id !== progettoAperto) {
    progettoAperto = progettoCorrente.id;
    if (!stato.aperti.includes(progettoCorrente.id)) stato.aperti.push(progettoCorrente.id);
    salvaStatoProgetti({ ...stato, chiusa: false });
    stato.chiusa = false;
  }

  const titolo = conIcona("button", { type: "button", className: "titolo-sezione", ariaExpanded: String(!stato.chiusa) }, "freccia", "Progetti");
  titolo.onclick = () => { stato.chiusa = !stato.chiusa; salvaStatoProgetti(stato); disegnaProgetti(sezione); };
  const altro = conIcona("button", { type: "button", className: "piccolo", title: "Opzioni", ariaLabel: "Opzioni dei progetti" }, "puntini");
  altro.onclick = () => menuContestuale(altro, [
    { testo: "Espandi tutti", icona: "espandi", azione: () => { salvaStatoProgetti({ ...stato, chiusa: false, aperti: elencoProgetti.map(p => p.id) }); disegnaProgetti(sezione); } },
    { testo: "Comprimi tutti", icona: "comprimi", azione: () => { salvaStatoProgetti({ ...stato, aperti: [] }); disegnaProgetti(sezione); } },
  ]);
  const nuovo = conIcona("button", { type: "button", className: "piccolo", title: "Nuovo progetto", ariaLabel: "Nuovo progetto" }, "nuovo");
  nuovo.onclick = () => nuovoProgetto();

  const lista = el("div", { className: "lista-progetti", hidden: stato.chiusa });
  if (!elencoProgetti.length) {
    lista.append(el("p", { className: "vuoto", textContent: "Nessun progetto. Salva una query dalla chat, oppure creane uno con +." }));
  }
  for (const p of elencoProgetti) {
    const aperto = stato.aperti.includes(p.id);
    const cartella = el("button", { type: "button", className: "cartella", ariaExpanded: String(aperto), title: p.nome });
    cartella.innerHTML = icona("freccia") + icona("cartella");
    cartella.append(el("span", { className: "nome", textContent: p.nome }), el("span", { className: "conteggio", textContent: p.query.length }));
    cartella.onclick = () => {
      stato.aperti = aperto ? stato.aperti.filter(id => id !== p.id) : [...stato.aperti, p.id];
      salvaStatoProgetti(stato); disegnaProgetti(sezione);
    };
    const azioni = conIcona("button", { type: "button", className: "piccolo azioni-progetto", title: "Azioni", ariaLabel: `Azioni del progetto ${p.nome}` }, "puntini");
    azioni.onclick = () => menuContestuale(azioni, [
      { testo: "Rinomina", icona: "modifica", azione: () => rinominaProgetto(p) },
      { testo: "Elimina", icona: "cestino", pericolo: true, azione: () => eliminaProgetto(p) },
    ]);

    const voci = el("ul", { className: "query-progetto", hidden: !aperto });
    for (const q of p.query) {
      const a = el("a", { href: `/query/${q.id}`, title: q.titolo, draggable: true },
        el("span", { className: "etichetta-sql", textContent: "SQL", ariaHidden: "true" }),
        el("span", { textContent: q.titolo }));
      if (q.id === queryCorrente) a.setAttribute("aria-current", "page");
      trascinabile(a, q, p);
      voci.append(el("li", {}, a));
    }
    if (!p.query.length) voci.append(el("li", { className: "vuoto", textContent: "Nessuna query" }));
    const blocco = el("div", { className: "progetto" }, el("div", { className: "riga-progetto" }, cartella, azioni), voci);
    bersaglio(blocco, p);
    lista.append(blocco);
  }

  sezione.replaceChildren(el("div", { className: "testata-progetti" }, titolo, el("span", { className: "spazio" }), altro, nuovo), lista);
}

// ---------- Trascinamento delle query da un progetto all'altro ----------
// Drag and drop nativo del browser: con il mouse sì, con il tocco no (lì resta "Sposta" nella pagina della query)
const TIPO_TRASCINAMENTO = "application/x-chat-sql-query";
let trascinata = null;  // { query, progetto } durante il trascinamento

function trascinabile(link, query, progetto) {
  link.addEventListener("dragstart", e => {
    trascinata = { query, progetto };
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData(TIPO_TRASCINAMENTO, String(query.id));
    e.dataTransfer.setData("text/plain", query.titolo);
    link.classList.add("in-trascinamento");
  });
  link.addEventListener("dragend", () => {
    trascinata = null;
    link.classList.remove("in-trascinamento");
    document.querySelectorAll(".progetto.bersaglio").forEach(b => b.classList.remove("bersaglio"));
  });
}

function bersaglio(blocco, progetto) {
  const valido = e => e.dataTransfer.types.includes(TIPO_TRASCINAMENTO) && trascinata && trascinata.progetto.id !== progetto.id;
  blocco.addEventListener("dragover", e => {
    if (!valido(e)) return;
    e.preventDefault();  // senza, il browser non permette il rilascio
    e.dataTransfer.dropEffect = "move";
    blocco.classList.add("bersaglio");
  });
  blocco.addEventListener("dragleave", e => {
    if (!blocco.contains(e.relatedTarget)) blocco.classList.remove("bersaglio");  // ignora il passaggio sui figli
  });
  blocco.addEventListener("drop", async e => {
    if (!valido(e)) return;
    e.preventDefault();
    blocco.classList.remove("bersaglio");
    const { query } = trascinata;
    trascinata = null;  // il menu viene ridisegnato: il "dragend" dell'elemento rimosso potrebbe non arrivare
    try {
      await api(`/api/query/${query.id}`, { progetto_id: progetto.id }, "PATCH");
    } catch (errore) {
      await finestra({ titolo: "Spostamento non riuscito", testo: errore.message, conferma: "OK" });
      return;
    }
    // Si apre la cartella di destinazione, così si vede dove è finita la query
    const stato = statoProgetti();
    if (!stato.aperti.includes(progetto.id)) stato.aperti.push(progetto.id);
    salvaStatoProgetti(stato);
    ricaricaProgetti();
  });
}

async function nuovoProgetto() {
  const p = await finestra({
    titolo: "Nuovo progetto", conferma: "Crea",
    campi: [{ nome: "nome", etichetta: "Nome", obbligatorio: true, segnaposto: "Es. Vendite 2025" }],
    azione: v => api("/api/progetti", { connessione_id: connessioneAttiva.id, nome: v.nome }),
  });
  if (!p) return;
  const stato = statoProgetti();
  salvaStatoProgetti({ ...stato, chiusa: false, aperti: [...stato.aperti, p.id] });
  ricaricaProgetti();
}

async function rinominaProgetto(p) {
  const r = await finestra({
    titolo: "Rinomina progetto", conferma: "Rinomina",
    campi: [{ nome: "nome", etichetta: "Nome", valore: p.nome, obbligatorio: true }],
    azione: v => api(`/api/progetti/${p.id}`, { nome: v.nome }, "PATCH"),
  });
  if (r) ricaricaProgetti();
}

async function eliminaProgetto(p) {
  const n = p.query.length;
  const r = await finestra({
    titolo: "Eliminare il progetto?", conferma: "Elimina", pericolo: true,
    testo: n ? `«${p.nome}» e ${n === 1 ? "la sua query sarà eliminata" : `le sue ${n} query saranno eliminate`} definitivamente.`
             : `Il progetto «${p.nome}» sarà eliminato.`,
    azione: () => api(`/api/progetti/${p.id}`, undefined, "DELETE"),
  });
  if (!r) return;
  if (p.query.some(q => q.id === queryCorrente)) { location.href = "/"; return; }
  ricaricaProgetti();
}

document.addEventListener("DOMContentLoaded", preparaMenu);
