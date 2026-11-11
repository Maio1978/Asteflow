// Da eseguire nella pagina https://pvp.giustizia.it/pvp/ (pannello del browser).
// Scarica tutte le abitazioni all'asta con data futura in tutti i tribunali e le mette in window._ch (blocchi da ~190 KB, ognuno è un array JSON valido).
// Poi leggere ogni blocco con:  '#'+i+'#'+window._ch[i]   per i = 0 .. window._ch.length-1
const oggi=new Date().toISOString().slice(0,10);
const trib=await fetch('/ve-3f723b85-986a1b71/ve-ms/tribunali').then(r=>r.json()).then(j=>(j.body||j).map(t=>t.nomeUfficio||t).filter(t=>/^Tribunale/i.test(t)));
const ABI=['ABITAZIONE','APPARTAMENTO','VILLA'];const rows=[];const errs=[];
async function uno(t){for(let page=0;page<30;page++){let j;try{j=await fetch(`/ric-496b258c-986a1b71/ric-ms/ricerca/vendite?language=it&page=${page}&size=100&sort=dataOraVendita,desc`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tipoLotto:'IMMOBILI',categoriaLotto:'IMMOBILE_RESIDENZIALE',tribunale:t})}).then(r=>r.json())}catch(e){errs.push(t);return}
 const c=(j.body||{}).content||[];const fut=c.filter(x=>(x.dataVendita||'')>=oggi);
 for(const x of fut){if(!(x.categoriaBene||[]).some(b=>ABI.some(k=>b.includes(k))))continue;const i=x.indirizzo||{},co=i.coordinate||{};
  rows.push([x.id,(x.tribunale||'').replace(/^Tribunale di /i,''),(i.via||'').replace(/,?\s*\d{5}\b.*$/,''),i.citta||'',i.provincia||'',co.latitudine||null,co.longitudine||null,x.prezzoBaseAsta,x.offertaMinima,x.dataVendita,(x.disponibilita||[])[0]||'',(x.descLotto||'').replace(/\s+/g,' ').trim().slice(0,900),x.orarioVendita||null,x.rialzoMinimo||null,x.procedura||null,(x.categoriaBene||[]).join('|'),x.numeroLotto||null])}
 if(fut.length<c.length||!c.length)return}}
const q=[...trib];await Promise.all(Array.from({length:6},async()=>{while(q.length)await uno(q.shift())}));
window._ch=[];let cur=[],len=0;for(const r of rows){const t=JSON.stringify(r);if(len+t.length>190000&&cur.length){window._ch.push(JSON.stringify(cur));cur=[];len=0}cur.push(r);len+=t.length+1}if(cur.length)window._ch.push(JSON.stringify(cur));
({tribunali:trib.length,abitazioni:rows.length,blocchi:window._ch.length,errori:errs})
