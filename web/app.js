const $ = (id) => document.getElementById(id);
let historico = [];
let registros = [];
let ocupado = false;
const exemplos = {
  anomalias: 'O motor 3 apresentou anomalias no período selecionado? Informe o total, o maior score e a diferença entre anomalia e falha prevista.',
  documentos: 'Relacione os dados do motor 3 com a documentação sobre superaquecimento e explique como investigar os desvios, indicando as fontes e os limites da análise.',
  manutencao: 'Qual foi a última troca de rolamento do motor 3, em que data e qual técnico realizou o serviço?'
};
function mensagem(papel, texto, erro = false) {
  const artigo = document.createElement('article');
  artigo.className = `mensagem ${papel}${erro ? ' erro' : ''}`;
  const autor = document.createElement('div'); autor.className = 'autor'; autor.textContent = papel === 'usuario' ? 'VOCÊ' : 'FORZY';
  const conteudo = document.createElement('div'); conteudo.className = 'conteudo'; conteudo.textContent = texto;
  artigo.append(autor, conteudo); $('mensagens').append(artigo); $('boas-vindas').hidden = true;
  artigo.scrollIntoView({behavior: 'smooth', block: 'nearest'});
  return conteudo;
}
function evidencia(resultado) {
  $('resumo').replaceChildren(); $('fontes').replaceChildren();
  const c = resultado.contexto_operacional || {};
  const numero = (n) => Number(n).toLocaleString('pt-BR', {maximumFractionDigits: 3});
  const linha = (nome, valor) => {const p=document.createElement('div');p.className='metrica';const a=document.createElement('span');a.textContent=nome;const b=document.createElement('strong');b.textContent=valor;p.append(a,b);$('resumo').append(p);};
  if(c.disponivel){
    linha('Motor', c.motor_id ?? 'Todos');linha('Leituras',numero(c.quantidade_leituras));linha('Anomalias · baseline',numero(c.anomalias_baseline));linha('Maior score',numero(c.score_maximo));
    const periodo=document.createElement('p');periodo.className='recorte';periodo.textContent=`${c.inicio} → ${c.fim}`;$('resumo').append(periodo);
    if(resultado.serie?.length){const ns='http://www.w3.org/2000/svg';const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 260 70');svg.setAttribute('class','grafico');svg.setAttribute('role','img');svg.setAttribute('aria-label','Evolução do score de anomalia no período');const max=Math.max(...resultado.serie.map(r=>r.score),1);const poly=document.createElementNS(ns,'polyline');poly.setAttribute('points',resultado.serie.map((r,i)=>`${i*260/Math.max(1,resultado.serie.length-1)},${65-r.score/max*60}`).join(' '));poly.setAttribute('fill','none');poly.setAttribute('stroke','#1d6549');poly.setAttribute('stroke-width','1.8');svg.append(poly);$('resumo').append(svg);}
  } else if(c.motivo){const p=document.createElement('p');p.className='nota';p.textContent=c.motivo;$('resumo').append(p);}
  if(resultado.informacao_insuficiente){const p=document.createElement('p');p.className='nota';p.textContent='Informação insuficiente para responder integralmente.';$('resumo').append(p);}
  const fontes = resultado.fontes || [];
  $('quantidade-fontes').textContent=`${fontes.length} fonte${fontes.length===1?'':'s'}`;
  for(const f of fontes){const d=document.createElement('details');d.className='fonte';const s=document.createElement('summary');s.textContent=`[${f.id}] ${f.titulo}`;const p=document.createElement('p');p.textContent=f.arquivo+(f.pagina?` · página ${f.pagina}`:'');const t=document.createElement('pre');t.textContent=f.trecho;d.append(s,p,t);$('fontes').append(d);}
  $('exportar').hidden = registros.length === 0;
}
async function enviar(evento){
  evento?.preventDefault(); if(ocupado)return;
  const pergunta=$('pergunta').value.trim();if(!pergunta)return;
  if(!$('filtros').reportValidity())return;
  const valores=['rotacao','vibracao','temperatura','corrente'].map(id=>$(id).value);
  if(valores.some(Boolean)&&!valores.every(Boolean)){mensagem('assistente','Preencha os quatro sensores ou deixe todos vazios.',true);return;}
  const dados={pergunta,motor_id:$('motor').value?Number($('motor').value):null,inicio:$('inicio').value||null,fim:$('fim').value||null,historico};
  if(valores.every(Boolean))dados.sensores=Object.fromEntries(['rotacao_rpm','vibracao_mm_s','temperatura_c','corrente_a'].map((n,i)=>[n,Number(valores[i])]));
  ocupado=true;$('enviar').disabled=true;$('nova').disabled=true;mensagem('usuario',pergunta);$('pergunta').value='';
  const saida=mensagem('assistente','Consultando dados e documentos…');saida.setAttribute('aria-busy','true');
  try{const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(dados)});const resposta=await r.json();if(!r.ok)throw Error(resposta.erro||'Falha na consulta.');saida.textContent=resposta.resposta;historico=[...historico,{papel:'usuario',conteudo:pergunta},{papel:'assistente',conteudo:resposta.resposta}].slice(-6);registros.push({pergunta,filtros:{motor_id:dados.motor_id,inicio:dados.inicio,fim:dados.fim},...resposta});evidencia(resposta);}
  catch(erro){saida.textContent=erro.message;saida.parentElement.classList.add('erro');}
  finally{saida.removeAttribute('aria-busy');ocupado=false;$('enviar').disabled=false;$('nova').disabled=false;$('pergunta').focus();}
}
$('consulta').addEventListener('submit',enviar);
$('pergunta').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();if($('consulta').reportValidity())enviar();}});
document.querySelectorAll('[data-exemplo]').forEach(b=>b.addEventListener('click',()=>{$('motor').value='3';$('pergunta').value=exemplos[b.dataset.exemplo];$('pergunta').focus();}));
$('nova').addEventListener('click',()=>{historico=[];registros=[];$('mensagens').replaceChildren();$('boas-vindas').hidden=false;$('resumo').replaceChildren();const p=document.createElement('p');p.className='vazio';p.textContent='Nenhuma consulta realizada.';$('resumo').append(p);$('fontes').replaceChildren();$('quantidade-fontes').textContent='0 fontes';$('exportar').hidden=true;$('pergunta').value='';$('pergunta').focus();});
$('exportar').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({projeto:'Forzy · Sprint 04',consultas:registros},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='forzy-conversa.json';a.click();URL.revokeObjectURL(url);});
async function iniciar(){try{const [r,s]=await Promise.all([fetch('/api/motores'),fetch('/api/status')]);if(!r.ok||!s.ok)throw Error('Falha ao iniciar.');const [motores,estado]=await Promise.all([r.json(),s.json()]);for(const m of motores){const o=document.createElement('option');o.value=m.motor_id;o.textContent=`Motor ${m.motor_id} · ${m.fabricante}`;$('motor').append(o);}$('conexao').textContent=estado.chave_configurada?'Chave OpenAI configurada':'Chave OpenAI não configurada';}catch(erro){$('conexao').textContent=erro.message;}}
iniciar();
